from __future__ import annotations

import ast
import logging
import re
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import boto3
import pytest
from botocore.exceptions import (
    ClientError,
    ConnectionClosedError,
    ConnectTimeoutError,
    CredentialRetrievalError,
    EndpointConnectionError,
    HTTPClientError,
    NoCredentialsError,
    ParamValidationError,
    PartialCredentialsError,
    ReadTimeoutError,
)
from moto import mock_aws
from pydantic import ValidationError as PydanticValidationError

from doc_helper_ai_agent.core.config import Settings, get_settings
from doc_helper_ai_agent.core.errors import CRMRepositoryError, DocHelperError
from doc_helper_ai_agent.dependencies import (
    Container,
    _build_crm_repository,
    get_container,
    reset_container,
)
from doc_helper_ai_agent.domain.enums import TicketType
from doc_helper_ai_agent.infrastructure.dynamodb_crm import DynamoDBCRMRepository
from doc_helper_ai_agent.infrastructure.mock_crm import MockCRMRepository, reset_crm
from doc_helper_ai_agent.services.intake_service import reset_intake_service


@pytest.fixture
def dynamodb_resource(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    with mock_aws():
        resource = boto3.resource("dynamodb", region_name="us-east-1")
        resource.create_table(
            TableName="doc-helper-records",
            KeySchema=[{"AttributeName": "record_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "record_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield resource


@pytest.fixture
def repository(dynamodb_resource: Any) -> DynamoDBCRMRepository:
    return DynamoDBCRMRepository(
        table_name="doc-helper-records",
        region_name="us-east-1",
        dynamodb_resource=dynamodb_resource,
    )


class _FailingTable:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def put_item(self, **_: Any) -> None:
        raise self.error


class _FakeResource:
    def __init__(self, table: Any) -> None:
        self.table = table

    def Table(self, _: str) -> Any:  # noqa: N802
        return self.table


class _RecordingTable:
    def __init__(self) -> None:
        self.put_kwargs: dict[str, Any] | None = None

    def put_item(self, **kwargs: Any) -> None:
        self.put_kwargs = kwargs


class _TableFailingResource:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def Table(self, _: str) -> Any:  # noqa: N802
        raise self.error


OPERATIONAL_ERRORS = [
    NoCredentialsError(),
    PartialCredentialsError(provider="test", cred_var="key"),
    CredentialRetrievalError(provider="test", error_msg="failed"),
    EndpointConnectionError(endpoint_url="https://example.invalid"),
    ConnectionClosedError(endpoint_url="https://example.invalid", request="request"),
    ConnectTimeoutError(endpoint_url="https://example.invalid"),
    ReadTimeoutError(endpoint_url="https://example.invalid"),
    HTTPClientError(error=RuntimeError("transport failed")),
]


def test_aws_sdk_imports_are_isolated_to_dynamodb_adapter():
    package_root = Path(__file__).parents[1] / "src" / "doc_helper_ai_agent"
    offenders = []
    for path in package_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name.split(".", 1)[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module.split(".", 1)[0]]
            else:
                continue
            if {"boto3", "botocore"}.intersection(modules):
                offenders.append(path.relative_to(package_root).as_posix())
    assert sorted(set(offenders)) == ["infrastructure/dynamodb_crm.py"]


def _assert_common_item(
    *,
    table: Any,
    returned: dict[str, Any],
    prefix: str,
    record_type: str,
    user_id: str,
    status: str,
    priority: str,
) -> dict[str, Any]:
    assert re.fullmatch(rf"{prefix}-\d{{4}}-[0-9A-F]{{12}}", returned["id"])
    item = table.get_item(Key={"record_id": returned["id"]})["Item"]
    assert item["record_id"] == returned["id"]
    assert item["record_type"] == record_type
    assert item["user_id"] == returned["user_id"] == user_id
    assert item["status"] == returned["status"] == status
    assert item["priority"] == returned["priority"] == priority
    assert item["created_at"] == item["updated_at"] == returned["created_at"]
    created_at = datetime.fromisoformat(item["created_at"])
    assert created_at.utcoffset() == timedelta(0)
    assert isinstance(item["payload"], dict)
    # DynamoDB Numbers are deserialized to Decimal by the boto3 resource API.
    assert isinstance(item["expires_at"], Decimal)
    assert item["expires_at"] == int(item["expires_at"])
    return item


def test_crm_settings_defaults_to_mock(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("CRM_PROVIDER", raising=False)
    settings = Settings(_env_file=None)
    assert settings.crm_provider == "mock"
    assert settings.dynamodb_table_name == "doc-helper-records"
    assert settings.aws_region == "us-east-1"
    assert settings.crm_record_ttl_days == 90


def test_crm_settings_accept_dynamodb():
    settings = Settings(CRM_PROVIDER="dynamodb", _env_file=None)
    assert settings.crm_provider == "dynamodb"


def test_crm_settings_reject_unknown_provider():
    with pytest.raises(PydanticValidationError):
        Settings(CRM_PROVIDER="unknown", _env_file=None)


def test_crm_repository_error_uses_existing_error_contract():
    error = CRMRepositoryError("CRM persistence is temporarily unavailable.")
    assert isinstance(error, DocHelperError)
    assert error.status_code == 503
    assert error.error_code == "crm_unavailable"


def test_container_selects_mock_repository():
    container = Container(Settings(CRM_PROVIDER="mock", _env_file=None))
    assert isinstance(container.crm, MockCRMRepository)
    assert container.intake._crm is container.crm


def test_container_selects_dynamodb_without_creating_aws_resource(
    monkeypatch: pytest.MonkeyPatch,
):
    sentinel = MockCRMRepository()
    calls = {}

    def fake_adapter(**kwargs: Any):
        calls.update(kwargs)
        return sentinel

    monkeypatch.setattr(
        "doc_helper_ai_agent.dependencies.DynamoDBCRMRepository",
        fake_adapter,
    )
    settings = Settings(
        CRM_PROVIDER="dynamodb",
        DYNAMODB_TABLE_NAME="table-test",
        AWS_REGION="eu-west-1",
        CRM_RECORD_TTL_DAYS=12,
        _env_file=None,
    )
    container = Container(settings)
    assert container.crm is sentinel
    assert container.intake._crm is container.crm
    assert calls == {"table_name": "table-test", "region_name": "eu-west-1", "ttl_days": 12}


def test_container_factory_rejects_unexpected_provider():
    settings = Settings(CRM_PROVIDER="mock", _env_file=None)
    object.__setattr__(settings, "crm_provider", "unsupported")

    with pytest.raises(ValueError, match="^Unsupported CRM_PROVIDER: unsupported$"):
        _build_crm_repository(settings)


def test_mock_singletons_reset_to_fresh_container_and_record_ids():
    assert get_settings().crm_provider == "mock"
    first_container = get_container()
    first_container.intake.create_callback(user_id="user", reason="first")

    reset_container()
    reset_intake_service()
    reset_crm()
    get_settings.cache_clear()

    second_container = get_container()
    first_record = second_container.intake.create_callback(user_id="user", reason="second")

    assert first_record["id"].endswith("0001")


def test_create_appointment_persists_and_returns_canonical_record(
    repository: DynamoDBCRMRepository,
    dynamodb_resource: Any,
):
    table = dynamodb_resource.Table("doc-helper-records")
    returned = repository.create_appointment_request(
        user_id="user-1",
        specialty="whitening",
        preferred_day="friday",
        slot=None,
        notes="Call first",
    )

    item = _assert_common_item(
        table=table,
        returned=returned,
        prefix="APPT",
        record_type="appointment",
        user_id="user-1",
        status="pending_confirmation",
        priority="normal",
    )
    assert item["payload"] == {
        "specialty": "whitening",
        "preferred_day": "friday",
        "slot": None,
        "notes": "Call first",
    }
    assert returned["slot"] is None

    slot = {
        "doctor_id": "dr-1",
        "doctor_name": "Dr Test",
        "specialty": "whitening",
        "day": "friday",
        "time": "09:30",
    }
    returned = repository.create_appointment_request(
        user_id="user-1",
        specialty="whitening",
        preferred_day="friday",
        slot=slot,
    )
    item = table.get_item(Key={"record_id": returned["id"]})["Item"]
    assert returned["slot"] == slot
    assert item["payload"]["slot"] == slot


def test_create_callback_persists_and_returns_canonical_record(
    repository: DynamoDBCRMRepository,
    dynamodb_resource: Any,
):
    returned = repository.create_callback_request(
        user_id="user-2",
        reason="Reschedule",
        priority="urgent",
    )
    item = _assert_common_item(
        table=dynamodb_resource.Table("doc-helper-records"),
        returned=returned,
        prefix="CALLBACK",
        record_type="callback",
        user_id="user-2",
        status="open",
        priority="urgent",
    )
    assert item["payload"]["reason"] == returned["reason"] == "Reschedule"


def test_create_complaint_persists_return_contract_and_configured_ttl(
    dynamodb_resource: Any,
):
    repository = DynamoDBCRMRepository(
        table_name="doc-helper-records",
        region_name="us-east-1",
        ttl_days=7,
        dynamodb_resource=dynamodb_resource,
    )
    lower = int((datetime.now(UTC) + timedelta(days=6, minutes=-1)).timestamp())
    returned = repository.create_complaint_ticket(user_id="user-3", summary="Long wait")
    upper = int((datetime.now(UTC) + timedelta(days=7, minutes=1)).timestamp())

    item = _assert_common_item(
        table=dynamodb_resource.Table("doc-helper-records"),
        returned=returned,
        prefix="COMPLAINT",
        record_type="complaint",
        user_id="user-3",
        status="open",
        priority="normal",
    )
    assert item["payload"]["summary"] == returned["summary"] == "Long wait"
    assert lower <= item["expires_at"] <= upper


def test_create_escalation_normalizes_categories_and_preserves_priority(
    repository: DynamoDBCRMRepository,
    dynamodb_resource: Any,
):
    returned = repository.create_human_escalation_ticket(
        user_id="user-4",
        reason="Needs staff",
        categories=None,
        priority="critical",
    )
    item = _assert_common_item(
        table=dynamodb_resource.Table("doc-helper-records"),
        returned=returned,
        prefix="ESC",
        record_type="escalation",
        user_id="user-4",
        status="open",
        priority="critical",
    )
    assert item["payload"]["reason"] == returned["reason"] == "Needs staff"
    assert item["payload"]["categories"] == returned["categories"] == []


def test_canonical_values_take_precedence_over_payload(
    repository: DynamoDBCRMRepository,
):
    returned = repository._create(
        ticket_type=TicketType.COMPLAINT,
        user_id="canonical-user",
        status="open",
        priority="normal",
        payload={
            "summary": "safe",
            "id": "bad-id",
            "type": "bad-type",
            "user_id": "bad-user",
            "status": "bad-status",
            "priority": "bad-priority",
            "created_at": "bad-time",
        },
    )
    assert returned["id"] != "bad-id"
    assert returned["type"] == "complaint"
    assert returned["user_id"] == "canonical-user"
    assert returned["status"] == "open"
    assert returned["priority"] == "normal"
    assert returned["created_at"] != "bad-time"


def test_put_item_receives_integer_ttl_and_exact_condition_expression():
    table = _RecordingTable()
    repository = DynamoDBCRMRepository(
        table_name="unused",
        region_name="us-east-1",
        dynamodb_resource=_FakeResource(table),
    )

    repository.create_complaint_ticket(user_id="user", summary="summary")

    assert table.put_kwargs is not None
    assert table.put_kwargs["ConditionExpression"] == "attribute_not_exists(record_id)"
    assert isinstance(table.put_kwargs["Item"]["expires_at"], int)


@pytest.mark.parametrize("original", OPERATIONAL_ERRORS, ids=lambda error: type(error).__name__)
def test_put_item_operational_errors_are_translated_and_chained(original: Exception):
    repository = DynamoDBCRMRepository(
        table_name="unused",
        region_name="us-east-1",
        dynamodb_resource=_FakeResource(_FailingTable(original)),
    )

    with pytest.raises(CRMRepositoryError) as raised:
        repository.create_callback_request(user_id="user", reason="reason")

    assert raised.value.__cause__ is original


def test_put_item_client_error_is_translated_chained_and_safely_logged(
    caplog: pytest.LogCaptureFixture,
):
    original = ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "denied"}},
        "PutItem",
    )
    repository = DynamoDBCRMRepository(
        table_name="unused",
        region_name="us-east-1",
        dynamodb_resource=_FakeResource(_FailingTable(original)),
    )
    sensitive = ["USER-SECRET-7Q9", "REASON-SECRET-7Q9", "CATEGORY-SECRET-7Q9"]

    with caplog.at_level(logging.ERROR), pytest.raises(CRMRepositoryError) as raised:
        repository.create_human_escalation_ticket(
            user_id=sensitive[0],
            reason=sensitive[1],
            categories=[sensitive[2]],
        )

    assert raised.value.__cause__ is original
    for value in sensitive:
        assert value not in caplog.text
    assert "AccessDeniedException" in caplog.text
    assert "ClientError" in caplog.text
    assert "escalation" in caplog.text


@pytest.mark.parametrize(
    ("method", "kwargs", "sensitive"),
    [
        (
            "create_appointment_request",
            {
                "user_id": "APPT-USER-SECRET",
                "specialty": "APPT-SPECIALTY-SECRET",
                "preferred_day": None,
                "slot": None,
                "notes": "APPT-NOTES-SECRET",
            },
            ["APPT-USER-SECRET", "APPT-SPECIALTY-SECRET", "APPT-NOTES-SECRET"],
        ),
        (
            "create_complaint_ticket",
            {"user_id": "COMPLAINT-USER-SECRET", "summary": "COMPLAINT-SUMMARY-SECRET"},
            ["COMPLAINT-USER-SECRET", "COMPLAINT-SUMMARY-SECRET"],
        ),
    ],
)
def test_write_failure_logs_do_not_expose_other_payloads(
    method: str,
    kwargs: dict[str, Any],
    sensitive: list[str],
    caplog: pytest.LogCaptureFixture,
):
    original = EndpointConnectionError(endpoint_url="https://example.invalid")
    repository = DynamoDBCRMRepository(
        table_name="unused",
        region_name="us-east-1",
        dynamodb_resource=_FakeResource(_FailingTable(original)),
    )

    with caplog.at_level(logging.ERROR), pytest.raises(CRMRepositoryError):
        getattr(repository, method)(**kwargs)

    for value in sensitive:
        assert value not in caplog.text


def test_param_validation_error_propagates_unchanged():
    original = ParamValidationError(report="invalid sentinel")
    repository = DynamoDBCRMRepository(
        table_name="unused",
        region_name="us-east-1",
        dynamodb_resource=_FakeResource(_FailingTable(original)),
    )

    with pytest.raises(ParamValidationError) as raised:
        repository.create_complaint_ticket(user_id="user", summary="summary")

    assert raised.value is original


@pytest.mark.parametrize("original", OPERATIONAL_ERRORS, ids=lambda error: type(error).__name__)
def test_resource_construction_operational_errors_are_translated_and_chained(
    original: Exception,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    def fail_resource(*_: Any, **__: Any) -> None:
        raise original

    monkeypatch.setattr(
        "doc_helper_ai_agent.infrastructure.dynamodb_crm.boto3.resource", fail_resource
    )

    with caplog.at_level(logging.ERROR), pytest.raises(CRMRepositoryError) as raised:
        DynamoDBCRMRepository(
            table_name="SENSITIVE-TABLE-NAME",
            region_name="SENSITIVE-REGION-NAME",
        )

    assert raised.value.__cause__ is original
    assert type(original).__name__ in caplog.text
    assert "SENSITIVE" not in caplog.text


def test_resource_construction_client_error_is_safely_logged(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    original = ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "SENSITIVE-AWS-MESSAGE"}},
        "Resource",
    )

    def fail_resource(*_: Any, **__: Any) -> None:
        raise original

    monkeypatch.setattr(
        "doc_helper_ai_agent.infrastructure.dynamodb_crm.boto3.resource", fail_resource
    )

    with caplog.at_level(logging.ERROR), pytest.raises(CRMRepositoryError) as raised:
        DynamoDBCRMRepository(
            table_name="SENSITIVE-TABLE-NAME",
            region_name="SENSITIVE-REGION-NAME",
        )

    assert raised.value.__cause__ is original
    assert "AccessDeniedException" in caplog.text
    assert "ClientError" in caplog.text
    assert "SENSITIVE" not in caplog.text
    assert "record_type=unavailable" in caplog.text
    assert "record_id=unavailable" in caplog.text


@pytest.mark.parametrize(
    "original",
    [
        ParamValidationError(report="invalid resource sentinel"),
        RuntimeError("programming sentinel"),
    ],
    ids=lambda error: type(error).__name__,
)
def test_resource_construction_non_operational_errors_propagate_unchanged(
    original: Exception,
    monkeypatch: pytest.MonkeyPatch,
):
    def fail_resource(*_: Any, **__: Any) -> None:
        raise original

    monkeypatch.setattr(
        "doc_helper_ai_agent.infrastructure.dynamodb_crm.boto3.resource", fail_resource
    )

    with pytest.raises(type(original)) as raised:
        DynamoDBCRMRepository(table_name="unused", region_name="us-east-1")

    assert raised.value is original


def test_table_resolution_errors_are_not_translated():
    original = EndpointConnectionError(endpoint_url="https://example.invalid")

    with pytest.raises(EndpointConnectionError) as raised:
        DynamoDBCRMRepository(
            table_name="unused",
            region_name="us-east-1",
            dynamodb_resource=_TableFailingResource(original),
        )

    assert raised.value is original
