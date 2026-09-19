"""D101 bounded server-side Calendar exact-target follow-up service."""

from __future__ import annotations

import secrets
import threading
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.contracts.calendar_write_followup import CalendarWriteFollowupBinding
from app.contracts.google_calendar_write import GoogleCalendarEventTarget
from app.contracts.workspace import WorkspaceId


D101_CALENDAR_WRITE_FOLLOWUP_MAX_ITEMS = 128
DEFAULT_CALENDAR_WRITE_FOLLOWUP_TTL = timedelta(minutes=10)


class CalendarWriteFollowupError(RuntimeError):
    """Base D101 Calendar follow-up error."""


class CalendarWriteFollowupNotFoundError(CalendarWriteFollowupError):
    """Follow-up is unavailable, expired, or outside the exact boundary."""


class CalendarWriteFollowupCollisionError(CalendarWriteFollowupError):
    """Opaque follow-up id is already bound differently."""


class CalendarWriteFollowupPendingError(CalendarWriteFollowupError):
    """One workspace/conversation already has a pending exact target."""


class CalendarWriteFollowupStoreFullError(CalendarWriteFollowupError):
    """Bounded process-local follow-up capacity is full."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_followup_id() -> str:
    return secrets.token_urlsafe(32)


class CalendarWriteFollowupStore:
    """Bounded process-local exact-target correlation; grants no authority."""

    def __init__(
        self,
        *,
        max_items: int = D101_CALENDAR_WRITE_FOLLOWUP_MAX_ITEMS,
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
        self._items: dict[str, CalendarWriteFollowupBinding] = {}
        self._lock = threading.Lock()

    @property
    def record_count(self) -> int:
        now = self._now()
        with self._lock:
            self._cleanup(now)
            return len(self._items)

    def add(
        self,
        binding: CalendarWriteFollowupBinding,
    ) -> CalendarWriteFollowupBinding:
        if not isinstance(binding, CalendarWriteFollowupBinding):
            raise TypeError("binding must be CalendarWriteFollowupBinding.")

        now = self._now()
        with self._lock:
            self._cleanup(now)

            existing = self._items.get(binding.followup_id)
            if existing is not None:
                if existing == binding:
                    return existing
                raise CalendarWriteFollowupCollisionError(
                    "followup_id is already bound differently."
                )

            if any(
                item.workspace_id is binding.workspace_id
                and item.conversation_id == binding.conversation_id
                for item in self._items.values()
            ):
                raise CalendarWriteFollowupPendingError(
                    "workspace conversation already has a pending Calendar follow-up."
                )

            if len(self._items) >= self._max_items:
                raise CalendarWriteFollowupStoreFullError(
                    "Calendar write follow-up capacity is full."
                )

            if binding.expires_at <= now:
                raise CalendarWriteFollowupNotFoundError(
                    "Calendar write follow-up is unavailable."
                )

            self._items[binding.followup_id] = binding
            return binding

    def pending_for_conversation(
        self,
        *,
        workspace_id: WorkspaceId,
        conversation_id: UUID,
    ) -> CalendarWriteFollowupBinding | None:
        if not isinstance(workspace_id, WorkspaceId):
            return None
        if not isinstance(conversation_id, UUID):
            return None

        now = self._now()
        with self._lock:
            self._cleanup(now)
            for binding in self._items.values():
                if (
                    binding.workspace_id is workspace_id
                    and binding.conversation_id == conversation_id
                ):
                    return binding
            return None

    def resolve(
        self,
        followup_id: str,
        *,
        workspace_id: WorkspaceId,
        conversation_id: UUID,
    ) -> CalendarWriteFollowupBinding:
        now = self._now()
        with self._lock:
            self._cleanup(now)
            binding = self._resolve_locked(
                followup_id,
                workspace_id=workspace_id,
                conversation_id=conversation_id,
            )
            return binding

    def consume(
        self,
        followup_id: str,
        *,
        workspace_id: WorkspaceId,
        conversation_id: UUID,
    ) -> CalendarWriteFollowupBinding:
        now = self._now()
        with self._lock:
            self._cleanup(now)
            binding = self._resolve_locked(
                followup_id,
                workspace_id=workspace_id,
                conversation_id=conversation_id,
            )
            self._items.pop(binding.followup_id, None)
            return binding

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def _resolve_locked(
        self,
        followup_id: str,
        *,
        workspace_id: WorkspaceId,
        conversation_id: UUID,
    ) -> CalendarWriteFollowupBinding:
        if (
            type(followup_id) is not str
            or not followup_id
            or followup_id != followup_id.strip()
            or not isinstance(workspace_id, WorkspaceId)
            or not isinstance(conversation_id, UUID)
        ):
            raise CalendarWriteFollowupNotFoundError(
                "Calendar write follow-up is unavailable."
            )

        binding = self._items.get(followup_id)
        if binding is None:
            raise CalendarWriteFollowupNotFoundError(
                "Calendar write follow-up is unavailable."
            )

        if (
            binding.workspace_id is not workspace_id
            or binding.conversation_id != conversation_id
        ):
            raise CalendarWriteFollowupNotFoundError(
                "Calendar write follow-up is unavailable."
            )

        return binding

    def _now(self) -> datetime:
        now = self._clock()
        if (
            not isinstance(now, datetime)
            or now.tzinfo is None
            or now.utcoffset() is None
        ):
            raise ValueError("clock must return a timezone-aware datetime.")
        return now

    def _cleanup(self, now: datetime) -> None:
        expired = [
            followup_id
            for followup_id, binding in self._items.items()
            if now >= binding.expires_at
        ]
        for followup_id in expired:
            self._items.pop(followup_id, None)


class CalendarWriteFollowupService:
    """Create bounded exact-target follow-ups for later server-side proposal use."""

    def __init__(
        self,
        *,
        store: CalendarWriteFollowupStore,
        ttl: timedelta = DEFAULT_CALENDAR_WRITE_FOLLOWUP_TTL,
        clock: Callable[[], datetime] = _utcnow,
        followup_id_factory: Callable[[], str] = _new_followup_id,
    ) -> None:
        if not isinstance(store, CalendarWriteFollowupStore):
            raise TypeError("store must be CalendarWriteFollowupStore.")
        if not isinstance(ttl, timedelta) or ttl.total_seconds() <= 0:
            raise ValueError("ttl must be a positive timedelta.")
        self._store = store
        self._ttl = ttl
        self._clock = clock
        self._followup_id_factory = followup_id_factory

    def bind_exact_target(
        self,
        *,
        target: GoogleCalendarEventTarget,
        workspace_id: WorkspaceId,
        conversation_id: UUID,
    ) -> CalendarWriteFollowupBinding:
        if not isinstance(target, GoogleCalendarEventTarget):
            raise ValueError("calendar_write_followup_target_invalid")
        if not isinstance(workspace_id, WorkspaceId):
            raise ValueError("workspace_id_invalid")
        if not isinstance(conversation_id, UUID):
            raise ValueError("conversation_id_invalid")

        now = self._now()
        binding = CalendarWriteFollowupBinding(
            followup_id=self._followup_id_factory(),
            target=target,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            expires_at=now + self._ttl,
        )
        return self._store.add(binding)

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
    "CalendarWriteFollowupCollisionError",
    "CalendarWriteFollowupError",
    "CalendarWriteFollowupNotFoundError",
    "CalendarWriteFollowupPendingError",
    "CalendarWriteFollowupService",
    "CalendarWriteFollowupStore",
    "CalendarWriteFollowupStoreFullError",
    "D101_CALENDAR_WRITE_FOLLOWUP_MAX_ITEMS",
    "DEFAULT_CALENDAR_WRITE_FOLLOWUP_TTL",
]
