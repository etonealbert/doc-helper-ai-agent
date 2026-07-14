"""Safety service.

Detects clinically-risky or out-of-scope messages (pain, bleeding, swelling,
fever, trauma, diagnosis/medication requests, emergencies). This agent is NOT a
medical tool: when any risk category is detected, the caller must avoid giving
medical advice, recommend contacting a professional, and escalate to a human.
"""

from __future__ import annotations

import re
import unicodedata

from doc_helper_ai_agent.core.logging import get_logger
from doc_helper_ai_agent.domain.enums import Locale
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
        "dolor intenso",
        "dolor insoportable",
        "dolor extremo",
        "mucho dolor",
        "dolor de muela",
        "dolor",
        "duele",
    },
    "bleeding": {
        "bleeding",
        "blood",
        "hemorrhage",
        "won't stop bleeding",
        "sangrado",
        "sangre",
        "sangrar",
        "sangra",
        "sangran",
        "sangrando",
        "no deja de sangrar",
        "hemorragia",
    },
    "swelling": {
        "swelling",
        "swollen",
        "abscess",
        "puffy face",
        "hinchazon",
        "hinchado",
        "hinchada",
        "absceso",
        "cara inflamada",
    },
    "fever": {"fever", "high temperature", "chills", "fiebre", "temperatura alta", "escalofrios"},
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
        "diente roto",
        "diente quebrado",
        "diente agrietado",
        "accidente",
        "caida",
        "lesion",
        "golpe",
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
        "diagnosticar",
        "diagnostico",
        "que tengo",
        "esta infectado",
        "tengo una infeccion",
        "que me pasa",
        "es grave",
        "que enfermedad",
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
        "recetar",
        "receta",
        "antibiotico",
        "antibioticos",
        "analgesico",
        "analgesicos",
        "medicamento",
        "medicamentos",
        "que medicina",
        "cuanto ibuprofeno",
        "dosis",
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
        "emergencia",
        "urgencia",
        "urgente",
        "no puedo respirar",
        "ambulancia",
        "riesgo vital",
        "pierdo el conocimiento",
        "desmayo",
    },
}

_RECOMMENDED_ACTIONS = {
    Locale.EN: (
        "This may need professional attention. I can't provide medical advice or a "
        "diagnosis. If this is a medical emergency, contact your local emergency "
        "services or a qualified professional right away."
    ),
    Locale.ES: (
        "Esto puede requerir atención profesional. No puedo ofrecer consejo médico ni "
        "un diagnóstico. Si se trata de una emergencia médica, contacta de inmediato "
        "con los servicios de emergencia locales o con un profesional cualificado."
    ),
}


def _normalize(text: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", text.casefold())
        if not unicodedata.combining(character)
    )


def _build_patterns() -> dict[str, list[re.Pattern[str]]]:
    compiled: dict[str, list[re.Pattern[str]]] = {}
    for category, phrases in _RISK_KEYWORDS.items():
        compiled[category] = [
            re.compile(rf"(?<!\w){re.escape(_normalize(phrase))}(?!\w)") for phrase in phrases
        ]
    return compiled


_PATTERNS = _build_patterns()


def assess_message(message: str, locale: Locale = Locale.ES) -> SafetyAssessment:
    """Evaluate ``message`` and return a :class:`SafetyAssessment`."""
    normalized_message = _normalize(message)
    matched: list[str] = []
    for category, patterns in _PATTERNS.items():
        if any(p.search(normalized_message) for p in patterns):
            matched.append(category)

    if not matched:
        return SafetyAssessment(triggered=False)

    logger.info("Safety triggered: categories=%s", matched)
    if locale == Locale.ES:
        reason = (
            "El mensaje menciona posibles riesgos clínicos: " + ", ".join(sorted(matched)) + "."
        )
    else:
        reason = (
            "Message mentions potentially urgent clinical concerns: "
            + ", ".join(sorted(matched))
            + "."
        )
    return SafetyAssessment(
        triggered=True,
        categories=sorted(matched),
        reason=reason,
        recommended_action=_RECOMMENDED_ACTIONS[locale],
    )
