# DynamoDB CRM Persistence Design

## Objective

Add durable CRM record persistence without coupling business logic to AWS. Local
development and all automated tests remain deterministic and offline with the
mock repository. ECS selects DynamoDB explicitly through configuration.

This milestone prepares application code, tests, IAM policy documents, and the
ECS task definition locally. It does not create or modify AWS resources, alter a
deployed service, commit implementation work, push, merge, or deploy.

## Architecture

The dependency direction is:

```text
IntakeService -> CRMRepository <- MockCRMRepository
                              <- DynamoDBCRMRepository
```

`CRMRepository` is a structural `Protocol` in `domain/repositories.py` containing
the four existing creation operations. `IntakeService` imports and depends only
on this protocol. It must not import either concrete adapter.

`MockCRMRepository` retains the existing in-memory records, thread safety, and
deterministic per-type sequential IDs. `MockCRM` remains as a compatibility alias.

`DynamoDBCRMRepository` is container-owned and is the only application module
that imports or directly uses `boto3`. The composition root in `dependencies.py`
selects an adapter from typed settings; there is no runtime fallback between
adapters.

The RAG system, sample documents, vector store, scheduling, agent routing, and
tool response composition remain unchanged.

## Configuration And Wiring

`Settings` adds:

```text
CRM_PROVIDER: Literal["mock", "dynamodb"] = "mock"
DYNAMODB_TABLE_NAME = "doc-helper-records"
AWS_REGION = "us-east-1"
CRM_RECORD_TTL_DAYS = 90
```

`.env.example` and Docker Compose explicitly use `CRM_PROVIDER=mock`. The ECS
task definition explicitly uses `CRM_PROVIDER=dynamodb` and supplies the table,
region, and TTL settings while retaining mock LLM settings.

`Container.__init__` constructs dependencies in this exact order:

1. Resolve settings.
2. Build the selected CRM repository.
3. Get the mock schedule.
4. Get the vector store.
5. Get the RAG service.
6. Build the intake service with the exact repository stored as `container.crm`.

`_build_crm_repository(settings)` returns the mock singleton for `mock`, creates
a `DynamoDBCRMRepository` for `dynamodb`, and defensively raises for any unsupported
provider. Pydantic normally rejects unsupported values first. Construction and
AWS failures are never converted into mock mode.

The DynamoDB adapter has no module singleton. Resetting the container drops its
reference. Tests also reset the intake service, mock CRM, settings cache, mock
schedule, vector store, and RAG service.

## DynamoDB Record Model

The table has one partition key, `record_id`, and no sort key. Every operation
writes this canonical item:

```text
record_id    string, <PREFIX>-<UTC_YEAR>-<12 uppercase UUID hex chars>
record_type  string
user_id      string
status       string
priority     string
created_at   ISO-8601 UTC string
updated_at   ISO-8601 UTC string
payload      DynamoDB map containing operation-specific fields
expires_at   integer Unix timestamp
```

Prefixes are `APPT`, `CALLBACK`, `COMPLAINT`, and `ESC`. UUID-derived suffixes
avoid distributed numeric counters. Sequential IDs remain exclusive to the mock.

Operation mappings are:

| Operation | Status | Priority | Payload |
| --- | --- | --- | --- |
| Appointment | `pending_confirmation` | `normal` | `specialty`, `preferred_day`, `slot`, `notes` |
| Callback | `open` | supplied value | `reason` |
| Complaint | `open` | `normal` | `summary` |
| Escalation | `open` | supplied value | `reason`, `categories` |

`categories=None` becomes `[]`. `slot=None` remains `None` and is serialized by
boto3 as DynamoDB null. TTL is calculated from the write time plus the configured
number of days. Writes use `attribute_not_exists(record_id)`.

The return dictionary flattens the payload for compatibility with existing tools,
maps persisted `record_id` to application field `id`, and includes canonical
`type`, `user_id`, `status`, `priority`, and `created_at`. Payload is expanded
first and canonical shared fields are assigned afterward, so payload keys cannot
overwrite `id`, `type`, `user_id`, `status`, `priority`, or `created_at`.

## Error Handling

`CRMRepositoryError` extends `DocHelperError`, maps to HTTP 503, uses error code
`crm_unavailable`, and exposes the safe message `CRM persistence is temporarily
unavailable.`

