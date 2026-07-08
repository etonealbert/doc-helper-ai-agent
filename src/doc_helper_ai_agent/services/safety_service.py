"""Safety service.

Detects clinically-risky or out-of-scope messages (pain, bleeding, swelling,
fever, trauma, diagnosis/medication requests, emergencies). This agent is NOT a
medical tool: when any risk category is detected, the caller must avoid giving
medical advice, recommend contacting a professional, and escalate to a human.
"""

from __future__ import annotations

import re

from doc_helper_ai_agent.core.logging import get_logger
from doc_helper_ai_agent.domain.models import SafetyAssessment

logger = get_logger(__name__)

# Whole-word keyword sets per risk category.
_RISK_KEYWORDS: dict[str, set[str]] = {
    "severe_pain": {
        "severe pain",
        "unbearable",
        "excruciating",
        "agony",
        "throbbing pain",
        "extreme pain",
        "really bad pain",
        "so much pain",
        "pain",
    },
    "bleeding": {"bleeding", "blood", "hemorrhage", "won't stop bleeding"},
    "swelling": {"swelling", "swollen", "abscess", "puffy face"},
    "fever": {"fever", "high temperature", "chills"},
    "trauma": {
        "knocked out",
        "broken tooth",
        "cracked tooth",
        "accident",
        "fell",
        "trauma",
        "injury",
        "hit my",
        "car crash",
    },
    "diagnosis_request": {
        "diagnose",
        "diagnosis",
        "what do i have",
        "is it infected",
        "do i have an infection",
        "what's wrong with",
        "is this serious",
        "what condition",
    },
    "medication_request": {
        "prescribe",
        "prescription",
        "antibiotic",
        "antibiotics",
        "painkiller",
        "painkillers",
        "medication",
        "what medicine",
        "which medicine",
        "how much ibuprofen",
        "dosage",
    },
    "emergency": {
        "emergency",
        "urgent",
        "can't breathe",
        "cannot breathe",
        "911",
        "call an ambulance",
        "life threatening",
        "passing out",
        "faint",
    },
}

_RECOMMENDED_ACTION = (
    "This may need professional attention. I can't provide medical advice or a "
    "diagnosis, but I can arrange for a member of our clinical team to call you "
    "back. If this is a medical emergency, please contact your local emergency "
    "services right away."
)


def _build_patterns() -> dict[str, list[re.Pattern[str]]]:
    compiled: dict[str, list[re.Pattern[str]]] = {}
    for category, phrases in _RISK_KEYWORDS.items():
        compiled[category] = [
            re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE) for phrase in phrases
        ]
    return compiled


_PATTERNS = _build_patterns()


def assess_message(message: str) -> SafetyAssessment:
    """Evaluate ``message`` and return a :class:`SafetyAssessment`."""
    matched: list[str] = []
    for category, patterns in _PATTERNS.items():
        if any(p.search(message) for p in patterns):
            matched.append(category)

    if not matched:
        return SafetyAssessment(triggered=False)

    logger.info("Safety triggered: categories=%s", matched)
    reason = (
        "Message mentions potentially urgent clinical concerns: " + ", ".join(sorted(matched)) + "."
    )
    return SafetyAssessment(
        triggered=True,
        categories=sorted(matched),
        reason=reason,
        recommended_action=_RECOMMENDED_ACTION,
    )
