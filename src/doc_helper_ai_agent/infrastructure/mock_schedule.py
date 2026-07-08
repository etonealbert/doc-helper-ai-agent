"""In-memory mock scheduling system.

Provides a deterministic set of doctors and weekly availability so appointment
flows can be demoed without a real practice-management system.
"""

from __future__ import annotations

from doc_helper_ai_agent.core.logging import get_logger
from doc_helper_ai_agent.domain.enums import Specialty
from doc_helper_ai_agent.domain.models import Doctor, TimeSlot

logger = get_logger(__name__)

_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]

_DOCTORS: list[Doctor] = [
    Doctor(
        id="doc-001",
        name="Dr. Ana Ramirez",
        specialties=[Specialty.GENERAL_DENTISTRY, Specialty.EMERGENCY],
    ),
    Doctor(
        id="doc-002",
        name="Dr. Ben Carter",
        specialties=[Specialty.ORTHODONTICS, Specialty.GENERAL_DENTISTRY],
    ),
    Doctor(
        id="doc-003",
        name="Dr. Chloe Nguyen",
        specialties=[Specialty.WHITENING, Specialty.GENERAL_DENTISTRY],
    ),
    Doctor(
        id="doc-004",
        name="Dr. David Okafor",
        specialties=[Specialty.IMPLANTS, Specialty.EMERGENCY],
    ),
]

# Deterministic "template" slots offered per specialty on each working day.
_SLOT_TEMPLATE: dict[Specialty, list[tuple[str, str]]] = {
    Specialty.GENERAL_DENTISTRY: [("09:00", "09:30"), ("11:00", "11:30"), ("14:00", "14:30")],
    Specialty.ORTHODONTICS: [("10:00", "10:45"), ("15:00", "15:45")],
    Specialty.WHITENING: [("09:30", "10:15"), ("13:00", "13:45")],
    Specialty.IMPLANTS: [("08:30", "09:30"), ("16:00", "17:00")],
    Specialty.EMERGENCY: [("08:00", "08:20"), ("12:00", "12:20"), ("17:30", "17:50")],
}


class MockSchedule:
    """Deterministic availability lookup keyed by specialty and day."""

    def __init__(self) -> None:
        self._doctors = _DOCTORS

    def list_doctors(self, specialty: Specialty | None = None) -> list[Doctor]:
        if specialty is None:
            return list(self._doctors)
        return [d for d in self._doctors if specialty in d.specialties]

    def check_availability(
        self,
        *,
        specialty: Specialty,
        preferred_day: str | None = None,
        limit: int = 3,
    ) -> list[TimeSlot]:
        """Return up to ``limit`` open slots for a specialty.

        If ``preferred_day`` matches a working weekday it is prioritised; the
        result otherwise fills across the working week deterministically.
        """
        doctors = self.list_doctors(specialty)
        if not doctors:
            return []

        days = list(_WEEKDAYS)
        if preferred_day:
            normalized = preferred_day.strip().lower()
            if normalized in days:
                days.remove(normalized)
                days.insert(0, normalized)

        template = _SLOT_TEMPLATE.get(specialty, _SLOT_TEMPLATE[Specialty.GENERAL_DENTISTRY])
        slots: list[TimeSlot] = []
        for day in days:
            for doctor in doctors:
                for start, end in template:
                    slots.append(
                        TimeSlot(
                            doctor_id=doctor.id,
                            doctor_name=doctor.name,
                            specialty=specialty,
                            day=day,
                            start_time=start,
                            end_time=end,
                        )
                    )
                    if len(slots) >= limit:
                        logger.info(
                            "Schedule found %d slot(s) for %s (preferred_day=%s)",
                            len(slots),
                            specialty.value,
                            preferred_day,
                        )
                        return slots
        return slots


_schedule: MockSchedule | None = None


def get_schedule() -> MockSchedule:
    """Return the process-wide :class:`MockSchedule` singleton."""
    global _schedule
    if _schedule is None:
        _schedule = MockSchedule()
    return _schedule


def reset_schedule() -> None:
    """Drop the singleton (used by tests)."""
    global _schedule
    _schedule = None
