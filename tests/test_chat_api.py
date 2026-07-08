"""Chat API tests (end-to-end through FastAPI)."""

from __future__ import annotations


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
