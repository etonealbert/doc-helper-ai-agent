"""Prompt text and label constants used by the agent."""

from __future__ import annotations

from doc_helper_ai_agent.domain.enums import Classification

CLASSIFICATION_LABELS: list[str] = [c.value for c in Classification]

CLASSIFIER_SYSTEM_PROMPT = (
    "You are a routing classifier for a dental clinic's front-desk assistant. "
    "Classify the user's message into exactly one of the following labels and "
    "reply with the label only, nothing else:\n"
    + "\n".join(f"- {label}" for label in CLASSIFICATION_LABELS)
    + "\n\nGuidance:\n"
    "- Use 'emergency_or_pain' for pain, bleeding, swelling, fever, trauma, "
    "infections, or requests for diagnosis/medication.\n"
    "- Use 'appointment_request' to book/reschedule visits.\n"
    "- Use 'pricing_question' for costs, fees, or insurance.\n"
    "- Use 'document_question' for policies, hours, location, or services.\n"
    "- Use 'complaint' for dissatisfaction about service.\n"
    "- Use 'human_escalation' when the user explicitly asks for a person.\n"
    "- Use 'general_question' otherwise."
)
