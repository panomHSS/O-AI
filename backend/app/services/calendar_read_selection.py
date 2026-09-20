"""D101 bounded server-side Calendar read-selection store."""

from __future__ import annotations

import secrets
import threading
from collections.abc import Callable, Iterable
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.contracts.calendar_read_selection import CalendarReadSelectionBinding
from app.contracts.google_calendar_write import GoogleCalendarEventTarget
from app.contracts.workspace import WorkspaceId


D101_CALENDAR_READ_SELECTION_MAX_ITEMS = 128
DEFAULT_CALENDAR_READ_SELECTION_TTL = timedelta(minutes=10)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_selection_id() -> str:
    return secrets.token_urlsafe(32)


class CalendarReadSelectionError(RuntimeError):
    """Base error for D101 Calendar read-selection correlation."""


class CalendarReadSelectionNotFoundError(CalendarReadSelectionError):
    pass


class CalendarReadSelectionCollisionError(CalendarReadSelectionError):
    pass


class CalendarReadSelectionStoreFullError(CalendarReadSelectionError):
    pass


class CalendarReadSelectionStore:
    """Bounded process-local exact-target selections; grants no write authority."""

    def __init__(
        self,
        *,
        ttl: timedelta = DEFAULT_CALENDAR_READ_SELECTION_TTL,
        max_items: int = D101_CALENDAR_READ_SELECTION_MAX_ITEMS,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        if not isinstance(ttl, timedelta) or ttl.total_seconds() <= 0:
            raise ValueError("ttl must be a positive timedelta.")
        if (
            isinstance(max_items, bool)
            or not isinstance(max_items, int)
            or max_items < 1
        ):
            raise ValueError("max_items must be a positive integer.")
        self._ttl = ttl
        self._max_items = max_items
        self._clock = clock
        self._items: dict[str, CalendarReadSelectionBinding] = {}
        self._lock = threading.Lock()

    @property
    def ttl(self) -> timedelta:
        return self._ttl

    @property
    def record_count(self) -> int:
        now = self._now()
        with self._lock:
            self._cleanup(now)
            return len(self._items)

    def add(
        self,
        binding: CalendarReadSelectionBinding,
    ) -> CalendarReadSelectionBinding:
        added = self.add_many((binding,))
        return added[0]

    def add_many(
        self,
        bindings: tuple[CalendarReadSelectionBinding, ...],
    ) -> tuple[CalendarReadSelectionBinding, ...]:
        if not isinstance(bindings, tuple) or any(
            not isinstance(item, CalendarReadSelectionBinding)
            for item in bindings
        ):
            raise TypeError(
                "bindings must be a tuple of CalendarReadSelectionBinding."
            )
        if not bindings:
            return ()

        now = self._now()
        with self._lock:
            self._cleanup(now)

            seen_ids: set[str] = set()
            new_items: list[CalendarReadSelectionBinding] = []
            for binding in bindings:
                if binding.expires_at <= now:
                    raise CalendarReadSelectionNotFoundError(
                        "Calendar read selection is unavailable."
                    )
                if binding.selection_id in seen_ids:
                    raise CalendarReadSelectionCollisionError(
                        "selection_id is duplicated in one selection batch."
                    )
                seen_ids.add(binding.selection_id)

                existing = self._items.get(binding.selection_id)
                if existing is not None:
                    if existing != binding:
                        raise CalendarReadSelectionCollisionError(
                            "selection_id is already bound differently."
                        )
                    continue
                new_items.append(binding)

            if len(self._items) + len(new_items) > self._max_items:
                raise CalendarReadSelectionStoreFullError(
                    "Calendar read selection capacity is full."
                )

            for binding in new_items:
                self._items[binding.selection_id] = binding

            return bindings

    def resolve(
        self,
        selection_id: str,
        *,
        workspace_id: WorkspaceId,
        conversation_id: UUID,
    ) -> CalendarReadSelectionBinding:
        if (
            not isinstance(selection_id, str)
            or not selection_id
            or not isinstance(workspace_id, WorkspaceId)
            or not isinstance(conversation_id, UUID)
        ):
            raise CalendarReadSelectionNotFoundError(
                "Calendar read selection is unavailable."
            )

        now = self._now()
        with self._lock:
            self._cleanup(now)
            binding = self._items.get(selection_id)
            if (
                binding is None
                or binding.workspace_id is not workspace_id
                or binding.conversation_id != conversation_id
            ):
                raise CalendarReadSelectionNotFoundError(
                    "Calendar read selection is unavailable."
                )
            return binding

    def consume(
        self,
        selection_id: str,
        *,
        workspace_id: WorkspaceId,
        conversation_id: UUID,
    ) -> CalendarReadSelectionBinding:
        if (
            not isinstance(selection_id, str)
            or not selection_id
            or not isinstance(workspace_id, WorkspaceId)
            or not isinstance(conversation_id, UUID)
        ):
            raise CalendarReadSelectionNotFoundError(
                "Calendar read selection is unavailable."
            )

        now = self._now()
        with self._lock:
            self._cleanup(now)
            binding = self._items.get(selection_id)
            if (
                binding is None
                or binding.workspace_id is not workspace_id
                or binding.conversation_id != conversation_id
            ):
                raise CalendarReadSelectionNotFoundError(
                    "Calendar read selection is unavailable."
                )
            del self._items[selection_id]
            return binding

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def _cleanup(self, now: datetime) -> None:
        expired = [
            selection_id
            for selection_id, binding in self._items.items()
            if binding.expires_at <= now
        ]
        for selection_id in expired:
            del self._items[selection_id]

    def _now(self) -> datetime:
        now = self._clock()
        if (
            not isinstance(now, datetime)
            or now.tzinfo is None
            or now.utcoffset() is None
        ):
            raise ValueError("clock must return a timezone-aware datetime.")
        return now


class CalendarReadSelectionService:
    """Mint opaque selections for validated exact Calendar targets."""

    def __init__(
        self,
        *,
        store: CalendarReadSelectionStore,
        ttl: timedelta = DEFAULT_CALENDAR_READ_SELECTION_TTL,
        clock: Callable[[], datetime] = _utcnow,
        selection_id_factory: Callable[[], str] = _new_selection_id,
    ) -> None:
        if not isinstance(store, CalendarReadSelectionStore):
            raise TypeError("store must be CalendarReadSelectionStore.")
        if not isinstance(ttl, timedelta) or ttl.total_seconds() <= 0:
            raise ValueError("ttl must be a positive timedelta.")
        self._store = store
        self._ttl = ttl
        self._clock = clock
        self._selection_id_factory = selection_id_factory

    def bind_exact_target(
        self,
        *,
        target: GoogleCalendarEventTarget,
        workspace_id: WorkspaceId,
        conversation_id: UUID,
    ) -> CalendarReadSelectionBinding:
        bindings = self.bind_exact_targets(
            targets=(target,),
            workspace_id=workspace_id,
            conversation_id=conversation_id,
        )
        return bindings[0]

    def bind_exact_targets(
        self,
        *,
        targets: tuple[GoogleCalendarEventTarget, ...],
        workspace_id: WorkspaceId,
        conversation_id: UUID,
    ) -> tuple[CalendarReadSelectionBinding, ...]:
        if not isinstance(targets, tuple) or any(
            not isinstance(target, GoogleCalendarEventTarget)
            for target in targets
        ):
            raise ValueError("calendar_read_selection_targets_invalid")
        if not isinstance(workspace_id, WorkspaceId):
            raise ValueError("workspace_id_invalid")
        if not isinstance(conversation_id, UUID):
            raise ValueError("conversation_id_invalid")
        if not targets:
            return ()

        now = self._now()
        bindings = tuple(
            CalendarReadSelectionBinding(
                selection_id=self._selection_id_factory(),
                target=target,
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                expires_at=now + self._ttl,
            )
            for target in targets
        )
        return self._store.add_many(bindings)

    def _now(self) -> datetime:
        now = self._clock()
        if (
            not isinstance(now, datetime)
            or now.tzinfo is None
            or now.utcoffset() is None
        ):
            raise ValueError("clock must return a timezone-aware datetime.")
        return now


__all__ = [
    "D101_CALENDAR_READ_SELECTION_MAX_ITEMS",
    "DEFAULT_CALENDAR_READ_SELECTION_TTL",
    "CalendarReadSelectionCollisionError",
    "CalendarReadSelectionError",
    "CalendarReadSelectionNotFoundError",
    "CalendarReadSelectionService",
    "CalendarReadSelectionStore",
    "CalendarReadSelectionStoreFullError",
]
