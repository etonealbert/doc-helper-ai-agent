---
description: "Use when writing or editing Python in this repo. Covers style, typing, Pydantic v2, logging, and mock-mode determinism."
name: "Python Conventions"
applyTo: "**/*.py"
---

# Python Conventions

- Start modules with `from __future__ import annotations`.
- Target Python 3.12; use modern typing (`X | None`, `list[str]`, `StrEnum`).
- Prefer small, pure functions. Add type hints on public functions.
- Validate data with Pydantic v2 models (`model_config`, `Field`, `model_dump`).
- Get loggers via `from doc_helper_ai_agent.core.logging import get_logger`
  then `logger = get_logger(__name__)`. Never log secrets or full API keys.
- Read config through `core.config.get_settings()`; do not read `os.environ` directly.
- Keep **mock mode deterministic**: any OpenAI/network call must be guarded by
  `settings.use_real_llm` or `settings.use_embeddings` and fall back to a
  keyword/mock path inside a `try/except` that logs a warning.
- Match existing formatting; run `uv run ruff check .` before finishing.

## Example

```python
from __future__ import annotations

from doc_helper_ai_agent.core.config import get_settings
from doc_helper_ai_agent.core.logging import get_logger

logger = get_logger(__name__)


def summarize(text: str) -> str:
    settings = get_settings()
    if settings.use_real_llm:
        try:
            return _llm_summarize(text)
        except Exception as exc:  # fall back, never crash mock mode
            logger.warning("LLM summarize failed, using mock: %s", exc)
    return text[:200]
```
