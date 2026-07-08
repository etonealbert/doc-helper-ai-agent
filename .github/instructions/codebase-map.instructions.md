---
description: "Use when you need to understand the project structure, locate functionality, trace how a request flows, or figure out which file/module to change. Points to the full codebase map."
name: "Codebase Map"
---

# Codebase Map (read the full reference)

Before navigating or changing this project, read
[CODEBASE_MAP.md](../CODEBASE_MAP.md) — it documents the full directory tree,
every module's purpose and key symbols, the request lifecycle, layering rules,
and "where do I edit for X" recipes.

## Fast index (details in CODEBASE_MAP.md)

- HTTP endpoints → `src/doc_helper_ai_agent/api/routes/` (`health`, `chat`, `documents`)
- Agent workflow → `src/doc_helper_ai_agent/agent/` (`graph`, `nodes`, `state`, `prompts`)
- Tools (return `ActionResult`) → `src/doc_helper_ai_agent/tools/`
- Business logic → `src/doc_helper_ai_agent/services/` (`rag`, `safety`, `intake`, `document_loader`)
- Mock adapters → `src/doc_helper_ai_agent/infrastructure/` (`mock_crm`, `mock_schedule`, `vector_store`)
- Config/logging/errors → `src/doc_helper_ai_agent/core/`
- Enums & internal models → `src/doc_helper_ai_agent/domain/`
- API models → `src/doc_helper_ai_agent/schemas/`
- Shared singletons → `src/doc_helper_ai_agent/dependencies.py` (`get_container()`)
- Tests → `tests/` (offline; singletons reset in `conftest.py`)
- Knowledge base → `data/sample_docs/`

## Non-negotiables

- Respect one-way layering: `api → agent → tools → services → infrastructure`.
- Keep mock mode deterministic (no network unless `settings.use_real_llm` / `use_embeddings`).
- Not a medical tool — risk signals escalate with `requires_human=true`.
- Update `CODEBASE_MAP.md` when you add/rename/remove modules or public functions.
