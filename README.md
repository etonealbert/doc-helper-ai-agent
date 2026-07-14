# Doc Helper AI Agent

A local-first, production-style **AI agent backend** for document Q&A and
clinic-style operations (appointments, callbacks, escalations). Inspired by a
dental clinic front-desk assistant, it demonstrates a clean, agentic workflow
built with **FastAPI** and **LangGraph** that runs **fully offline in
deterministic mock mode** — no API key required.

> ⚠️ **Disclaimer:** This is a **demo/portfolio project**. It is **not a medical
> tool** and must never be used for diagnosis, prescription, or treatment
> advice. It is intended only for **fake demonstration data**; do not submit
> real patient data.

---

## Why this project exists

Most "AI chatbot" demos are a single prompt to an LLM. Real assistants need
**structure**: intent classification, safety guardrails, tool use, retrieval
with citations, human-in-the-loop escalation, logging, and tests. This project
shows that architecture end-to-end in a way that is easy to run, easy to demo,
and easy to extend toward a real cloud deployment.

## Features

- 🧠 **Agentic workflow** with LangGraph (classify → safety → route → act → respond)
- 🗂️ **Intent classification** into 7 categories with deterministic keyword mode
  and optional LLM mode
- 📚 **Local RAG** over markdown docs with **source citations**
- 🛡️ **Safety service** that detects pain/bleeding/emergencies/diagnosis requests
  and **escalates to a human** instead of giving medical advice
- 🗓️ **Mock scheduling + selectable CRM storage** (in-memory or DynamoDB)
- 🧾 **Structured JSON responses** with an auditable list of actions taken
- 🌐 **English and Spanish** classification, safety, scheduling, and RAG responses,
  with Spanish as the API default
- 🔎 **Per-request `trace_id`** propagated through logs and responses
- ✅ **Tests** that pass offline with no API key
- 🧱 **Clean architecture**: clear separation of API / agent / services /
  infrastructure

## Tech stack

| Concern            | Choice                                  |
| ------------------ | --------------------------------------- |
| Language           | Python 3.12                             |
| Web framework      | FastAPI + Uvicorn                       |
| Data validation    | Pydantic v2 / pydantic-settings         |
| Agent orchestration| LangGraph                               |
| LLM (optional)     | OpenAI SDK (mock mode by default)       |
| Vector store       | Local in-memory (Chroma-ready)          |
| Testing            | pytest + httpx                          |
| Linting            | ruff                                    |
| Packaging / env    | uv                                      |
| Infrastructure     | Terraform (existing-resource adoption)  |

## Architecture

```mermaid
flowchart TD
    Client[Client] -->|POST /api/chat| API[FastAPI + trace_id middleware]
    API --> Agent[LangGraph Agent]

    subgraph Agent Workflow
        C[classify_request] --> S[safety_check]
        S --> R[route_request]
        R -->|escalate| E[escalate_to_human]
        R -->|rag| RAG[answer_with_rag]
        R -->|appointment| AV[check_availability]
        AV --> IN[create_intake_or_callback]
        R -->|complaint| IN
        E --> F[final_response]
        RAG --> F
        IN --> F
    end

    RAG -.-> VS[(Local Vector Store)]
    AV -.-> SCH[(Mock Schedule)]
    IN -.-> SELECTED[Container.crm: selected CRMRepository]
    E -.-> SELECTED

    CONFIG{CRM_PROVIDER}
    CONFIG -->|mock, mutually exclusive| MOCK[(In-memory Mock Adapter)]
    CONFIG -->|dynamodb, mutually exclusive| DDB[(DynamoDB Adapter)]
    MOCK --> SELECTED
    DDB --> SELECTED
    F -->|structured JSON| API
```

At startup, `dependencies.Container` follows exactly one `CRM_PROVIDER` branch and
wires that adapter as the single `Container.crm` repository used by intake requests.

### Layout

