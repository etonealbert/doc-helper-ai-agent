"""Shared graph state passed between agent nodes."""

from __future__ import annotations

from operator import add
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict, total=False):
    """State threaded through the LangGraph workflow.

    ``actions`` uses an ``add`` reducer so each node can append its own
    :class:`ActionResult` without clobbering earlier ones.
    """

    # Inputs
    message: str
    user_id: str
    session_id: str
    trace_id: str

    # Derived
    classification: str
    safety: dict[str, Any]
    requires_human: bool
    route: str
    availability: dict[str, Any]

    # Outputs
    actions: Annotated[list[dict[str, Any]], add]
    sources: list[str]
    response_message: str
