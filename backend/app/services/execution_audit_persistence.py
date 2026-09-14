"""D47 durable, non-authoritative execution audit sinks."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from sqlalchemy.orm import Session

from app.contracts.execution_audit import AuditSink, ExecutionAuditEvent
from app.repositories.execution_audit_events import (
    ExecutionAuditEventRepository,
)


class CompositeAuditSink:
    """Fan out one event to every sink while isolating sibling sink failures."""

    def __init__(
        self,
        sinks: Iterable[AuditSink],
    ) -> None:
        self._sinks = tuple(sinks)
        if not self._sinks:
            raise ValueError(
                "CompositeAuditSink requires at least one sink."
            )

    def record(
        self,
        event: ExecutionAuditEvent,
    ) -> None:
        if not isinstance(event, ExecutionAuditEvent):
            raise TypeError(
                "event must be an ExecutionAuditEvent."
            )

        failed = False
        for sink in self._sinks:
            try:
                sink.record(event)
            except Exception:
                failed = True

        if failed:
            raise RuntimeError(
                "One or more execution audit sinks failed."
            )


class DatabaseAuditSink:
    """Persist one audit event in its own short-lived transaction."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
    ) -> None:
        if not callable(session_factory):
            raise TypeError(
                "session_factory must be callable."
            )
        self._session_factory = session_factory

    def record(
        self,
        event: ExecutionAuditEvent,
    ) -> None:
        if not isinstance(event, ExecutionAuditEvent):
            raise TypeError(
                "event must be an ExecutionAuditEvent."
            )

        session = self._session_factory()
        try:
            repository = ExecutionAuditEventRepository(
                session
            )
            repository.append(event)
            session.commit()
        except Exception:
            try:
                session.rollback()
            except Exception:
                pass
            raise
        finally:
            session.close()
