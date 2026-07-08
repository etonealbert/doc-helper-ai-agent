"""Knowledge tool: answer a question from the local RAG knowledge base."""

from __future__ import annotations

from doc_helper_ai_agent.core.logging import get_logger
from doc_helper_ai_agent.dependencies import get_container
from doc_helper_ai_agent.domain.enums import ToolStatus
from doc_helper_ai_agent.schemas.tools import ActionResult

logger = get_logger(__name__)


def answer_question(question: str, top_k: int | None = None) -> ActionResult:
    """Run RAG over the knowledge base and return an answer with sources."""
    container = get_container()
    result = container.rag.answer(question, top_k=top_k)
    return ActionResult(
        tool="answer_with_rag",
        status=ToolStatus.SUCCESS,
        result={
            "answer": result.answer,
            "sources": result.sources,
            "num_chunks": len(result.chunks),
        },
    )
