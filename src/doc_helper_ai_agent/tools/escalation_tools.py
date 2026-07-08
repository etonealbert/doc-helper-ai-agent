"""Escalation tool: hand off to a human via a CRM escalation ticket."""

from __future__ import annotations

from doc_helper_ai_agent.core.logging import get_logger
from doc_helper_ai_agent.dependencies import get_container
from doc_helper_ai_agent.domain.enums import ToolStatus
from doc_helper_ai_agent.schemas.tools import ActionResult

logger = get_logger(__name__)


def escalate_to_human(
    *,
    user_id: str,
    reason: str,
    categories: list[str] | None = None,
    priority: str = "high",
) -> ActionResult:
    """Create a human-escalation ticket."""
    container = get_container()
    record = container.intake.create_escalation(
        user_id=user_id,
        reason=reason,
        categories=categories,
        priority=priority,
    )
    return ActionResult(
        tool="escalate_to_human",
        status=ToolStatus.SUCCESS,
        result={
            "ticket_id": record["id"],
            "status": record["status"],
            "priority": record["priority"],
            "categories": record.get("categories", []),
        },
    )
