"""Agent node implementations.

Each node is a pure function ``AgentState -> partial AgentState`` so the graph is
easy to reason about and test. Classification runs in deterministic keyword mode
by default and can optionally use an LLM when one is configured.
"""

from __future__ import annotations

from doc_helper_ai_agent.agent.prompts import CLASSIFICATION_LABELS, CLASSIFIER_SYSTEM_PROMPT
from doc_helper_ai_agent.agent.state import AgentState
from doc_helper_ai_agent.core.config import get_settings
from doc_helper_ai_agent.core.logging import get_logger
from doc_helper_ai_agent.domain.enums import Classification, Route
from doc_helper_ai_agent.services.safety_service import assess_message
from doc_helper_ai_agent.tools import (
    appointment_tools,
    crm_tools,
    escalation_tools,
    knowledge_tools,
)

logger = get_logger(__name__)

# --- keyword classification ----------------------------------------------
_EMERGENCY_TERMS = (
    "pain", "hurts", "hurt", "ache", "aching", "toothache", "emergency",
    "bleeding", "blood", "swelling", "swollen", "abscess", "fever", "trauma",
    "knocked out", "broken tooth", "cracked tooth", "severe", "urgent",
    "diagnose", "diagnosis", "infected", "infection", "prescribe",
    "prescription", "antibiotic", "antibiotics", "painkiller", "painkillers",
)
_HUMAN_TERMS = (
    "speak to a human", "talk to a human", "speak to someone", "talk to someone",
    "real person", "representative", "human agent", "speak to a person",
    "call me back", "callback", "call back",
)
_COMPLAINT_TERMS = (
    "complaint", "complain", "unhappy", "dissatisfied", "disappointed", "rude",
    "terrible", "awful", "worst", "unacceptable", "poor service", "bad experience",
)
_APPOINTMENT_TERMS = (
    "book", "booking", "appointment", "schedule", "reschedule", "availability",
    "available", "slot", "slots", "make an appointment", "see a dentist",
)
_PRICING_TERMS = (
    "price", "prices", "pricing", "cost", "costs", "how much", "fee", "fees",
    "charge", "expensive", "insurance", "payment", "co-pay", "financing",
)
_DOCUMENT_TERMS = (
    "policy", "policies", "cancellation", "refund", "hours", "opening", "open",
    "location", "address", "parking", "services", "service", "offer", "form",
    "forms", "document", "requirement", "requirements", "provide", "faq",
)


