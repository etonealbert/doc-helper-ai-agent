"""Chat route: the main agent entry point."""

from __future__ import annotations

from fastapi import APIRouter

from doc_helper_ai_agent.agent.graph import run_agent
from doc_helper_ai_agent.core.errors import AgentExecutionError, DocHelperError
from doc_helper_ai_agent.core.logging import get_logger, get_trace_id
from doc_helper_ai_agent.domain.enums import Classification
from doc_helper_ai_agent.schemas.chat import ChatRequest, ChatResponse
from doc_helper_ai_agent.schemas.tools import ActionResult

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Accept a user message, run the agent workflow, return a structured reply."""
    trace_id = get_trace_id()
    logger.info(
        "Chat request user=%s session=%s len=%d",
        request.user_id,
        request.session_id,
        len(request.message),
    )
    try:
        state = run_agent(
            message=request.message,
            user_id=request.user_id,
            session_id=request.session_id,
            trace_id=trace_id,
            locale=request.locale,
        )
    except DocHelperError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Agent execution failed")
        raise AgentExecutionError("The assistant failed to process the request.") from exc

    actions = [ActionResult.model_validate(a) for a in state.get("actions", [])]
    return ChatResponse(
        message=state.get("response_message", ""),
        classification=Classification(state["classification"]),
        actions=actions,
        requires_human=state.get("requires_human", False),
        sources=state.get("sources", []),
        trace_id=trace_id,
        locale=request.locale,
    )
