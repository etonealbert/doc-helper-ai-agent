"""Intake service and mock CRM tests."""

from __future__ import annotations

import re

from doc_helper_ai_agent.domain.repositories import CRMRepository
from doc_helper_ai_agent.infrastructure.mock_crm import MockCRM, MockCRMRepository
from doc_helper_ai_agent.services.intake_service import IntakeService


def _service() -> IntakeService:
    return IntakeService(MockCRMRepository())


def _accepts_repository(repository: CRMRepository) -> CRMRepository:
    return repository


def test_mock_crm_compatibility_alias():
    assert MockCRM is MockCRMRepository


def test_intake_service_keeps_injected_repository():
    repository = MockCRMRepository()
    service = IntakeService(repository)
    assert service._crm is repository


def test_mock_repository_matches_protocol_shape():
    repository = MockCRMRepository()
    assert _accepts_repository(repository) is repository


def test_appointment_id_format():
    record = _service().create_appointment(
        user_id="u1", specialty="whitening", preferred_day="friday", slot=None
    )
    assert re.fullmatch(r"APPT-\d{4}-0001", record["id"])
    assert record["status"] == "pending_confirmation"


def test_callback_id_format():
    record = _service().create_callback(user_id="u1", reason="needs scheduling")
    assert re.fullmatch(r"CALLBACK-\d{4}-0001", record["id"])
    assert record["status"] == "open"


def test_complaint_id_format():
    record = _service().create_complaint(user_id="u1", summary="unhappy with wait time")
    assert re.fullmatch(r"COMPLAINT-\d{4}-0001", record["id"])


def test_escalation_id_format():
    record = _service().create_escalation(user_id="u1", reason="pain", categories=["severe_pain"])
    assert re.fullmatch(r"ESC-\d{4}-0001", record["id"])
    assert record["priority"] == "high"


def test_ids_increment_per_type():
    service = _service()
    first = service.create_appointment(
        user_id="u", specialty="general_dentistry", preferred_day=None, slot=None
    )
    second = service.create_appointment(
        user_id="u", specialty="general_dentistry", preferred_day=None, slot=None
    )
    assert first["id"].endswith("0001")
    assert second["id"].endswith("0002")
