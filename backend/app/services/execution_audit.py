"""D39 safe, non-authoritative execution audit trail."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timezone

from app.contracts.execution_audit import AuditSink, ExecutionAuditEvent


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InMemoryAuditSink:
    """Ordered in-memory sink for deterministic tests and local inspection."""

    def __init__(self) -> None:
        self._events: list[ExecutionAuditEvent] = []

    @property
    def events(self) -> tuple[ExecutionAuditEvent, ...]:
        return tuple(self._events)

    def record(self, event: ExecutionAuditEvent) -> None:
        if not isinstance(event, ExecutionAuditEvent):
            raise TypeError("event must be an ExecutionAuditEvent.")
        self._events.append(event)


class LoggingAuditSink:
    """Structured standard-library logging sink with an allowlisted payload."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("oai.execution_audit")

    def record(self, event: ExecutionAuditEvent) -> None:
        if not isinstance(event, ExecutionAuditEvent):
            raise TypeError("event must be an ExecutionAuditEvent.")
        payload = {
            "contract_version": event.contract_version,
            "request_id": event.request_id,
            "stage": event.stage,
            "action": event.action,
            "status": event.status,
            "occurred_at": event.occurred_at.isoformat(),
            "target_kind": event.target_kind,
            "adapter_id": event.adapter_id,
            "reason_code": event.reason_code,
            "plan_digest": event.plan_digest,
        }
        self._logger.info(
            "oai.execution_audit",
            extra={"execution_audit": payload},
        )


class ExecutionAuditTrail:
    """Construct safe audit events and isolate all sink failures."""

    def __init__(
        self,
        *,
        sink: AuditSink,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._sink = sink
        self._clock = clock or _utc_now

    def try_record(
        self,
        *,
        request_id: str,
        stage: str,
        action: str,
        status: str,
        target_kind: str | None = None,
        adapter_id: str | None = None,
        reason_code: str | None = None,
        plan_digest: str | None = None,
    ) -> bool:
        """Record one allowlisted event; never raise into business execution."""
        try:
            event = ExecutionAuditEvent(
                request_id=request_id,
                stage=stage,  # type: ignore[arg-type]
                action=action,  # type: ignore[arg-type]
                status=status,  # type: ignore[arg-type]
                occurred_at=self._clock(),
                target_kind=target_kind,  # type: ignore[arg-type]
                adapter_id=adapter_id,
                reason_code=reason_code,
                plan_digest=plan_digest,
            )
            self._sink.record(event)
        except Exception:
            return False
        return True
