"""Convenience launcher.

The application lives in the ``doc_helper_ai_agent`` package. Prefer running:

    uv run uvicorn doc_helper_ai_agent.main:app --reload

This script simply delegates to the package's console entry point.
"""

from doc_helper_ai_agent.main import run

if __name__ == "__main__":
    run()
