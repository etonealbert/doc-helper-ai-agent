"""Safety service tests."""

from __future__ import annotations

import pytest

from doc_helper_ai_agent.domain.enums import Locale
from doc_helper_ai_agent.services.safety_service import assess_message


@pytest.mark.parametrize(
    "message,expected_category",
    [
        ("I have severe pain in my tooth", "severe_pain"),
        ("My gum won't stop bleeding", "bleeding"),
        ("My face is swollen and I have an abscess", "swelling"),
        ("I think I have a fever", "fever"),
        ("I knocked out a tooth in an accident", "trauma"),
        ("Can you diagnose what is wrong with me?", "diagnosis_request"),
        ("Can you prescribe me some antibiotics?", "medication_request"),
        ("This is an emergency, I can't breathe", "emergency"),
    ],
)
def test_risky_messages_trigger_safety(message, expected_category):
    assessment = assess_message(message)
    assert assessment.triggered is True
    assert expected_category in assessment.categories
    assert assessment.recommended_action


def test_safe_message_does_not_trigger():
    assessment = assess_message("What are your opening hours on weekdays?")
    assert assessment.triggered is False
    assert assessment.categories == []


@pytest.mark.parametrize(
    "message,expected_category",
    [
        ("Tengo un dolor insoportable en una muela", "severe_pain"),
        ("La encía no deja de sangrar", "bleeding"),
        ("Tengo la cara hinchada y un absceso", "swelling"),
        ("Creo que tengo fiebre", "fever"),
        ("Se me rompió un diente en un accidente", "trauma"),
        ("¿Puedes diagnosticar qué tengo?", "diagnosis_request"),
        ("¿Puedes recetarme antibióticos?", "medication_request"),
        ("Es una emergencia y no puedo respirar", "emergency"),
        ("Me sangran las encías", "bleeding"),
        ("Estoy sangrando desde esta mañana", "bleeding"),
        ("Tengo una urgencia dental", "emergency"),
        ("Me duele una muela", "severe_pain"),
    ],
)
def test_spanish_risky_messages_trigger_safety(message, expected_category):
    assessment = assess_message(message, Locale.ES)

    assert assessment.triggered is True
    assert expected_category in assessment.categories
    assert "atención profesional" in assessment.recommended_action


def test_selected_language_does_not_limit_safety_detection():
    assessment = assess_message("Tengo dolor intenso y sangrado", Locale.EN)

    assert assessment.triggered is True
    assert "professional attention" in assessment.recommended_action
