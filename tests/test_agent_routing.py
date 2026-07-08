"""Agent routing tests (through the compiled LangGraph workflow)."""

from __future__ import annotations

from doc_helper_ai_agent.agent.graph import run_agent


def _run(message: str) -> dict:
    return run_agent(message=message, user_id="u", session_id="s", trace_id="trace-test")


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
