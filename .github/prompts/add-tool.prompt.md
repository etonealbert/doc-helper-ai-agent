---
description: "Scaffold a new agent tool that returns an ActionResult and wire it into a node."
name: "Add Agent Tool"
argument-hint: "e.g. 'send appointment reminder' — describe the tool and its inputs"
agent: "agent"
---

Add a new agent tool to this repo following the Tool Authoring conventions.

Steps:
1. Create/extend the appropriate file in `src/doc_helper_ai_agent/tools/`
   (`appointment_tools.py`, `crm_tools.py`, `knowledge_tools.py`, or
   `escalation_tools.py`). The tool must return an
   [ActionResult](../../src/doc_helper_ai_agent/schemas/tools.py) with a
   JSON-serialisable `result` dict and use `get_container()` for services.
2. If it needs new business logic, add it to a service in
   `src/doc_helper_ai_agent/services/`, not to the tool.
3. Call the tool from the relevant node in
   [agent/nodes.py](../../src/doc_helper_ai_agent/agent/nodes.py).
4. Add a test asserting the tool appears in `state["actions"]` for the right
   message in [tests/test_agent_routing.py](../../tests/test_agent_routing.py).
5. Keep it deterministic in mock mode and run `uv run pytest` mentally against
   the change; ensure `uv run ruff check .` would pass.

The tool to add: $ARGUMENTS
