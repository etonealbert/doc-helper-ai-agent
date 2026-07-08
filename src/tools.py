"""Backwards-compatibility shim.

Agent tools now live in ``doc_helper_ai_agent.tools``. Import from there.
"""

from doc_helper_ai_agent.tools import (
    appointment_tools,
    crm_tools,
    escalation_tools,
    knowledge_tools,
)

__all__ = ["appointment_tools", "crm_tools", "escalation_tools", "knowledge_tools"]
