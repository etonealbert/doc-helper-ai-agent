"""Agent node implementations.

Each node is a pure function ``AgentState -> partial AgentState`` so the graph is
easy to reason about and test. Classification runs in deterministic keyword mode
by default and can optionally use an LLM when one is configured.
"""

from __future__ import annotations

import re
import unicodedata

from doc_helper_ai_agent.agent.prompts import CLASSIFICATION_LABELS, CLASSIFIER_SYSTEM_PROMPT
from doc_helper_ai_agent.agent.state import AgentState
from doc_helper_ai_agent.core.config import get_settings
from doc_helper_ai_agent.core.logging import get_logger
from doc_helper_ai_agent.domain.enums import Classification, Locale, Route, ToolStatus
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
    "pain",
    "hurts",
    "hurt",
    "ache",
    "aching",
    "toothache",
    "emergency",
    "bleeding",
    "blood",
    "swelling",
    "swollen",
    "abscess",
    "fever",
    "trauma",
    "knocked out",
    "broken tooth",
    "cracked tooth",
    "severe",
    "urgent",
    "diagnose",
    "diagnosis",
    "infected",
    "infection",
    "prescribe",
    "prescription",
    "antibiotic",
    "antibiotics",
    "painkiller",
    "painkillers",
    "dolor",
    "duele",
    "dolor de muela",
    "emergencia",
    "sangrado",
    "sangre",
    "sangra",
    "sangran",
    "sangrando",
    "hinchazon",
    "hinchado",
    "hinchada",
    "absceso",
    "fiebre",
    "trauma",
    "diente roto",
    "diente quebrado",
    "diente agrietado",
    "grave",
    "urgente",
    "urgencia",
    "diagnosticar",
    "diagnostico",
    "infectado",
    "infeccion",
    "recetar",
    "receta",
    "antibiotico",
    "antibioticos",
    "analgesico",
    "analgesicos",
    "no puedo respirar",
)
_HUMAN_TERMS = (
    "speak to a human",
    "talk to a human",
    "speak to someone",
    "talk to someone",
    "real person",
    "representative",
    "human agent",
    "speak to a person",
    "call me back",
    "callback",
    "call back",
    "hablar con una persona",
    "hablar con alguien",
    "persona real",
    "representante",
    "agente humano",
    "quiero que me llamen",
    "llamenme",
    "devolver la llamada",
)
_COMPLAINT_TERMS = (
    "complaint",
    "complain",
    "unhappy",
    "dissatisfied",
    "disappointed",
    "rude",
    "terrible",
    "awful",
    "worst",
    "unacceptable",
    "poor service",
    "bad experience",
    "queja",
    "reclamar",
    "descontento",
    "insatisfecho",
    "decepcionado",
    "grosero",
    "pesimo",
    "peor",
    "inaceptable",
    "mal servicio",
    "mala experiencia",
)
_APPOINTMENT_TERMS = (
    "book",
    "booking",
    "appointment",
    "schedule",
    "reschedule",
    "availability",
    "available",
    "slot",
    "slots",
    "make an appointment",
    "see a dentist",
    "reservar",
    "reserva",
    "cita",
    "programar",
    "reprogramar",
    "disponibilidad",
    "disponible",
    "turno",
    "pedir cita",
    "ver a un dentista",
)
_PRICING_TERMS = (
    "price",
    "prices",
    "pricing",
    "cost",
    "costs",
    "how much",
    "fee",
    "fees",
    "charge",
    "expensive",
    "insurance",
    "payment",
    "co-pay",
    "financing",
    "precio",
    "precios",
    "costo",
    "costos",
    "cuanto cuesta",
    "tarifa",
    "tarifas",
    "caro",
    "seguro dental",
    "aseguradora",
    "cobertura",
    "pago",
    "copago",
    "financiacion",
)
_DOCUMENT_TERMS = (
    "policy",
    "policies",
    "cancellation",
    "refund",
    "hours",
    "opening",
    "open",
    "location",
    "address",
    "parking",
    "services",
    "service",
    "offer",
    "form",
    "forms",
    "document",
    "requirement",
    "requirements",
    "provide",
    "faq",
    "politica",
    "politicas",
    "cancelacion",
    "reembolso",
    "horario",
    "horarios",
    "abierto",
    "ubicacion",
    "direccion",
    "aparcamiento",
    "estacionamiento",
    "servicios",
    "servicio",
    "ofrecen",
    "formulario",
    "formularios",
    "documento",
    "requisito",
    "requisitos",
    "preguntas frecuentes",
)


