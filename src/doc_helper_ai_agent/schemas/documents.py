"""Document endpoint schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentInfo(BaseModel):
    """Summary of a single indexed source document."""

    source: str
    chunks: int


class DocumentsResponse(BaseModel):
    """Listing of indexed documents in the knowledge base."""

    documents: list[DocumentInfo] = Field(default_factory=list)
    total_documents: int = 0
    total_chunks: int = 0


class DocumentSearchRequest(BaseModel):
    """Direct RAG query against the knowledge base."""

    query: str = Field(min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=10)


class DocumentSearchResponse(BaseModel):
    """RAG answer plus provenance for a direct search."""

    answer: str
    sources: list[str] = Field(default_factory=list)
    trace_id: str
