"""CRM tools: create appointment, callback, and complaint records."""

from __future__ import annotations

from typing import Any

from doc_helper_ai_agent.core.logging import get_logger
from doc_helper_ai_agent.dependencies import get_container
from doc_helper_ai_agent.domain.enums import ToolStatus
from doc_helper_ai_agent.domain.models import TimeSlot
from doc_helper_ai_agent.schemas.tools import ActionResult

logger = get_logger(__name__)


def create_appointment_request(
    *,
    user_id: str,
    availability: dict[str, Any],
    notes: str = "",
) -> ActionResult:
    """Create an appointment request from a prior availability result."""
    container = get_container()
    slots = availability.get("slots") or []
    slot = TimeSlot(**slots[0]) if slots else None
    record = container.intake.create_appointment(
        user_id=user_id,
        specialty=availability.get("specialty", "general_dentistry"),
        preferred_day=availability.get("preferred_day"),
        slot=slot,
        notes=notes,
    )
    return ActionResult(
        tool="create_appointment_request",
        status=ToolStatus.SUCCESS,
        result={
            "ticket_id": record["id"],
            "status": record["status"],
            "proposed_slot": record["slot"],
        },
    )


def create_callback_request(
    *,
    user_id: str,
    reason: str,
    priority: str = "normal",
) -> ActionResult:
    """Create a callback request for the user."""
    container = get_container()
    record = container.intake.create_callback(
        user_id=user_id, reason=reason, priority=priority
    )
    return ActionResult(
        tool="create_callback_request",
        status=ToolStatus.SUCCESS,
        result={"ticket_id": record["id"], "status": record["status"], "priority": priority},
    )


def create_complaint_ticket(*, user_id: str, summary: str) -> ActionResult:
    """Create a complaint ticket for follow-up by staff."""
    container = get_container()
    record = container.intake.create_complaint(user_id=user_id, summary=summary)
    return ActionResult(
        tool="create_complaint_ticket",
        status=ToolStatus.SUCCESS,
        result={"ticket_id": record["id"], "status": record["status"]},
    )
