# `.github/tools`

Maintenance scripts an agent (or human) can run to keep the project healthy.
All scripts work **offline in mock mode** and require no API key.

| Script | What it does | Run |
| ------ | ------------ | --- |
| [smoke_test.py](smoke_test.py) | Boots the FastAPI app in-process and exercises `/health`, `/api/chat` (pricing, appointment, emergency), and `/api/documents`. Exits non-zero on failure. | `uv run python .github/tools/smoke_test.py` |
| [check.py](check.py) | Runs the quality gate: `ruff` + `pytest` (add `--smoke` to also run the smoke test). | `uv run python .github/tools/check.py --smoke` |

These are convenience wrappers around the canonical commands:

```bash
uv run ruff check .
uv run pytest
uv run uvicorn doc_helper_ai_agent.main:app --reload
```
