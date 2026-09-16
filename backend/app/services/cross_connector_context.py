"""D78 bounded process-local cross-connector context store."""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import datetime, timezone
from uuid import UUID

from app.contracts.cross_connector_context import (
    CROSS_CONNECTOR_CONTEXT_TTL,
    CalendarContextEvent,
    CalendarContextSnapshot,
    CrossConnectorContextBundle,
    GmailContextMessage,
    GmailContextSnapshot,
)


CROSS_CONNECTOR_CONTEXT_MAX_CONVERSATIONS = 256


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CrossConnectorContextStore:
    """Keep only fresh owner-approved connector projections in process memory."""

    def __init__(
        self,
        *,
        max_conversations: int = CROSS_CONNECTOR_CONTEXT_MAX_CONVERSATIONS,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        if (
            isinstance(max_conversations, bool)
            or not isinstance(max_conversations, int)
            or max_conversations < 1
        ):
            raise ValueError("max_conversations must be a positive integer.")
        if not callable(clock):
            raise TypeError("clock must be callable.")
        self._max_conversations = max_conversations
        self._clock = clock
        self._items: dict[
            UUID,
            dict[str, GmailContextSnapshot | CalendarContextSnapshot],
        ] = {}
        self._lock = threading.Lock()

    @property
    def conversation_count(self) -> int:
        now = self._now()
        with self._lock:
            self._cleanup_expired(now)
            return len(self._items)

    def capture_gmail(
        self,
        conversation_id: UUID,
        messages: tuple[GmailContextMessage, ...],
    ) -> GmailContextSnapshot:
        conversation_id = self._conversation_id(conversation_id)
        now = self._now()
        snapshot = GmailContextSnapshot(
            conversation_id=conversation_id,
            captured_at=now,
            expires_at=now + CROSS_CONNECTOR_CONTEXT_TTL,
            messages=messages,
        )
        self._put(conversation_id, "gmail", snapshot, now=now)
        return snapshot

    def capture_calendar(
        self,
        conversation_id: UUID,
        events: tuple[CalendarContextEvent, ...],
    ) -> CalendarContextSnapshot:
        conversation_id = self._conversation_id(conversation_id)
        now = self._now()
        snapshot = CalendarContextSnapshot(
            conversation_id=conversation_id,
            captured_at=now,
            expires_at=now + CROSS_CONNECTOR_CONTEXT_TTL,
            events=events,
        )
        self._put(
            conversation_id,
            "google_calendar",
            snapshot,
            now=now,
        )
        return snapshot

    def resolve_gmail(
        self,
        conversation_id: UUID,
    ) -> GmailContextSnapshot | None:
        conversation_id = self._conversation_id(conversation_id)
        now = self._now()
        with self._lock:
            self._cleanup_expired(now)
            snapshot = self._items.get(conversation_id, {}).get("gmail")
            return snapshot if isinstance(snapshot, GmailContextSnapshot) else None

    def resolve_calendar(
        self,
        conversation_id: UUID,
    ) -> CalendarContextSnapshot | None:
        conversation_id = self._conversation_id(conversation_id)
        now = self._now()
        with self._lock:
            self._cleanup_expired(now)
            snapshot = self._items.get(conversation_id, {}).get(
                "google_calendar"
            )
            return (
                snapshot
                if isinstance(snapshot, CalendarContextSnapshot)
                else None
            )

    def resolve_bundle(
        self,
        conversation_id: UUID,
    ) -> CrossConnectorContextBundle | None:
        conversation_id = self._conversation_id(conversation_id)
        now = self._now()
        with self._lock:
            self._cleanup_expired(now)
            sources = self._items.get(conversation_id)
            if sources is None:
                return None
            gmail = sources.get("gmail")
            calendar = sources.get("google_calendar")
            if not isinstance(gmail, GmailContextSnapshot):
                return None
            if not isinstance(calendar, CalendarContextSnapshot):
                return None
            try:
                return CrossConnectorContextBundle(
                    gmail=gmail,
                    calendar=calendar,
                )
            except (TypeError, ValueError):
                return None

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def _put(
        self,
        conversation_id: UUID,
        source: str,
        snapshot: GmailContextSnapshot | CalendarContextSnapshot,
        *,
        now: datetime,
    ) -> None:
        with self._lock:
            self._cleanup_expired(now)
            existing = self._items.get(conversation_id)
            if existing is None:
                if len(self._items) >= self._max_conversations:
                    raise RuntimeError("cross_connector_context_store_full")
                candidate: dict[
                    str,
                    GmailContextSnapshot | CalendarContextSnapshot,
                ] = {}
            else:
                candidate = dict(existing)

            candidate[source] = snapshot
            gmail = candidate.get("gmail")
            calendar = candidate.get("google_calendar")
            if (
                isinstance(gmail, GmailContextSnapshot)
                and isinstance(calendar, CalendarContextSnapshot)
            ):
                CrossConnectorContextBundle(
                    gmail=gmail,
                    calendar=calendar,
                )

            self._items[conversation_id] = candidate

    def _cleanup_expired(self, now: datetime) -> None:
        empty: list[UUID] = []
        for conversation_id, sources in self._items.items():
            expired = [
                source
                for source, snapshot in sources.items()
                if now >= snapshot.expires_at
            ]
            for source in expired:
                sources.pop(source, None)
            if not sources:
                empty.append(conversation_id)
        for conversation_id in empty:
            self._items.pop(conversation_id, None)

    def _now(self) -> datetime:
        try:
            value = self._clock()
        except Exception:
            raise ValueError("cross_connector_context_clock_invalid") from None
        if (
            not isinstance(value, datetime)
            or value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError("cross_connector_context_clock_invalid")
        return value

    @staticmethod
    def _conversation_id(value: object) -> UUID:
        if not isinstance(value, UUID):
            raise TypeError("conversation_id must be a UUID.")
        return value


__all__ = [
    "CROSS_CONNECTOR_CONTEXT_MAX_CONVERSATIONS",
    "CrossConnectorContextStore",
]
