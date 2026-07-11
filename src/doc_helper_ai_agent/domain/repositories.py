"""Domain repository interfaces."""

from __future__ import annotations

from typing import Any, Protocol


class CRMRepository(Protocol):
    """Persistence operations required by CRM intake workflows."""

    def create_appointment_request(
        self,
        *,
        user_id: str,
        specialty: str,
        preferred_day: str | None,
        slot: dict[str, Any] | None,
        notes: str = "",
    ) -> dict[str, Any]: ...

    def create_callback_request(
        self,
        *,
        user_id: str,
        reason: str,
        priority: str = "normal",
    ) -> dict[str, Any]: ...

    def create_complaint_ticket(
        self,
        *,
        user_id: str,
        summary: str,
    ) -> dict[str, Any]: ...

    def create_human_escalation_ticket(
        self,
        *,
        user_id: str,
        reason: str,
        categories: list[str] | None = None,
        priority: str = "high",
    ) -> dict[str, Any]: ...
