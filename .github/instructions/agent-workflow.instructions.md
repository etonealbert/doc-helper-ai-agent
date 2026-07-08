---
description: "Use when adding or changing agent nodes, routing, or graph edges in the LangGraph workflow (src/doc_helper_ai_agent/agent)."
name: "Agent Workflow"
applyTo: "src/doc_helper_ai_agent/agent/**"
---

# Agent Workflow Guidelines

The workflow is a LangGraph `StateGraph` compiled once per process.

## State

- `AgentState` is a `TypedDict` in [state.py](../../src/doc_helper_ai_agent/agent/state.py).
- `actions` uses an `operator.add` reducer. Nodes append with
  `return {"actions": [action.model_dump()]}`; the initial state sets `actions=[]`.
- Plain fields (`classification`, `route`, `sources`, `response_message`,
  `requires_human`, `availability`) are replaced, not merged.

## Nodes

- Each node is a pure function `AgentState -> partial AgentState`. No side effects
  beyond calling tools/services; no printing.
- Nodes call tools (in `tools/`) — they should not talk to infrastructure directly.
- Classification runs deterministic keyword logic by default; the LLM path is
  optional and must fall back to keywords on any error.

## Routing

- Add new routes to the `Route` enum and `_decide_route` in
  [nodes.py](../../src/doc_helper_ai_agent/agent/nodes.py), then wire the
  conditional edge in [graph.py](../../src/doc_helper_ai_agent/agent/graph.py).
- Safety-triggered or low-confidence requests must route to escalation with
  `requires_human=True`.

## Adding a node — checklist

1. Implement the node function in `nodes.py`.
2. Register it with `graph.add_node(...)` and connect edges in `graph.py`.
3. Ensure it converges to `final_response`.
4. Add/extend a test in [tests/test_agent_routing.py](../../tests/test_agent_routing.py).
