"""Appointment-related tools: infer intent details and check availability."""

from __future__ import annotations

import re

from doc_helper_ai_agent.core.logging import get_logger
from doc_helper_ai_agent.dependencies import get_container
from doc_helper_ai_agent.domain.enums import Specialty, ToolStatus
from doc_helper_ai_agent.schemas.tools import ActionResult

logger = get_logger(__name__)

_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

_SPECIALTY_KEYWORDS: list[tuple[Specialty, tuple[str, ...]]] = [
    (Specialty.WHITENING, ("whitening", "whiten", "bleaching")),
    (Specialty.ORTHODONTICS, ("braces", "orthodontic", "orthodontics", "aligner", "invisalign")),
    (Specialty.IMPLANTS, ("implant", "implants")),
    (Specialty.EMERGENCY, ("emergency", "urgent")),
    (
        Specialty.GENERAL_DENTISTRY,
        ("cleaning", "checkup", "check-up", "filling", "cavity", "general"),
    ),
]


def infer_specialty(message: str) -> Specialty:
    """Best-effort mapping from free text to a bookable specialty."""
    lowered = message.lower()
    for specialty, keywords in _SPECIALTY_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return specialty
    return Specialty.GENERAL_DENTISTRY


def infer_preferred_day(message: str) -> str | None:
    """Extract a preferred weekday from free text, if present."""
    lowered = message.lower()
    for day in _WEEKDAYS:
        if re.search(rf"\b{day}\b", lowered):
            return day
    return None


def check_availability(message: str) -> ActionResult:
    """Look up open slots for the inferred specialty and preferred day."""
    container = get_container()
    specialty = infer_specialty(message)
    preferred_day = infer_preferred_day(message)
    slots = container.schedule.check_availability(
        specialty=specialty, preferred_day=preferred_day, limit=3
    )
    return ActionResult(
        tool="check_availability",
        status=ToolStatus.SUCCESS,
        result={
            "specialty": specialty.value,
            "preferred_day": preferred_day,
            "slot_count": len(slots),
            "slots": [s.model_dump() for s in slots],
        },
    )
