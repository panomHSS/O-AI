"""D101 exact Update owner-decision correlation store."""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import datetime, timezone
from uuid import UUID

from app.contracts.calendar_update_decision import CalendarUpdateDecisionBinding
from app.contracts.workspace import WorkspaceId


D101_CALENDAR_UPDATE_DECISION_MAX_ITEMS = 128


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CalendarUpdateDecisionError(RuntimeError):
    """Base D101 Update decision correlation error."""


class CalendarUpdateDecisionNotFoundError(CalendarUpdateDecisionError):
    pass


class CalendarUpdateDecisionCollisionError(CalendarUpdateDecisionError):
    pass


class CalendarUpdateDecisionPendingError(CalendarUpdateDecisionError):
    pass


class CalendarUpdateDecisionStoreFullError(CalendarUpdateDecisionError):
    pass


class CalendarUpdateDecisionStore:
    """Bounded process-local owner decision correlation; grants no authority."""

    def __init__(
        self,
        *,
        max_items: int = D101_CALENDAR_UPDATE_DECISION_MAX_ITEMS,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        if (
            isinstance(max_items, bool)
            or not isinstance(max_items, int)
            or max_items < 1
        ):
            raise ValueError("max_items must be a positive integer.")
        self._max_items = max_items
        self._clock = clock
        self._items: dict[str, CalendarUpdateDecisionBinding] = {}
        self._lock = threading.Lock()

    @property
    def record_count(self) -> int:
        now = self._now()
        with self._lock:
            self._cleanup(now)
            return len(self._items)

    def add(
        self,
        binding: CalendarUpdateDecisionBinding,
    ) -> CalendarUpdateDecisionBinding:
        if not isinstance(binding, CalendarUpdateDecisionBinding):
            raise TypeError("binding must be CalendarUpdateDecisionBinding.")

        now = self._now()
        with self._lock:
            self._cleanup(now)

            existing = self._items.get(binding.approval_id)
            if existing is not None:
                if existing == binding:
                    return existing
                raise CalendarUpdateDecisionCollisionError(
                    "approval_id is already bound differently."
                )

            if any(
                item.workspace_id is binding.workspace_id
                and item.conversation_id == binding.conversation_id
                for item in self._items.values()
            ):
                raise CalendarUpdateDecisionPendingError(
                    "workspace conversation already has a pending Update decision."
                )

            if len(self._items) >= self._max_items:
                raise CalendarUpdateDecisionStoreFullError(
                    "Calendar Update decision capacity is full."
                )

            if binding.expires_at <= now:
                raise CalendarUpdateDecisionNotFoundError(
                    "Calendar Update decision is unavailable."
                )

            self._items[binding.approval_id] = binding
            return binding

    def resolve(
        self,
        approval_id: str,
        write_digest: str,
        *,
        workspace_id: WorkspaceId,
        conversation_id: UUID,
    ) -> CalendarUpdateDecisionBinding:
        now = self._now()
        with self._lock:
            self._cleanup(now)
            binding = self._items.get(approval_id)
            if (
                binding is None
                or binding.write_digest != write_digest
                or binding.workspace_id is not workspace_id
                or binding.conversation_id != conversation_id
            ):
                raise CalendarUpdateDecisionNotFoundError(
                    "Calendar Update decision is unavailable."
                )
            return binding

    def consume(
        self,
        approval_id: str,
        write_digest: str,
        *,
        workspace_id: WorkspaceId,
        conversation_id: UUID,
    ) -> CalendarUpdateDecisionBinding:
        now = self._now()
        with self._lock:
            self._cleanup(now)
            binding = self._items.get(approval_id)
            if (
                binding is None
                or binding.write_digest != write_digest
                or binding.workspace_id is not workspace_id
                or binding.conversation_id != conversation_id
            ):
                raise CalendarUpdateDecisionNotFoundError(
                    "Calendar Update decision is unavailable."
                )
            del self._items[approval_id]
            return binding

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def _cleanup(self, now: datetime) -> None:
        expired = [
            approval_id
            for approval_id, binding in self._items.items()
            if binding.expires_at <= now
        ]
        for approval_id in expired:
            del self._items[approval_id]

    def _now(self) -> datetime:
        now = self._clock()
        if (
            not isinstance(now, datetime)
            or now.tzinfo is None
            or now.utcoffset() is None
        ):
            raise ValueError("clock must return a timezone-aware datetime.")
        return now


class CalendarUpdateDecisionBindingService:
    """Bind one D73 proposal to exact owner workspace/conversation correlation."""

    def __init__(self, *, store: CalendarUpdateDecisionStore) -> None:
        if not isinstance(store, CalendarUpdateDecisionStore):
            raise TypeError("store must be CalendarUpdateDecisionStore.")
        self._store = store

    def bind_proposal(
        self,
        *,
        approval_id: str,
        write_digest: str,
        workspace_id: WorkspaceId,
        conversation_id: UUID,
        expires_at: datetime,
    ) -> CalendarUpdateDecisionBinding:
        return self._store.add(
            CalendarUpdateDecisionBinding(
                approval_id=approval_id,
                write_digest=write_digest,
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                expires_at=expires_at,
            )
        )


__all__ = [
    "D101_CALENDAR_UPDATE_DECISION_MAX_ITEMS",
    "CalendarUpdateDecisionBindingService",
    "CalendarUpdateDecisionCollisionError",
    "CalendarUpdateDecisionError",
    "CalendarUpdateDecisionNotFoundError",
    "CalendarUpdateDecisionPendingError",
    "CalendarUpdateDecisionStore",
    "CalendarUpdateDecisionStoreFullError",
]