def _contains(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _classify_keywords(message: str) -> Classification:
    text = message.lower()
    if _contains(text, _EMERGENCY_TERMS):
        return Classification.EMERGENCY_OR_PAIN
    if _contains(text, _HUMAN_TERMS):
        return Classification.HUMAN_ESCALATION
    if _contains(text, _COMPLAINT_TERMS):
        return Classification.COMPLAINT
    if _contains(text, _APPOINTMENT_TERMS):
        return Classification.APPOINTMENT_REQUEST
    if _contains(text, _PRICING_TERMS):
        return Classification.PRICING_QUESTION
    if _contains(text, _DOCUMENT_TERMS):
        return Classification.DOCUMENT_QUESTION
    return Classification.GENERAL_QUESTION


def _classify_llm(message: str) -> Classification:  # pragma: no cover - network dependent
    from openai import OpenAI

    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.llm_model,
        temperature=0,
        messages=[
            {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
    )
    label = (response.choices[0].message.content or "").strip().lower()
    if label in CLASSIFICATION_LABELS:
        return Classification(label)
    logger.warning("LLM returned unknown label %r; falling back to keywords", label)
    return _classify_keywords(message)


def _classify(message: str) -> Classification:
    settings = get_settings()
    if settings.use_real_llm:
        try:
            return _classify_llm(message)
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning("LLM classification failed, using keywords: %s", exc)
    return _classify_keywords(message)


# --- nodes ----------------------------------------------------------------
def classify_request(state: AgentState) -> AgentState:
    classification = _classify(state["message"])
    logger.info("classify_request -> %s", classification.value)
    return {"classification": classification.value}


def safety_check(state: AgentState) -> AgentState:
    assessment = assess_message(state["message"])
    logger.info("safety_check -> triggered=%s", assessment.triggered)
    return {"safety": assessment.model_dump(), "requires_human": assessment.triggered}


def _decide_route(state: AgentState) -> Route:
    classification = state["classification"]
    requires_human = state.get("requires_human", False)
    if requires_human or classification in {
        Classification.EMERGENCY_OR_PAIN.value,
        Classification.HUMAN_ESCALATION.value,
    }:
        return Route.ESCALATE
    if classification in {
        Classification.PRICING_QUESTION.value,
        Classification.DOCUMENT_QUESTION.value,
        Classification.GENERAL_QUESTION.value,
    }:
        return Route.RAG
    if classification == Classification.APPOINTMENT_REQUEST.value:
        return Route.APPOINTMENT
    if classification == Classification.COMPLAINT.value:
        return Route.COMPLAINT
    return Route.ESCALATE


def route_request(state: AgentState) -> AgentState:
    route = _decide_route(state)
    logger.info("route_request -> %s", route.value)
    return {"route": route.value}


def answer_with_rag(state: AgentState) -> AgentState:
    action = knowledge_tools.answer_question(state["message"])
    return {
        "actions": [action.model_dump()],
        "sources": action.result.get("sources", []),
        "response_message": action.result.get("answer", ""),
    }


def check_availability(state: AgentState) -> AgentState:
    action = appointment_tools.check_availability(state["message"])
    return {"actions": [action.model_dump()], "availability": action.result}


def create_intake_or_callback(state: AgentState) -> AgentState:
    classification = state["classification"]
    user_id = state["user_id"]
    message = state["message"]

    if classification == Classification.COMPLAINT.value:
        action = crm_tools.create_complaint_ticket(user_id=user_id, summary=message[:300])
        return {"actions": [action.model_dump()], "requires_human": True}

    # Appointment path.
    availability = state.get("availability", {})
    if availability.get("slot_count", 0) > 0:
        action = crm_tools.create_appointment_request(
            user_id=user_id, availability=availability, notes=message[:200]
        )
    else:
        action = crm_tools.create_callback_request(
            user_id=user_id,
            reason="No matching appointment slot found; needs manual scheduling.",
        )
    return {"actions": [action.model_dump()]}


def escalate_to_human(state: AgentState) -> AgentState:
    safety = state.get("safety", {})
    categories = safety.get("categories", [])
    reason = safety.get("reason") or (
        f"Escalation requested for classification={state.get('classification')}."
    )
    action = escalation_tools.escalate_to_human(
        user_id=state["user_id"], reason=reason, categories=categories
    )
    return {"actions": [action.model_dump()], "requires_human": True}


def _find_ticket_id(actions: list[dict], tool: str) -> str | None:
    for action in actions:
        if action.get("tool") == tool:
            return action.get("result", {}).get("ticket_id")
    return None


def final_response(state: AgentState) -> AgentState:
    route = state.get("route")
    safety = state.get("safety", {})
    actions = state.get("actions", [])

    if route == Route.ESCALATE.value:
        ticket = _find_ticket_id(actions, "escalate_to_human")
        if safety.get("triggered"):
            message = (
                f"{safety.get('recommended_action', '')} "
                f"I've logged a priority callback (ref {ticket}) so our clinical "
                "team can reach you as soon as possible."
            ).strip()
        else:
            message = (
                "I've connected you with a member of our team who will follow up "
                f"shortly (ref {ticket})."
            )
    elif route == Route.RAG.value:
        message = state.get("response_message") or (
            "I'm not certain about that. Please contact the clinic and our team "
            "will help."
        )
    elif route == Route.APPOINTMENT.value:
        message = _compose_appointment_message(state, actions)
    elif route == Route.COMPLAINT.value:
        ticket = _find_ticket_id(actions, "create_complaint_ticket")
        message = (
            "I'm sorry to hear about your experience. I've logged your feedback "
            f"(ref {ticket}) and a member of our team will follow up with you."
        )
    else:  # defensive fallback
        message = (
            "I'm not sure how to help with that yet. I'll pass this to our team "
            "so someone can assist you."
        )

    logger.info("final_response composed (route=%s)", route)
    return {"response_message": message}


def _compose_appointment_message(state: AgentState, actions: list[dict]) -> str:
    availability = state.get("availability", {})
    specialty = availability.get("specialty", "general_dentistry").replace("_", " ")
    preferred_day = availability.get("preferred_day")
    slots = availability.get("slots") or []
    appt_ticket = _find_ticket_id(actions, "create_appointment_request")
    callback_ticket = _find_ticket_id(actions, "create_callback_request")

    if slots and appt_ticket:
        top = slots[0]
        day = (preferred_day or top["day"]).capitalize()
        return (
            f"I found availability for {specialty} with {top['doctor_name']} on "
            f"{day} at {top['start_time']}. I've created appointment request "
            f"{appt_ticket}; our team will confirm the details with you."
        )
    return (
        f"I couldn't find an open {specialty} slot right now, so I've created a "
        f"callback request ({callback_ticket}) for our scheduling team to reach out."
    )