```
src/doc_helper_ai_agent/
  main.py            # FastAPI app + trace_id middleware + lifespan
  dependencies.py    # composition root (shared singletons)
  api/routes/        # health, chat, documents
  core/              # config, logging, errors
  schemas/           # request/response models
  domain/            # enums, internal models, repository protocols
  services/          # rag, document_loader, intake, safety
  agent/             # graph, nodes, state, prompts
  tools/             # appointment, crm, knowledge, escalation
  infrastructure/    # vector_store, mock_crm, dynamodb_crm, mock_schedule
data/sample_docs/    # fake clinic docs used by RAG
tests/               # pytest suite (offline)
infra/terraform/     # bootstrap state + adopt the existing dev AWS resources
```

## Local setup

Prerequisites: Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run uvicorn doc_helper_ai_agent.main:app --reload
```

The API is served at `http://localhost:8000` (interactive docs at `/docs`).

Copy the example environment file if you want to customise settings (optional —
the defaults run fully offline):

```bash
cp .env.example .env
```

Local runs use the in-memory CRM by default. CRM persistence is configured with:

| Variable | Local default | Purpose |
| -------- | ------------- | ------- |
| `CRM_PROVIDER` | `mock` | Select `mock` or `dynamodb` in the composition root |
| `DYNAMODB_TABLE_NAME` | `doc-helper-records` | DynamoDB table used by the persistent adapter |
| `AWS_REGION` | `us-east-1` | Region used to construct the DynamoDB resource |
| `CRM_RECORD_TTL_DAYS` | `90` | Retention period used to calculate each record's TTL |

`CRM_PROVIDER=mock` remains deterministic, offline, and process-local. Selecting
`dynamodb` does not fall back to mock storage when AWS is unavailable; operational
SDK failures use the API's `503 crm_unavailable` error contract.

## Run with Docker

The image builds with `uv` in a multi-stage build, runs as a non-root user, and
includes a health check. It runs fully offline in mock mode by default.

```bash
# Using docker compose (recommended)
docker compose up --build          # build + run at http://localhost:8000
docker compose up -d               # detached
docker compose logs -f api         # follow logs
docker compose down                # stop + remove

# Or with plain docker
docker build -t doc-helper-ai-agent .
docker run --rm -p 8000:8000 doc-helper-ai-agent
```

To enable the real OpenAI paths, create a `.env` (see `.env.example`), set
`ENABLE_MOCK_LLM=false` and `OPENAI_API_KEY=...`, then uncomment `env_file` in
[docker-compose.yml](docker-compose.yml).

## API examples

### Health

```bash
curl http://localhost:8000/health
```

```json
{ "status": "ok", "service": "doc-helper-ai-agent", "version": "0.1.0" }
```

### Chat — Spanish by default

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{ "message": "¿Cuánto cuesta el blanqueamiento dental?" }'
```

Omitting `locale` selects Spanish. Set `"locale": "en"` for an English response;
any other explicit locale is rejected with `422`. Intent codes, tool names,
statuses, and specialty values remain stable English machine identifiers.

### Chat — appointment request in English

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I need to book an appointment for tooth whitening next Friday",
    "user_id": "demo-user",
    "session_id": "demo-session",
    "locale": "en"
  }'
```

```json
{
  "message": "A demonstration slot is available for whitening with Dr. Chloe Nguyen on Friday at 09:30. Appointment request APPT-2026-0001 was recorded; the slot is not reserved or confirmed until the team contacts you.",
  "classification": "appointment_request",
  "actions": [
    { "tool": "check_availability", "status": "success", "result": {} },
    { "tool": "create_appointment_request", "status": "success", "result": {} }
  ],
  "requires_human": false,
  "sources": [],
  "trace_id": "…",
  "locale": "en"
}
```

### Chat — emergency (escalates, never diagnoses)

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{ "message": "I have severe pain and my gum is bleeding", "locale": "en" }'
```

`requires_human` will be `true` and an `escalate_to_human` action (`ESC-…`
ticket) is created.

### PowerShell (Windows)

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/chat `
  -ContentType 'application/json' `
  -Body '{ "message": "What are your opening hours?", "user_id": "demo-user", "locale": "en" }'
```