def _normalize(text: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", text.casefold())
        if not unicodedata.combining(character)
    )


def _contains(text: str, terms: tuple[str, ...]) -> bool:
    return any(
        re.search(rf"(?<!\w){re.escape(_normalize(term))}(?!\w)", text) is not None
        for term in terms
    )


def _classify_keywords(message: str) -> Classification:
    text = _normalize(message)
    if _contains(text, _EMERGENCY_TERMS):
        return Classification.EMERGENCY_OR_PAIN
    if _contains(text, _HUMAN_TERMS):
        return Classification.HUMAN_ESCALATION
    if _contains(text, _COMPLAINT_TERMS):
        return Classification.COMPLAINT
    if _contains(text, _PRICING_TERMS):
        return Classification.PRICING_QUESTION
    if _contains(text, _APPOINTMENT_TERMS):
        return Classification.APPOINTMENT_REQUEST
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
    assessment = assess_message(state["message"], Locale(state.get("locale", Locale.ES)))
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
    action = knowledge_tools.answer_question(
        state["message"], locale=Locale(state.get("locale", Locale.ES))
    )
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
    locale = Locale(state.get("locale", Locale.ES))

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
            reason=(
                "No se encontró un horario compatible; requiere programación manual."
                if locale == Locale.ES
                else "No matching appointment slot found; needs manual scheduling."
            ),
        )
    return {"actions": [action.model_dump()]}


def escalate_to_human(state: AgentState) -> AgentState:
    safety = state.get("safety", {})
    categories = safety.get("categories", [])
    locale = Locale(state.get("locale", Locale.ES))
    reason = safety.get("reason") or (
        f"Se solicitó revisión humana para classification={state.get('classification')}."
        if locale == Locale.ES
        else f"Escalation requested for classification={state.get('classification')}."
    )
    action = escalation_tools.escalate_to_human(
        user_id=state["user_id"], reason=reason, categories=categories
    )
    return {"actions": [action.model_dump()], "requires_human": True}


def _find_ticket_id(actions: list[dict], tool: str) -> str | None:
    for action in actions:
        if action.get("tool") != tool or action.get("status") != ToolStatus.SUCCESS:
            continue
        result = action.get("result")
        if isinstance(result, dict):
            ticket_id = result.get("ticket_id")
            if isinstance(ticket_id, str) and ticket_id:
                return ticket_id
    return None


_SPECIALTY_LABELS = {
    Locale.EN: {
        "general_dentistry": "general dentistry",
        "orthodontics": "orthodontics",
        "whitening": "whitening",
        "implants": "dental implants",
        "emergency": "emergency dentistry",
    },
    Locale.ES: {
        "general_dentistry": "odontología general",
        "orthodontics": "ortodoncia",
        "whitening": "blanqueamiento dental",
        "implants": "implantes dentales",
        "emergency": "atención dental de urgencia",
    },
}

_DAY_LABELS = {
    Locale.EN: {
        "monday": "Monday",
        "tuesday": "Tuesday",
        "wednesday": "Wednesday",
        "thursday": "Thursday",
        "friday": "Friday",
        "saturday": "Saturday",
        "sunday": "Sunday",
    },
    Locale.ES: {
        "monday": "lunes",
        "tuesday": "martes",
        "wednesday": "miércoles",
        "thursday": "jueves",
        "friday": "viernes",
        "saturday": "sábado",
        "sunday": "domingo",
    },
}


