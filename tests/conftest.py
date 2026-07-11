"""Shared pytest fixtures.

Every test runs against fresh, isolated singletons so mock IDs and the vector
store don't leak between tests. All defaults keep the app in deterministic mock
mode (no network, no API key required).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_singletons(monkeypatch: pytest.MonkeyPatch):
    """Reset process-wide singletons before each test."""
    monkeypatch.setenv("CRM_PROVIDER", "mock")

    from doc_helper_ai_agent.core.config import get_settings
    from doc_helper_ai_agent.dependencies import reset_container
    from doc_helper_ai_agent.infrastructure.mock_crm import reset_crm
    from doc_helper_ai_agent.infrastructure.mock_schedule import reset_schedule
    from doc_helper_ai_agent.infrastructure.vector_store import reset_vector_store
    from doc_helper_ai_agent.services.intake_service import reset_intake_service
    from doc_helper_ai_agent.services.rag_service import reset_rag_service

    get_settings.cache_clear()
    reset_container()
    reset_vector_store()
    reset_rag_service()
    reset_intake_service()
    reset_crm()
    reset_schedule()
    yield
    reset_container()
    reset_vector_store()
    reset_rag_service()
    reset_intake_service()
    reset_crm()
    reset_schedule()
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    """A FastAPI test client bound to the application."""
    from doc_helper_ai_agent.main import app

    return TestClient(app)