### Documents

```bash
curl http://localhost:8000/api/documents
curl -X POST http://localhost:8000/api/documents/search \
  -H "Content-Type: application/json" \
  -d '{ "query": "política de cancelación", "locale": "es" }'
```

## Agent workflow

| Node                        | Responsibility                                            |
| --------------------------- | -------------------------------------------------------- |
| `classify_request`          | Assign one of 7 intent labels                            |
| `safety_check`              | Detect clinical risk / out-of-scope requests             |
| `route_request`             | Decide route: escalate / rag / appointment / complaint   |
| `answer_with_rag`           | Answer from the knowledge base with citations            |
| `check_availability`        | Look up slots in the mock schedule                       |
| `create_intake_or_callback` | Create appointment/callback/complaint records            |
| `escalate_to_human`         | Create a human-escalation ticket                         |
| `final_response`            | Compose the user-facing message                          |

**Routing rules**

- Emergency / pain / diagnosis-like messages → **safety → human escalation**
- Pricing / policy / service / general questions → **RAG**
- Appointment requests → **mock schedule + intake**
- Complaints → **complaint ticket + human follow-up**
- Unknown / low-confidence → **escalate**

**Classifications:** `appointment_request`, `pricing_question`,
`document_question`, `emergency_or_pain`, `complaint`, `general_question`,
`human_escalation`.

## Safety design

The agent is explicitly **not** a medical tool. The safety service flags
messages mentioning severe pain, bleeding, swelling, fever, trauma, diagnosis
requests, medication/prescription questions, or emergencies. For any such
message the agent:

1. **Avoids diagnosis or treatment advice.**
2. **Recommends contacting a professional / clinic** (and emergency services if
   life-threatening).
3. **Creates a callback / escalation** and sets `requires_human = true`.

## Mock mode vs. real LLM

By default (`ENABLE_MOCK_LLM=true`, no `OPENAI_API_KEY`) everything is
deterministic and offline: keyword classification and keyword RAG retrieval. Set
`ENABLE_MOCK_LLM=false`, `LLM_PROVIDER=openai`, and provide `OPENAI_API_KEY` to
enable LLM classification, embedding-based retrieval, and LLM answer synthesis.

CRM provider selection is independent of LLM mode. Changing `CRM_PROVIDER` does not
change the local document loader, vector store, retrieval, citations, or RAG flow.
Both mock and LLM paths propagate the selected locale. The local corpus contains
matching English and Spanish fictional documents, and retrieval is filtered by
locale so responses do not mix languages.

## DynamoDB persistence and ECS roles

The DynamoDB adapter stores one canonical item per intake operation. Every item has
`record_id`, `record_type`, `user_id`, `status`, `priority`, `created_at`,
`updated_at`, an operation-specific `payload` map, and numeric `expires_at` TTL.
Persistent IDs use `<PREFIX>-<UTC_YEAR>-<12 uppercase UUID hex characters>` (for
example, `APPT-2026-A1B2C3D4E5F6`); local mock IDs remain sequential.

The checked-in ECS task definition is prepared to select DynamoDB. Its roles have
separate responsibilities:

- `DocHelperEcsTaskRole` is assumed by the running application and receives only
  the DynamoDB `PutItem` permission in
  [`.aws/iam/doc-helper-dynamodb-policy.json`](.aws/iam/doc-helper-dynamodb-policy.json).
- `ecsTaskExecutionRole` is used by ECS to pull the image and publish task logs; it
  is not the application's DynamoDB identity.

The IAM files are deployment artifacts, not evidence that AWS resources were
provisioned. Use the trust-policy artifact as `DocHelperEcsTaskRole`'s trust
relationship and attach the DynamoDB permissions as a named inline policy. Apply
[`github-actions-passrole-policy.json`](.aws/iam/github-actions-passrole-policy.json)
as an **additive, named inline policy** on the existing
`GitHubActionsDeployRole`; do not replace that role's unrelated policies. This lets
the existing deployment workflow pass both ECS roles when registering the prepared
task definition.

