"""FastAPI application entry point.

Run with::

    uv run uvicorn doc_helper_ai_agent.main:app --reload

A per-request ``trace_id`` is generated in middleware, bound to the logging
context, echoed in the ``X-Trace-Id`` response header, and included in error and
chat responses for end-to-end correlation.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from doc_helper_ai_agent.api.routes import chat, documents, health
from doc_helper_ai_agent.core.config import get_settings
from doc_helper_ai_agent.core.errors import register_exception_handlers
from doc_helper_ai_agent.core.logging import configure_logging, get_logger, set_trace_id
from doc_helper_ai_agent.dependencies import get_container

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm up shared dependencies (index sample docs) on startup."""
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info(
        "Starting %s v%s (env=%s, llm=%s, mock_llm=%s)",
        settings.app_name,
        settings.app_version,
        settings.app_env,
        settings.llm_provider,
        settings.enable_mock_llm,
    )
    container = get_container()
    container.rag.ensure_indexed()
    yield
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Doc Helper AI Agent",
        version=settings.app_version,
        description=(
            "Local-first AI agent backend for document Q&A and clinic-style "
            "operations. Demo project — not medical advice."
        ),
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def trace_id_middleware(request: Request, call_next):
        trace_id = request.headers.get("X-Trace-Id") or uuid.uuid4().hex
        set_trace_id(trace_id)
        response = await call_next(request)
        response.headers["X-Trace-Id"] = trace_id
        return response

    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(documents.router)
    return app


app = create_app()


def run() -> None:
    """Console-script entry point: ``doc-helper-ai-agent``."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "doc_helper_ai_agent.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app_env == "local",
    )


if __name__ == "__main__":
    run()
