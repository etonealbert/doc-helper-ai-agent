"""Backwards-compatibility shim.

The agent workflow now lives in ``doc_helper_ai_agent.agent``. Import from there.
"""

from doc_helper_ai_agent.agent.graph import build_graph, run_agent

__all__ = ["build_graph", "run_agent"]
