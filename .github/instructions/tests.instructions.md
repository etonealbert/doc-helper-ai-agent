---
description: "Use when writing or editing pytest tests. Covers offline determinism, singleton resets, and the FastAPI test client."
name: "Testing Conventions"
applyTo: "tests/**"
---

# Testing Conventions

- Tests must pass **offline with no `OPENAI_API_KEY`** (`uv run pytest`).
- Keep assertions deterministic — rely on mock mode (keyword classification and
  keyword RAG retrieval), never on live model output.
- Singletons are reset before every test by the autouse `reset_singletons`
  fixture in [conftest.py](../../tests/conftest.py). If you add a new singleton,
  add its `reset_*` helper and call it there.
- Use the `client` fixture (FastAPI `TestClient`) for HTTP-level tests.
- For CRM ID assertions, construct a fresh `MockCRM` so counters start at `0001`,
  or match with a regex like `r"APPT-\d{4}-0001"`.
- Prefer testing behaviour through `run_agent(...)` or the API over reaching into
  private helpers.

## Example

```python
def test_pricing_uses_rag(client):
    resp = client.post("/api/chat", json={"message": "How much is whitening?"})
    data = resp.json()
    assert data["classification"] == "pricing_question"
    assert data["sources"]
```
