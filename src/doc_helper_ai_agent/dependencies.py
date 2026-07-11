"""Composition root: wires settings, infrastructure, and services together.

A single :class:`Container` owns the process-wide singletons so tools, agent
nodes, and API routes all share the same CRM/schedule/vector store/RAG state.
"""

from __future__ import annotations

from doc_helper_ai_agent.core.config import Settings, get_settings
from doc_helper_ai_agent.domain.repositories import CRMRepository
from doc_helper_ai_agent.infrastructure.dynamodb_crm import DynamoDBCRMRepository
from doc_helper_ai_agent.infrastructure.mock_crm import get_crm
from doc_helper_ai_agent.infrastructure.mock_schedule import MockSchedule, get_schedule
from doc_helper_ai_agent.infrastructure.vector_store import (
    LocalVectorStore,
    get_vector_store,
)
from doc_helper_ai_agent.services.intake_service import IntakeService, get_intake_service
from doc_helper_ai_agent.services.rag_service import RagService, get_rag_service


def _build_crm_repository(settings: Settings) -> CRMRepository:
    if settings.crm_provider == "mock":
        return get_crm()
    if settings.crm_provider == "dynamodb":
        return DynamoDBCRMRepository(
            table_name=settings.dynamodb_table_name,
            region_name=settings.aws_region,
            ttl_days=settings.crm_record_ttl_days,
        )
    raise ValueError(f"Unsupported CRM_PROVIDER: {settings.crm_provider}")


class Container:
    """Holds shared application dependencies."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.crm: CRMRepository = _build_crm_repository(self.settings)
        self.schedule: MockSchedule = get_schedule()
        self.vector_store: LocalVectorStore = get_vector_store(self.settings)
        self.rag: RagService = get_rag_service(self.settings, self.vector_store)
        self.intake: IntakeService = get_intake_service(self.crm)


_container: Container | None = None


def get_container() -> Container:
    """Return the process-wide :class:`Container` singleton."""
    global _container
    if _container is None:
        _container = Container()
    return _container


def reset_container() -> None:
    """Drop the container singleton (used by tests)."""
    global _container
    _container = None
