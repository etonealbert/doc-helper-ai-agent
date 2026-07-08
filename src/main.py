"""Backwards-compatibility shim.

The FastAPI app now lives in ``doc_helper_ai_agent.main``. Import from there.
"""

from doc_helper_ai_agent.main import app, run

__all__ = ["app", "run"]
