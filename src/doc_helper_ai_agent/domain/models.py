"""Internal domain models (not tied to the HTTP layer)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from doc_helper_ai_agent.domain.enums import Locale, Specialty


class Doctor(BaseModel):
    """A clinician offering one or more specialties."""

    id: str
    name: str
    specialties: list[Specialty]


class TimeSlot(BaseModel):
    """A single bookable slot returned by the schedule."""

    doctor_id: str
    doctor_name: str
    specialty: Specialty
    day: str
    start_time: str
    end_time: str


class SafetyAssessment(BaseModel):
    """Result of the safety service evaluating a user message."""

    triggered: bool = False
    categories: list[str] = Field(default_factory=list)
    reason: str = ""
    recommended_action: str = ""


class RetrievedChunk(BaseModel):
    """A chunk returned from the vector store during retrieval."""

    id: str
    text: str
    source: str
    locale: Locale
    score: float = 0.0


class RagResult(BaseModel):
    """Answer plus provenance produced by the RAG service."""

    answer: str
    sources: list[str] = Field(default_factory=list)
    chunks: list[RetrievedChunk] = Field(default_factory=list)
