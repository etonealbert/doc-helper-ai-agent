"""Enumerations used throughout the domain."""

from __future__ import annotations

from enum import StrEnum


class Classification(StrEnum):
    """High-level intent categories the agent can route on."""

    APPOINTMENT_REQUEST = "appointment_request"
    PRICING_QUESTION = "pricing_question"
    DOCUMENT_QUESTION = "document_question"
    EMERGENCY_OR_PAIN = "emergency_or_pain"
    COMPLAINT = "complaint"
    GENERAL_QUESTION = "general_question"
    HUMAN_ESCALATION = "human_escalation"


class Route(StrEnum):
    """Internal routing decisions produced by the router node."""

    RAG = "rag"
    APPOINTMENT = "appointment"
    COMPLAINT = "complaint"
    ESCALATE = "escalate"


class Specialty(StrEnum):
    """Bookable clinic specialties."""

    GENERAL_DENTISTRY = "general_dentistry"
    ORTHODONTICS = "orthodontics"
    WHITENING = "whitening"
    IMPLANTS = "implants"
    EMERGENCY = "emergency"


class ToolStatus(StrEnum):
    """Execution status of an agent tool/action."""

    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"


class TicketType(StrEnum):
    """CRM record types produced by the intake service."""

    APPOINTMENT = "appointment"
    CALLBACK = "callback"
    COMPLAINT = "complaint"
    ESCALATION = "escalation"
