"""Agent routing tests (through the compiled LangGraph workflow)."""

from __future__ import annotations

from doc_helper_ai_agent.agent.graph import run_agent
from doc_helper_ai_agent.domain.enums import Locale


def _run(message: str, locale: Locale = Locale.EN) -> dict:
    return run_agent(
        message=message,
        user_id="u",
        session_id="s",
        trace_id="trace-test",
        locale=locale,
    )


def _tools(state: dict) -> list[str]:
    return [action["tool"] for action in state.get("actions", [])]


def test_emergency_routes_to_escalation():
    state = _run("I have severe tooth pain and my gum is bleeding")
    assert state["classification"] == "emergency_or_pain"
    assert state["requires_human"] is True
    assert "escalate_to_human" in _tools(state)
    assert state["response_message"]


def test_pricing_routes_to_rag():
    state = _run("How much does teeth whitening cost?")
    assert state["classification"] == "pricing_question"
    assert "answer_with_rag" in _tools(state)
    assert state["sources"]
    assert state["requires_human"] is False


def test_document_question_routes_to_rag():
    state = _run("What is your cancellation policy?")
    assert state["classification"] == "document_question"
    assert "answer_with_rag" in _tools(state)


def test_appointment_routes_to_availability_and_intake():
    state = _run("I want to book an appointment for whitening next Friday")
    assert state["classification"] == "appointment_request"
    tools = _tools(state)
    assert "check_availability" in tools
    assert "create_appointment_request" in tools


def test_complaint_creates_ticket_and_flags_human():
    state = _run("I want to make a complaint, the service was terrible")
    assert state["classification"] == "complaint"
    assert state["requires_human"] is True
    assert "create_complaint_ticket" in _tools(state)


def test_explicit_human_request_escalates():
    state = _run("I would like to speak to a human please")
    assert state["classification"] == "human_escalation"
    assert state["requires_human"] is True
    assert "escalate_to_human" in _tools(state)


def test_spanish_pricing_routes_to_spanish_rag_answer():
    state = _run("¿Cuánto cuesta el blanqueamiento dental?", Locale.ES)

    assert state["classification"] == "pricing_question"
    assert "answer_with_rag" in _tools(state)
    assert state["sources"]
    assert "Según nuestros documentos" in state["response_message"]


def test_spanish_appointment_maps_day_and_specialty_to_canonical_values():
    state = _run("Quiero reservar una cita de blanqueamiento el próximo viernes.", Locale.ES)

    assert state["classification"] == "appointment_request"
    assert state["availability"]["specialty"] == "whitening"
    assert state["availability"]["preferred_day"] == "friday"
    assert "create_appointment_request" in _tools(state)
    assert "no está reservado ni confirmado" in state["response_message"]


def test_spanish_emergency_routes_to_escalation_even_with_english_output():
    state = _run("Tengo dolor intenso, sangrado e hinchazón.", Locale.EN)

    assert state["classification"] == "emergency_or_pain"
    assert state["requires_human"] is True
    assert "escalate_to_human" in _tools(state)
    assert "professional attention" in state["response_message"]


def test_spanish_conjugated_pain_gets_professional_guidance():
    state = _run("Me duele una muela", Locale.ES)

    assert state["classification"] == "emergency_or_pain"
    assert state["requires_human"] is True
    assert "atención profesional" in state["response_message"]


def test_pricing_language_wins_over_non_actionable_appointment_noun():
    state = _run("¿Cuánto cuesta una cita de limpieza?", Locale.ES)

    assert state["classification"] == "pricing_question"
    assert "answer_with_rag" in _tools(state)
    assert "create_appointment_request" not in _tools(state)


def test_seguro_as_uncertainty_does_not_route_to_pricing():
    state = _run("No estoy seguro de qué servicios ofrecen", Locale.ES)

    assert state["classification"] == "document_question"


def test_weekend_request_creates_callback_instead_of_mismatched_appointment():
    state = _run("Quiero reservar una cita de limpieza el sábado", Locale.ES)

    assert state["availability"]["preferred_day"] == "saturday"
    assert state["availability"]["slot_count"] == 0
    assert "create_callback_request" in _tools(state)
    assert "create_appointment_request" not in _tools(state)
    assert "solicitud de llamada" in state["response_message"]


def test_mock_mode_runs_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from doc_helper_ai_agent.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    assert settings.use_real_llm is False
    assert settings.use_embeddings is False

    state = _run("What services do you offer?")
    assert state["response_message"]
    assert state["classification"] in {"document_question", "general_question"}
