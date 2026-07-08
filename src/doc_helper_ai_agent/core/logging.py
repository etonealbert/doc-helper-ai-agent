"""Structured-ish logging with a per-request trace id.

A :class:`contextvars.ContextVar` carries the current ``trace_id`` so every log
line emitted while handling a request is automatically correlated, including
logs from agent nodes and services. Secrets are never logged by this module.
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar

_trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="-")

_CONFIGURED = False


def set_trace_id(trace_id: str) -> None:
    """Bind ``trace_id`` to the current execution context."""
    _trace_id_ctx.set(trace_id)


def get_trace_id() -> str:
    """Return the trace id bound to the current execution context."""
    return _trace_id_ctx.get()


class _TraceIdFilter(logging.Filter):
    """Inject the current trace id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = _trace_id_ctx.get()
        return True


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once. Safe to call multiple times."""
    global _CONFIGURED
    root = logging.getLogger()
    if _CONFIGURED:
        root.setLevel(level.upper())
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | trace=%(trace_id)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    handler.addFilter(_TraceIdFilter())
    root.handlers = [handler]
    root.setLevel(level.upper())
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger."""
    return logging.getLogger(name)
