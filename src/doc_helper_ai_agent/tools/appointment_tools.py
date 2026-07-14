"""Appointment-related tools: infer intent details and check availability."""

from __future__ import annotations

import re
import unicodedata

from doc_helper_ai_agent.core.logging import get_logger
from doc_helper_ai_agent.dependencies import get_container
from doc_helper_ai_agent.domain.enums import Specialty, ToolStatus
from doc_helper_ai_agent.schemas.tools import ActionResult

logger = get_logger(__name__)

_WEEKDAY_ALIASES = {
    "monday": "monday",
    "lunes": "monday",
    "tuesday": "tuesday",
    "martes": "tuesday",
    "wednesday": "wednesday",
    "miercoles": "wednesday",
    "thursday": "thursday",
    "jueves": "thursday",
    "friday": "friday",
    "viernes": "friday",
    "saturday": "saturday",
    "sabado": "saturday",
    "sunday": "sunday",
    "domingo": "sunday",
}

_SPECIALTY_KEYWORDS: list[tuple[Specialty, tuple[str, ...]]] = [
    (
        Specialty.WHITENING,
        ("whitening", "whiten", "bleaching", "blanqueamiento", "blanquear"),
    ),
    (
        Specialty.ORTHODONTICS,
        (
            "braces",
            "orthodontic",
            "orthodontics",
            "aligner",
            "invisalign",
            "ortodoncia",
            "ortodontico",
            "ortodontica",
            "frenillos",
            "alineadores",
        ),
    ),
    (Specialty.IMPLANTS, ("implant", "implants", "implante", "implantes")),
    (Specialty.EMERGENCY, ("emergency", "urgent", "emergencia", "urgente")),
    (
        Specialty.GENERAL_DENTISTRY,
        (
            "cleaning",
            "checkup",
            "check-up",
            "filling",
            "cavity",
            "general",
            "limpieza",
            "revision",
            "chequeo",
            "empaste",
            "caries",
            "odontologia general",
        ),
    ),
]


def _normalize(text: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", text.casefold())
        if not unicodedata.combining(character)
    )


def _contains_phrase(text: str, phrase: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(_normalize(phrase))}(?!\w)", text) is not None


def infer_specialty(message: str) -> Specialty:
    """Best-effort mapping from free text to a bookable specialty."""
    normalized = _normalize(message)
    for specialty, keywords in _SPECIALTY_KEYWORDS:
        if any(_contains_phrase(normalized, keyword) for keyword in keywords):
            return specialty
    return Specialty.GENERAL_DENTISTRY


def infer_preferred_day(message: str) -> str | None:
    """Extract a preferred weekday from free text, if present."""
    normalized = _normalize(message)
    for alias, canonical_day in _WEEKDAY_ALIASES.items():
        if _contains_phrase(normalized, alias):
            return canonical_day
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
