"""Schemas for tool/action results embedded in responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from doc_helper_ai_agent.domain.enums import ToolStatus


class ActionResult(BaseModel):
    """The outcome of a single tool invocation performed by the agent."""

    tool: str
    status: ToolStatus
    result: dict[str, Any] = Field(default_factory=dict)
