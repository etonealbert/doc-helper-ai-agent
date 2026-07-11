"""Chat API tests (end-to-end through FastAPI)."""

from __future__ import annotations

from types import SimpleNamespace

from doc_helper_ai_agent.core.errors import CRMRepositoryError
from doc_helper_ai_agent.infrastructure.mock_crm import MockCRMRepository
from doc_helper_ai_agent.services.intake_service import IntakeService


class FailingCRMRepository(MockCRMRepository):
    def create_human_escalation_ticket(self, **kwargs):
        raise CRMRepositoryError("CRM persistence is temporarily unavailable.")


def test_chat_returns_structured_response(client):
    response = client.post(
        "/api/chat",
        json={
            "message": "How much does teeth whitening cost?",
            "user_id": "demo-user",
            "session_id": "demo-session",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["classification"] == "pricing_question"
    assert data["requires_human"] is False
    assert isinstance(data["actions"], list)
    assert data["sources"], "pricing question should cite sources"
    assert data["trace_id"]
    assert data["message"]


def test_chat_appointment_flow(client):
    response = client.post(
        "/api/chat",
        json={"message": "I need to book an appointment for whitening next Friday"},
    )
    data = response.json()
    assert data["classification"] == "appointment_request"
    tools = [action["tool"] for action in data["actions"]]
    assert "check_availability" in tools
    assert "create_appointment_request" in tools


def test_chat_emergency_requires_human(client):
    response = client.post(
        "/api/chat",
        json={"message": "I have severe pain and my gum is bleeding badly"},
    )
    data = response.json()
    assert data["classification"] == "emergency_or_pain"
    assert data["requires_human"] is True
    tools = [action["tool"] for action in data["actions"]]
    assert "escalate_to_human" in tools


def test_chat_preserves_crm_unavailable_error(client, monkeypatch):
    intake = IntakeService(FailingCRMRepository())
    container = SimpleNamespace(intake=intake)
    monkeypatch.setattr(
        "doc_helper_ai_agent.tools.escalation_tools.get_container",
        lambda: container,
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "I have severe pain and my gum is bleeding",
            "user_id": "failure-user",
        },
    )
    body = response.json()

    assert response.status_code == 503
    assert body["error"]["code"] == "crm_unavailable"
    assert body["error"]["message"] == "CRM persistence is temporarily unavailable."
    assert body["error"]["trace_id"]
    assert "ticket_id" not in response.text
    assert "actions" not in body


def test_chat_empty_message_is_rejected(client):
    response = client.post("/api/chat", json={"message": ""})
    assert response.status_code == 422


def test_documents_listing(client):
    response = client.get("/api/documents")
    assert response.status_code == 200
    data = response.json()
    assert data["total_documents"] >= 4
    sources = {doc["source"] for doc in data["documents"]}
    assert "pricing.md" in sources
