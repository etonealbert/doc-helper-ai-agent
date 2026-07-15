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


def test_local_frontend_origin_is_allowed(client):
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert response.headers["Access-Control-Allow-Methods"] == "GET, POST, OPTIONS"

    response = client.get("/health", headers={"Origin": "http://localhost:5173"})

    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert response.headers["Access-Control-Expose-Headers"] == "X-Trace-Id"


def test_unknown_frontend_origin_is_not_allowed(client):
    response = client.options(
        "/health",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "Access-Control-Allow-Origin" not in response.headers
