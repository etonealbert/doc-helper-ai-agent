"""Health endpoint tests."""

from __future__ import annotations


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "status": "ok",
        "service": "doc-helper-ai-agent",
        "version": "0.1.0",
    }


def test_health_sets_trace_header(client):
    response = client.get("/health")
    assert response.headers.get("X-Trace-Id")
