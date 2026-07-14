"""Build, compile, and run the LangGraph agent workflow.

Flow::

    START
      -> classify_request
      -> safety_check
      -> route_request
           |-- escalate ---> escalate_to_human --------------\\
           |-- rag --------> answer_with_rag ----------------|
           |-- appointment-> check_availability              |
           |                     -> create_intake_or_callback|
           |-- complaint --> create_intake_or_callback ------|
                                                             v
                                                       final_response --> END
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from doc_helper_ai_agent.agent import nodes
from doc_helper_ai_agent.agent.state import AgentState
from doc_helper_ai_agent.core.logging import get_logger
from doc_helper_ai_agent.domain.enums import Locale

logger = get_logger(__name__)


def _route_selector(state: AgentState) -> str:
    return state.get("route", "escalate")


def build_graph():
    """Construct and compile the agent :class:`StateGraph`."""
    graph = StateGraph(AgentState)

    graph.add_node("classify_request", nodes.classify_request)
    graph.add_node("safety_check", nodes.safety_check)
    graph.add_node("route_request", nodes.route_request)
    graph.add_node("answer_with_rag", nodes.answer_with_rag)
    graph.add_node("check_availability", nodes.check_availability)
    graph.add_node("create_intake_or_callback", nodes.create_intake_or_callback)
    graph.add_node("escalate_to_human", nodes.escalate_to_human)
    graph.add_node("final_response", nodes.final_response)

    graph.add_edge(START, "classify_request")
    graph.add_edge("classify_request", "safety_check")
    graph.add_edge("safety_check", "route_request")
    graph.add_conditional_edges(
        "route_request",
        _route_selector,
        {
            "escalate": "escalate_to_human",
            "rag": "answer_with_rag",
            "appointment": "check_availability",
            "complaint": "create_intake_or_callback",
        },
    )
    graph.add_edge("check_availability", "create_intake_or_callback")
    graph.add_edge("create_intake_or_callback", "final_response")
    graph.add_edge("answer_with_rag", "final_response")
    graph.add_edge("escalate_to_human", "final_response")
    graph.add_edge("final_response", END)

    return graph.compile()


_compiled = None


def get_agent():
    """Return the compiled agent, building it once per process."""
    global _compiled
    if _compiled is None:
        _compiled = build_graph()
    return _compiled


def run_agent(
    *,
    message: str,
    user_id: str,
    session_id: str,
    trace_id: str,
    locale: Locale = Locale.ES,
) -> dict[str, Any]:
    """Execute the agent workflow and return the final state."""
    initial: AgentState = {
        "message": message,
        "user_id": user_id,
        "session_id": session_id,
        "trace_id": trace_id,
        "locale": locale.value,
        "actions": [],
        "sources": [],
    }
    logger.info("Running agent for user=%s session=%s", user_id, session_id)
    return get_agent().invoke(initial)
