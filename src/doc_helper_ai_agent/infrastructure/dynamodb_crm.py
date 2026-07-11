"""DynamoDB-backed CRM repository."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, NoReturn
from uuid import uuid4

import boto3
from botocore.exceptions import (
    ClientError,
    ConnectionClosedError,
    ConnectTimeoutError,
    CredentialRetrievalError,
    EndpointConnectionError,
    HTTPClientError,
    NoCredentialsError,
    PartialCredentialsError,
    ReadTimeoutError,
)

from doc_helper_ai_agent.core.errors import CRMRepositoryError
from doc_helper_ai_agent.core.logging import get_logger
from doc_helper_ai_agent.domain.enums import TicketType

logger = get_logger(__name__)

_PREFIXES: dict[TicketType, str] = {
    TicketType.APPOINTMENT: "APPT",
    TicketType.CALLBACK: "CALLBACK",
    TicketType.COMPLAINT: "COMPLAINT",
    TicketType.ESCALATION: "ESC",
}

_OPERATIONAL_ERRORS = (
    ClientError,
    CredentialRetrievalError,
    NoCredentialsError,
    PartialCredentialsError,
    EndpointConnectionError,
    ConnectionClosedError,
    ConnectTimeoutError,
    ReadTimeoutError,
    HTTPClientError,
)


def _raise_repository_error(
    exc: Exception,
    *,
    record_type: str,
    record_id: str,
) -> NoReturn:
    error_code = (
        exc.response.get("Error", {}).get("Code", type(exc).__name__)
        if isinstance(exc, ClientError)
        else type(exc).__name__
    )
    logger.error(
        "DynamoDB CRM write failed record_type=%s record_id=%s aws_error_code=%s exception=%s",
        record_type,
        record_id,
        error_code,
        type(exc).__name__,
    )
    raise CRMRepositoryError("CRM persistence is temporarily unavailable.") from exc


class DynamoDBCRMRepository:
    """Persist CRM records using a DynamoDB table."""

    def __init__(
        self,
        table_name: str,
        region_name: str,
        ttl_days: int = 90,
        dynamodb_resource: Any | None = None,
    ) -> None:
        if dynamodb_resource is None:
            try:
                dynamodb_resource = boto3.resource("dynamodb", region_name=region_name)
            except _OPERATIONAL_ERRORS as exc:
                _raise_repository_error(
                    exc,
                    record_type="unavailable",
                    record_id="unavailable",
                )
        self._table = dynamodb_resource.Table(table_name)
        self._ttl_days = ttl_days

    def _create(
        self,
        *,
        ticket_type: TicketType,
        user_id: str,
        status: str,
        priority: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        created_at = now.isoformat()
        record_id = f"{_PREFIXES[ticket_type]}-{now.year}-{uuid4().hex[:12].upper()}"
        item = {
            "record_id": record_id,
            "record_type": ticket_type.value,
            "user_id": user_id,
            "status": status,
            "priority": priority,
            "created_at": created_at,
            "updated_at": created_at,
            "payload": payload,
            "expires_at": int((now + timedelta(days=self._ttl_days)).timestamp()),
        }
        try:
            self._table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(record_id)",
            )
        except _OPERATIONAL_ERRORS as exc:
            _raise_repository_error(
                exc,
                record_type=ticket_type.value,
                record_id=record_id,
            )
        return {
            **payload,
            "id": record_id,
            "type": ticket_type.value,
            "user_id": user_id,
            "status": status,
            "priority": priority,
            "created_at": created_at,
        }

    def create_appointment_request(
        self,
        *,
        user_id: str,
        specialty: str,
        preferred_day: str | None,
        slot: dict[str, Any] | None,
        notes: str = "",
    ) -> dict[str, Any]:
        return self._create(
            ticket_type=TicketType.APPOINTMENT,
            user_id=user_id,
            status="pending_confirmation",
            priority="normal",
            payload={
                "specialty": specialty,
                "preferred_day": preferred_day,
                "slot": slot,
                "notes": notes,
            },
        )

    def create_callback_request(
        self,
        *,
        user_id: str,
        reason: str,
        priority: str = "normal",
    ) -> dict[str, Any]:
        return self._create(
            ticket_type=TicketType.CALLBACK,
            user_id=user_id,
            status="open",
            priority=priority,
            payload={"reason": reason},
        )

    def create_complaint_ticket(
        self,
        *,
        user_id: str,
        summary: str,
    ) -> dict[str, Any]:
        return self._create(
            ticket_type=TicketType.COMPLAINT,
            user_id=user_id,
            status="open",
            priority="normal",
            payload={"summary": summary},
        )

    def create_human_escalation_ticket(
        self,
        *,
        user_id: str,
        reason: str,
        categories: list[str] | None = None,
        priority: str = "high",
    ) -> dict[str, Any]:
        return self._create(
            ticket_type=TicketType.ESCALATION,
            user_id=user_id,
            status="open",
            priority=priority,
            payload={"reason": reason, "categories": categories or []},
        )
