"""In-memory mock CRM.

Generates deterministic, human-readable record IDs (e.g. ``APPT-2026-0001``)
and stores records in memory. No real patient data is ever persisted.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Any

from doc_helper_ai_agent.core.logging import get_logger
from doc_helper_ai_agent.domain.enums import TicketType

logger = get_logger(__name__)

_PREFIX: dict[TicketType, str] = {
    TicketType.APPOINTMENT: "APPT",
    TicketType.CALLBACK: "CALLBACK",
    TicketType.COMPLAINT: "COMPLAINT",
    TicketType.ESCALATION: "ESC",
}


class MockCRMRepository:
    """A minimal, thread-safe, in-memory CRM."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[TicketType, int] = dict.fromkeys(TicketType, 0)
        self._records: dict[str, dict[str, Any]] = {}

    def _next_id(self, ticket_type: TicketType) -> str:
        year = datetime.now(UTC).year
        self._counters[ticket_type] += 1
        seq = self._counters[ticket_type]
        return f"{_PREFIX[ticket_type]}-{year}-{seq:04d}"

    def _create(self, ticket_type: TicketType, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            record_id = self._next_id(ticket_type)
            record = {
                "id": record_id,
                "type": ticket_type.value,
                "created_at": datetime.now(UTC).isoformat(),
                **payload,
            }
            self._records[record_id] = record
        logger.info("CRM created %s record %s", ticket_type.value, record_id)
        return record

    def create_appointment_request(
        self,
        *,
        user_id: str,
        specialty: str,
        preferred_day: str | None,
        slot: dict[str, Any] | None,
        notes: str = "",
    ) -> dict[str, Any]:
        return self._create(
            TicketType.APPOINTMENT,
            {
                "user_id": user_id,
                "specialty": specialty,
                "preferred_day": preferred_day,
                "slot": slot,
                "notes": notes,
                "status": "pending_confirmation",
            },
        )

    def create_callback_request(
        self,
        *,
        user_id: str,
        reason: str,
        priority: str = "normal",
    ) -> dict[str, Any]:
        return self._create(
            TicketType.CALLBACK,
            {"user_id": user_id, "reason": reason, "priority": priority, "status": "open"},
        )

    def create_complaint_ticket(
        self,
        *,
        user_id: str,
        summary: str,
    ) -> dict[str, Any]:
        return self._create(
            TicketType.COMPLAINT,
            {"user_id": user_id, "summary": summary, "status": "open"},
        )

    def create_human_escalation_ticket(
        self,
        *,
        user_id: str,
        reason: str,
        categories: list[str] | None = None,
        priority: str = "high",
    ) -> dict[str, Any]:
        return self._create(
            TicketType.ESCALATION,
            {
                "user_id": user_id,
                "reason": reason,
                "categories": categories or [],
                "priority": priority,
                "status": "open",
            },
        )

    def get(self, record_id: str) -> dict[str, Any] | None:
        return self._records.get(record_id)

    def all(self) -> list[dict[str, Any]]:
        return list(self._records.values())


MockCRM = MockCRMRepository


_crm: MockCRMRepository | None = None


def get_crm() -> MockCRMRepository:
    """Return the process-wide mock CRM repository singleton."""
    global _crm
    if _crm is None:
        _crm = MockCRMRepository()
    return _crm


def reset_crm() -> None:
    """Drop the singleton (used by tests)."""
    global _crm
    _crm = None
