# Doc Helper AI Agent — Project Guidelines

Local-first, mock-mode-by-default AI agent backend (FastAPI + LangGraph). The app
must always run and pass tests **offline without an API key**.

> **Start here:** For a full map of the codebase — directory tree, every module's
> purpose and key symbols, the request lifecycle, and "where to edit for X" —
> read [CODEBASE_MAP.md](CODEBASE_MAP.md). Keep it updated when structure changes.

## Required documentation context

Before changing code, build context from these sources in order:

1. [CODEBASE_MAP.md](CODEBASE_MAP.md) — authoritative module map, dependency
   direction, request flow, public symbols, configuration, and change recipes.
2. [README.md](../README.md) — user-facing architecture, setup, API examples,
   deployment status, persistence behavior, safety boundaries, and roadmap.
3. [DynamoDB CRM design](../docs/superpowers/specs/2026-07-10-dynamodb-crm-design.md)
   — approved repository boundary, record contract, error handling, IAM model,
   and explicit out-of-scope work.
4. [DynamoDB CRM implementation plan](../docs/superpowers/plans/2026-07-10-dynamodb-crm-implementation.md)
   — exact files, test coverage, local verification gates, and the operator-run
   AWS handoff. AWS provisioning and deployment commands are not agent defaults.
5. The matching file under [instructions/](instructions/) before editing Python,
   tests, tools, agent workflow, or safety-sensitive behavior.

Treat the current code and tests as the runtime source of truth if documentation
has drifted. Update `CODEBASE_MAP.md` and `README.md` whenever architecture,
configuration, public modules, deployment artifacts, or supported behavior changes.
Do not infer that local AWS artifacts have been applied: distinguish implemented
code from provisioned infrastructure and verified production behavior.

## Build, run, and test

- Install deps: `uv sync`
- Run API: `uv run uvicorn doc_helper_ai_agent.main:app --reload`
- Test (must stay green offline): `uv run pytest`
- Lint: `uv run ruff check .`
- App object: `doc_helper_ai_agent.main:app` (package lives in `src/`).
- Container: `docker compose up --build` (multi-stage uv image, runs mock mode offline).

## Architecture (layered — respect the boundaries)

```
api/routes  -> HTTP only (FastAPI routers)
agent       -> LangGraph workflow (graph, nodes, state, prompts)
tools       -> thin wrappers returning ActionResult
services    -> business logic (rag, intake, safety, document_loader)
infrastructure -> mock_crm, mock_schedule, vector_store (swappable adapters)
domain      -> enums + internal models
schemas     -> API request/response models
core        -> config, logging, errors
```

- Dependency direction is one-way: `api → agent → tools → services → infrastructure`.
  Never import "upward" (e.g. services must not import agent/tools).
- Shared singletons come from [dependencies.py](../src/doc_helper_ai_agent/dependencies.py)
  via `get_container()`. Add new shared deps there, not as scattered globals.

## Agent workflow

- Graph: `classify_request → safety_check → route_request →` (conditional)
  `{escalate_to_human | answer_with_rag | check_availability→create_intake_or_callback | create_intake_or_callback} → final_response`.
- See [nodes.py](../src/doc_helper_ai_agent/agent/nodes.py) and [graph.py](../src/doc_helper_ai_agent/agent/graph.py).
- `AgentState.actions` uses an `operator.add` reducer; always initialize `actions=[]`
  in the initial state and return `{"actions": [action.model_dump()]}` from nodes.

## Conventions

- Python 3.12, type hints where practical, `from __future__ import annotations` at top.
- Pydantic v2 models for all API and domain data; enums are `StrEnum`.
- Every tool returns an [ActionResult](../src/doc_helper_ai_agent/schemas/tools.py).
- Keep **mock mode deterministic**: no network calls unless `settings.use_real_llm`
  / `settings.use_embeddings` are true. Guard OpenAI usage behind those flags with a
  keyword/mock fallback.
- Log via `core.logging.get_logger(__name__)`. Never log secrets or full API keys.
- Tests reset singletons through the `conftest.py` autouse fixture — add a
  `reset_*` helper when you introduce a new singleton.

## Safety (non-negotiable)

This is **not** a medical tool. It must never diagnose, prescribe, or give treatment
advice. Risk signals (pain, bleeding, swelling, fever, trauma, diagnosis/medication
requests, emergencies) must route to human escalation with `requires_human=true`.
See [safety_service.py](../src/doc_helper_ai_agent/services/safety_service.py) and the
`safety.instructions.md` guidance before touching that logic.
