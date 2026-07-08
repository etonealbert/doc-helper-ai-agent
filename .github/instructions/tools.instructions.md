---
description: "Use when adding or editing agent tools (src/doc_helper_ai_agent/tools). Covers the ActionResult contract and wiring through the container."
name: "Tool Authoring"
applyTo: "src/doc_helper_ai_agent/tools/**"
---

# Tool Authoring Guidelines

Tools are thin wrappers over services/infrastructure that produce a uniform,
serialisable audit record.

- Every tool returns an
  [ActionResult](../../src/doc_helper_ai_agent/schemas/tools.py):
  `ActionResult(tool="<name>", status=ToolStatus.SUCCESS, result={...})`.
- The `result` dict must be JSON-serialisable (plain dicts/lists/str/int/bool).
- Access shared services via `from doc_helper_ai_agent.dependencies import get_container`
  and `get_container().<service>`. Do not construct services directly.
- Keep tools deterministic in mock mode; do not call the network unless a service
  behind them is explicitly gated by settings.
- Set `status=ToolStatus.ERROR` and put a `"message"` in `result` on failure —
  never raise out of a tool used by a node.

## Template

```python
from __future__ import annotations

from doc_helper_ai_agent.dependencies import get_container
from doc_helper_ai_agent.domain.enums import ToolStatus
from doc_helper_ai_agent.schemas.tools import ActionResult


def do_thing(*, user_id: str) -> ActionResult:
    container = get_container()
    record = container.intake.create_callback(user_id=user_id, reason="...")
    return ActionResult(
        tool="do_thing",
        status=ToolStatus.SUCCESS,
        result={"ticket_id": record["id"], "status": record["status"]},
    )
```

After adding a tool, call it from a node and add a routing test.