def final_response(state: AgentState) -> AgentState:
    route = state.get("route")
    safety = state.get("safety", {})
    actions = state.get("actions", [])
    locale = Locale(state.get("locale", Locale.ES))

    if route == Route.ESCALATE.value:
        ticket = _find_ticket_id(actions, "escalate_to_human")
        if safety.get("triggered"):
            if locale == Locale.ES:
                confirmation = (
                    f"Se registró una solicitud prioritaria de revisión humana (ref {ticket}). "
                    "No se ha contactado a los servicios de emergencia."
                    if ticket
                    else "No se confirmó ninguna solicitud de seguimiento."
                )
            else:
                confirmation = (
                    f"A priority human-review request was recorded (ref {ticket}). Emergency "
                    "services have not been contacted."
                    if ticket
                    else "No follow-up request was confirmed."
                )
            message = f"{safety.get('recommended_action', '')} {confirmation}".strip()
        else:
            if locale == Locale.ES:
                message = (
                    f"Se registró una solicitud de revisión por parte del equipo (ref {ticket}). "
                    "Todavía no se ha establecido contacto."
                    if ticket
                    else "No se pudo confirmar una solicitud de revisión humana. Contacta con la clínica."
                )
            else:
                message = (
                    f"A request for team review was recorded (ref {ticket}). Contact has not "
                    "yet been made."
                    if ticket
                    else "A human-review request could not be confirmed. Please contact the clinic."
                )
    elif route == Route.RAG.value:
        message = state.get("response_message") or (
            "No tengo certeza sobre eso. Contacta con la clínica para que el equipo te ayude."
            if locale == Locale.ES
            else "I'm not certain about that. Please contact the clinic and our team will help."
        )
    elif route == Route.APPOINTMENT.value:
        message = _compose_appointment_message(state, actions, locale)
    elif route == Route.COMPLAINT.value:
        ticket = _find_ticket_id(actions, "create_complaint_ticket")
        if locale == Locale.ES:
            message = (
                f"Lamento lo ocurrido. Se registró tu queja para revisión (ref {ticket})."
                if ticket
                else "Lamento lo ocurrido. No se pudo confirmar el registro de la queja; contacta con la clínica."
            )
        else:
            message = (
                f"I'm sorry to hear about your experience. Your complaint was recorded for "
                f"review (ref {ticket})."
                if ticket
                else "I'm sorry to hear about your experience. The complaint could not be confirmed; please contact the clinic."
            )
    else:  # defensive fallback
        message = (
            "No sé cómo ayudarte con eso todavía. Contacta con la clínica para recibir asistencia."
            if locale == Locale.ES
            else "I'm not sure how to help with that yet. Please contact the clinic for assistance."
        )

    logger.info("final_response composed (route=%s)", route)
    return {"response_message": message}


def _compose_appointment_message(state: AgentState, actions: list[dict], locale: Locale) -> str:
    availability = state.get("availability", {})
    specialty_code = availability.get("specialty", "general_dentistry")
    specialty = _SPECIALTY_LABELS[locale].get(specialty_code, str(specialty_code).replace("_", " "))
    preferred_day = availability.get("preferred_day")
    slots = availability.get("slots") or []
    appt_ticket = _find_ticket_id(actions, "create_appointment_request")
    callback_ticket = _find_ticket_id(actions, "create_callback_request")

    if slots and appt_ticket:
        top = slots[0]
        day_code = preferred_day or top["day"]
        day = _DAY_LABELS[locale].get(day_code, str(day_code))
        if locale == Locale.ES:
            return (
                f"Hay un horario de demostración disponible para {specialty} con "
                f"{top['doctor_name']} el {day} a las {top['start_time']}. Se registró la "
                f"solicitud de cita {appt_ticket}; el horario no está reservado ni confirmado "
                "hasta que el equipo se comunique contigo."
            )
        return (
            f"A demonstration slot is available for {specialty} with {top['doctor_name']} on "
            f"{day} at {top['start_time']}. Appointment request {appt_ticket} was recorded; "
            "the slot is not reserved or confirmed until the team contacts you."
        )
    if callback_ticket:
        if locale == Locale.ES:
            return (
                f"No encontré un horario disponible para {specialty}. Se registró una solicitud "
                f"de llamada del equipo de programación (ref {callback_ticket}); la llamada "
                "todavía no se ha realizado."
            )
        return (
            f"I couldn't find an open {specialty} slot. A scheduling callback request was "
            f"recorded (ref {callback_ticket}); the callback has not happened yet."
        )
    return (
        f"No encontré un horario disponible para {specialty} y no se confirmó ninguna solicitud de seguimiento."
        if locale == Locale.ES
        else f"I couldn't find an open {specialty} slot, and no follow-up request was confirmed."
    )