## Terraform adoption

Terraform configuration under [`infra/terraform/`](infra/terraform/) is an
adoption/import project for the existing live AWS infrastructure, not a request
to recreate it. The separate `bootstrap` root stack creates the private,
versioned S3 backend. The `environments/dev` root stack uses declarative import
blocks for the existing ECR, ECS, DynamoDB, CloudWatch, security group, and IAM
resources.

**Status:** configuration is complete, but live adoption is not. Adoption is
complete only after the imports-only saved plan is applied and a second
`terraform plan -detailed-exitcode` exits `0` with no changes. DynamoDB live
verification remains separate and requires creating a fake record through the
deployed API and reading it from the live table.

The ownership boundary prevents Terraform and application CD from changing the
same mutable deployment properties:

| Terraform owns | GitHub Actions application CD owns |
| --- | --- |
| ECR repository and lifecycle policy | Docker builds and immutable Git SHA tags |
| ECS cluster and service baseline | Task-definition revisions and ECS deployments |
| ECS security group | Public task-IP discovery and health checks |
| CloudWatch log group | Route 53 A-record updates |
| DynamoDB table and TTL | Application release cadence |
| Application IAM roles/policies and remote state | Checked-in `.aws/ecs-task-definition.json` |

Terraform intentionally does not define an ECS task definition or the changing
`api.albertlukmanovlabs.lol` A record. The ECS service ignores
`task_definition` drift because [`deploy.yml`](.github/workflows/deploy.yml)
deploys each immutable revision. Existing public subnet IDs and the VPC ID are
inputs; no custom VPC, ALB, NAT Gateway, or private subnet architecture is added.

See the [dev adoption guide](infra/terraform/environments/dev/README.md) for
read-only AWS discovery commands, exact import IDs, and the mandatory safety
gate: the first applyable dev plan must contain imports only with `0 to add,
0 to change, 0 to destroy`. The separate
[`terraform.yml`](.github/workflows/terraform.yml) workflow only formats and
validates Terraform; it never applies infrastructure.

The deployment role's complete permission inventory must be preserved during
adoption. In addition to the Terraform-represented `iam:PassRole` permission,
[`deploy.yml`](.github/workflows/deploy.yml) requires ECR authentication/image
push, ECS registration/deployment and task discovery, EC2 network-interface
discovery, and Route 53 record update/waiter permissions. Exact actions and
resource scopes are documented in the
[dev adoption guide](infra/terraform/environments/dev/README.md#github-deployment-role-permissions).

## Developer experience

```bash
uv sync                                                   # install deps
uv run uvicorn doc_helper_ai_agent.main:app --reload      # run the API
uv run pytest                                             # run tests (offline)
uv run ruff format --check .                              # check formatting
uv run ruff check .                                       # lint
```

## Roadmap

- [ ] **Frontend** (chat UI)
- [x] **CI/CD** (lint, test, container build, and ECS deployment workflow)
- [x] **ECS deployment** workflow and task-definition integration
- [x] **DynamoDB CRM persistence** implemented and prepared for deployment
- [x] **Terraform adoption configuration** with remote state, imports, and CI validation
- [ ] **Terraform live adoption** after an imports-only plan and no-op verification
- [ ] **AWS DynamoDB live persistence verification**
- [ ] **Real vector DB** (Chroma persistence / managed vector store)
- [ ] **Auth** (API keys / OAuth) and rate limiting
- [ ] **Observability** (OpenTelemetry traces, metrics, dashboards)
- [x] **English/Spanish support** with Spanish-default API responses

## Disclaimer

This is a demonstration project for portfolio purposes. It does **not** provide
medical advice, diagnosis, or treatment. It is intended only for **fake
demonstration data**; users must not submit real patient data.
