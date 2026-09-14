"""Persistence boundary for durable execution audit observations."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contracts.execution_audit import ExecutionAuditEvent
from app.models.execution_audit_event import ExecutionAuditEventRecord


class ExecutionAuditEventRepository:
    """Append and read durable audit records without owning transactions."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def append(
        self,
        event: ExecutionAuditEvent,
    ) -> ExecutionAuditEventRecord:
        if not isinstance(event, ExecutionAuditEvent):
            raise TypeError("event must be an ExecutionAuditEvent.")

        record = ExecutionAuditEventRecord(
            contract_version=event.contract_version,
            request_id=event.request_id,
            stage=event.stage,
            action=event.action,
            status=event.status,
            occurred_at=event.occurred_at,
            target_kind=event.target_kind,
            adapter_id=event.adapter_id,
            reason_code=event.reason_code,
            plan_digest=event.plan_digest,
        )
        self._session.add(record)
        self._session.flush()
        return record

    def list_for_request(
        self,
        request_id: str,
    ) -> list[ExecutionAuditEventRecord]:
        if (
            not isinstance(request_id, str)
            or not request_id
            or request_id != request_id.strip()
        ):
            raise ValueError(
                "request_id must be a non-empty trimmed string."
            )

        statement = (
            select(ExecutionAuditEventRecord)
            .where(
                ExecutionAuditEventRecord.request_id
                == request_id
            )
            .order_by(
                ExecutionAuditEventRecord.id.asc()
            )
        )
        return list(
            self._session.scalars(statement).all()
        )
