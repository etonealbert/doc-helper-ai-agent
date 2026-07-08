---
description: "Add a new intent classification label and route it through the agent workflow."
name: "Add Classification & Route"
argument-hint: "e.g. 'insurance_question -> RAG' — label and desired route"
agent: "agent"
---

Add a new request classification and wire its routing end to end.

Steps:
1. Add the label to the `Classification` enum in
   [domain/enums.py](../../src/doc_helper_ai_agent/domain/enums.py).
2. Add keyword rules for it in `_classify_keywords` in
   [agent/nodes.py](../../src/doc_helper_ai_agent/agent/nodes.py) (mind the
   ordering — more specific/urgent checks first). Update the classifier prompt in
   [agent/prompts.py](../../src/doc_helper_ai_agent/agent/prompts.py).
3. Map it in `_decide_route`. If it needs a new destination, add a `Route` value
   and a conditional edge in
   [agent/graph.py](../../src/doc_helper_ai_agent/agent/graph.py).
4. Update `final_response` wording if the user-facing message should differ.
5. Add a routing test in
   [tests/test_agent_routing.py](../../tests/test_agent_routing.py) and, if it is
   user-facing, an API test in
   [tests/test_chat_api.py](../../tests/test_chat_api.py).

Keep mock mode deterministic. The classification/route to add: $ARGUMENTS
