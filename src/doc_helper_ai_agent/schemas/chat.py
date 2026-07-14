"""Chat endpoint schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from doc_helper_ai_agent.domain.enums import Classification, Locale
from doc_helper_ai_agent.schemas.tools import ActionResult


class ChatRequest(BaseModel):
    """Incoming chat message from a user/session."""

    message: str = Field(min_length=1, description="The user's natural-language message.")
    user_id: str = Field(default="anonymous", description="Stable identifier for the user.")
    session_id: str = Field(default="default", description="Conversation/session identifier.")
    locale: Locale = Field(default=Locale.ES, description="Language for the user-facing response.")


class ChatResponse(BaseModel):
    """Structured agent response."""

    message: str
    classification: Classification
    actions: list[ActionResult] = Field(default_factory=list)
    requires_human: bool = False
    sources: list[str] = Field(default_factory=list)
    trace_id: str
    locale: Locale
