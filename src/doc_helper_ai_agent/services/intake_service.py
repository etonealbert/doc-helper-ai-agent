"""Intake service.

A thin orchestration layer over the mock CRM for the different intake flows:
appointments, callbacks, complaints, and human escalations. Keeping this logic
here (rather than in the agent nodes) makes it independently testable.
"""

from __future__ import annotations

from typing import Any

from doc_helper_ai_agent.core.logging import get_logger
from doc_helper_ai_agent.domain.models import TimeSlot
from doc_helper_ai_agent.infrastructure.mock_crm import MockCRM

logger = get_logger(__name__)


class IntakeService:
    """Create CRM records for the various intake workflows."""

    def __init__(self, crm: MockCRM) -> None:
        self._crm = crm

    def create_appointment(
        self,
        *,
        user_id: str,
        specialty: str,
        preferred_day: str | None,
        slot: TimeSlot | None,
        notes: str = "",
    ) -> dict[str, Any]:
        return self._crm.create_appointment_request(
            user_id=user_id,
            specialty=specialty,
            preferred_day=preferred_day,
            slot=slot.model_dump() if slot else None,
            notes=notes,
        )

    def create_callback(
        self,
        *,
        user_id: str,
        reason: str,
        priority: str = "normal",
    ) -> dict[str, Any]:
        return self._crm.create_callback_request(
            user_id=user_id, reason=reason, priority=priority
        )

    def create_complaint(self, *, user_id: str, summary: str) -> dict[str, Any]:
        return self._crm.create_complaint_ticket(user_id=user_id, summary=summary)

    def create_escalation(
        self,
        *,
        user_id: str,
        reason: str,
        categories: list[str] | None = None,
        priority: str = "high",
    ) -> dict[str, Any]:
        return self._crm.create_human_escalation_ticket(
            user_id=user_id, reason=reason, categories=categories, priority=priority
        )


_service: IntakeService | None = None


def get_intake_service(crm: MockCRM) -> IntakeService:
    """Return the process-wide :class:`IntakeService` singleton."""
    global _service
    if _service is None:
        _service = IntakeService(crm)
    return _service


def reset_intake_service() -> None:
    """Drop the singleton (used by tests)."""
    global _service
    _service = None
