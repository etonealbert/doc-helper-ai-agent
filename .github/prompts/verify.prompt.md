---
description: "Run the project's quality gate: lint, tests, and an offline smoke test of the API."
name: "Verify Project"
agent: "agent"
tools: [runCommands]
---

Verify the project is healthy. Run these and report results concisely; fix any
failures you introduced.

1. Lint: `uv run ruff check .`
2. Tests (must pass offline, no API key): `uv run pytest`
3. Offline smoke test of the API and agent:
   `uv run python .github/tools/smoke_test.py`

If a command is unavailable in the environment, say so and fall back to static
analysis (read the code and reason about correctness). Do not weaken tests or the
safety logic to make checks pass.
