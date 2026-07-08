"""Documents route: inspect and query the local RAG knowledge base."""

from __future__ import annotations

from fastapi import APIRouter

from doc_helper_ai_agent.core.logging import get_logger, get_trace_id
from doc_helper_ai_agent.dependencies import get_container
from doc_helper_ai_agent.schemas.documents import (
    DocumentInfo,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentsResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("", response_model=DocumentsResponse)
def list_documents() -> DocumentsResponse:
    """List the documents currently indexed in the knowledge base."""
    rag = get_container().rag
    summary = rag.document_summary()
    documents = [DocumentInfo(source=source, chunks=count) for source, count in summary]
    return DocumentsResponse(
        documents=documents,
        total_documents=len(documents),
        total_chunks=sum(d.chunks for d in documents),
    )


@router.post("/search", response_model=DocumentSearchResponse)
def search_documents(request: DocumentSearchRequest) -> DocumentSearchResponse:
    """Run RAG directly against the knowledge base (bypassing the full agent)."""
    rag = get_container().rag
    result = rag.answer(request.query, top_k=request.top_k)
    return DocumentSearchResponse(
        answer=result.answer,
        sources=result.sources,
        trace_id=get_trace_id(),
    )