The adapter translates `ClientError` and explicitly operational SDK failures,
including credential retrieval, missing/partial credentials, endpoint/connection,
timeout, HTTP client, and transport errors. A `ClientError` code is read safely:

```python
error_code = exc.response.get("Error", {}).get("Code", "Unknown")
```

The translated error is raised from the original exception. Client-side
validation and programming errors such as `ParamValidationError` propagate
unchanged rather than being mislabeled as availability failures.

Failure logs contain only record type, generated record ID when available, AWS
error code, and exception class. They never include user IDs, payloads, notes,
reasons, summaries, categories, or other request content. Success logs contain
only record type and generated record ID.

Repository failures propagate through `IntakeService`, transactional creation
tools, and the graph. They are not converted into `ActionResult.ERROR`, because a
failed write must not lead the graph to imply that a ticket exists. The chat route
re-raises `DocHelperError` before its broad exception handler, preserving the 503
contract. Unexpected exceptions retain the existing generic agent error behavior.

Tool-authoring guidance will narrowly document that transactional record-creation
tools propagate persistence failures; ordinary recoverable tool failures may
still return `ActionResult.ERROR`.

## AWS Deployment Artifacts

Local file changes include:

- An ECS task-role trust policy for `ecs-tasks.amazonaws.com`, constrained by the
  known source account and ECS source ARN.
- A least-privilege DynamoDB table policy for the task role.
- A GitHub Actions pass-role policy covering both the execution role and task role.
- `taskRoleArn` and DynamoDB environment settings in the ECS task definition.

The task execution role remains responsible for image pulls and logs. The new ECS
task role grants the Python process DynamoDB access. No AWS CLI mutation command
is run during implementation; the final report provides the account-check,
table/TTL, IAM, and verification commands for the user-operated next stage.

## Test Strategy

The autouse fixture sets `CRM_PROVIDER=mock` with `monkeypatch.setenv` before
clearing `get_settings.cache_clear()` or constructing a container. Teardown
restores the environment through `monkeypatch` and clears caches/singletons again.
This prevents a developer shell setting from causing network access.

Offline tests cover:

- Existing mock sequential IDs and the `MockCRM` compatibility alias.
- Settings default, valid DynamoDB selection, and invalid-provider validation.
- Container adapter selection and identity between `container.crm` and the
  repository held by `container.intake`; DynamoDB construction is patched so
  selection tests cannot resolve credentials or access a network.
- A Moto table with only `record_id` declared as its partition key.
- Persistence and return contracts for appointment, callback, complaint, and
  escalation records.
- Prefix/year/12-uppercase-hex ID format.
- Canonical fields, map payload, integer TTL in a reasonable window, null slot,
  normalized categories, explicit complaint priority, and canonical return-field
  precedence.
- Translation and exact exception chaining for `ClientError` and operational SDK
  errors, plus unchanged propagation for `ParamValidationError`.
- Log redaction using distinctive sentinel values for every sensitive input.
- Complete HTTP error mapping: status 503, `crm_unavailable`, safe message, trace
  ID, and no ticket ID or successful action.
- An application-source-only boundary check proving that `boto3` is imported only
  by `infrastructure/dynamodb_crm.py`; tests and metadata are excluded.

## Local Verification Gate

With `CRM_PROVIDER=mock`, run these checks before any AWS work:

```powershell
uv sync --locked
uv run ruff format .
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run python .github/tools/smoke_test.py
uv run python .github/tools/check.py --smoke
docker build -t doc-helper-ai-agent:dynamodb-test .
```

AWS provisioning remains blocked unless all applicable local checks pass. If
Docker is unavailable, report that verification gap explicitly rather than
claiming the image build succeeded.

## Documentation

Update `.github/CODEBASE_MAP.md` and `README.md` for the repository protocol,
DynamoDB adapter, provider selection, table, ECS task role, and completed CI/CD
and ECS deployment milestones. Keep the existing local RAG architecture intact.

## Out Of Scope

- Live AWS provisioning or service changes
- Git push, pull request, merge, or deployment
- Production health or persistence checks
- Numeric distributed counters
- RAG storage, sample documents, vector store changes
- PostgreSQL, RDS, Redis, ALB, frontend, or Terraform
