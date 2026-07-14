"""Appointment language parsing tests."""

from __future__ import annotations

import pytest

from doc_helper_ai_agent.domain.enums import Specialty
from doc_helper_ai_agent.tools.appointment_tools import infer_preferred_day, infer_specialty


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Necesito una cita de blanqueamiento", Specialty.WHITENING),
        ("Quiero consultar por ortodoncia", Specialty.ORTHODONTICS),
        ("Necesito información sobre implantes", Specialty.IMPLANTS),
        ("Quiero una limpieza dental", Specialty.GENERAL_DENTISTRY),
    ],
)
def test_infers_spanish_specialties(message, expected):
    assert infer_specialty(message) == expected


@pytest.mark.parametrize(
    "message,expected",
    [
        ("el próximo viernes", "friday"),
        ("el miércoles por la mañana", "wednesday"),
        ("Monday works for me", "monday"),
    ],
)
def test_infers_spanish_and_english_weekdays(message, expected):
    assert infer_preferred_day(message) == expected


def test_short_appointment_term_does_not_match_inside_another_word():
    from doc_helper_ai_agent.agent.nodes import _classify_keywords

    assert _classify_keywords("La clínica necesita información") != "appointment_request"
