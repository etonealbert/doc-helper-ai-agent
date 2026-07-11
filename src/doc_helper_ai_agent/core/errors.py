"""Application error types and FastAPI exception handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request
from fastapi.responses import JSONResponse

from doc_helper_ai_agent.core.logging import get_logger, get_trace_id

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = get_logger(__name__)


class DocHelperError(Exception):
    """Base class for expected, mapped application errors."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code


class NotFoundError(DocHelperError):
    status_code = 404
    error_code = "not_found"


class ValidationError(DocHelperError):
    status_code = 422
    error_code = "validation_error"


class AgentExecutionError(DocHelperError):
    status_code = 500
    error_code = "agent_error"


class CRMRepositoryError(DocHelperError):
    status_code = 503
    error_code = "crm_unavailable"


def _error_body(error_code: str, message: str) -> dict[str, object]:
    return {
        "error": {
            "code": error_code,
            "message": message,
            "trace_id": get_trace_id(),
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    """Register JSON exception handlers on the FastAPI app."""

    @app.exception_handler(DocHelperError)
    async def _handle_known(_: Request, exc: DocHelperError) -> JSONResponse:
        logger.warning("Handled application error: %s (%s)", exc.message, exc.error_code)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.error_code, exc.message),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=500,
            content=_error_body("internal_error", "An unexpected error occurred."),
        )
