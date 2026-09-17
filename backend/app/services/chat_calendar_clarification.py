"""Bounded non-authoritative Calendar date clarification state."""

from __future__ import annotations

import re
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Literal, TypeAlias
from uuid import UUID


CALENDAR_CLARIFICATION_MAX_ITEMS = 128
CALENDAR_CLARIFICATION_TTL = timedelta(minutes=5)

CalendarClarificationStatus: TypeAlias = Literal[
    "none",
    "positive",
    "negative",
    "expired",
    "unrelated",
]

_POSITIVE_PHRASES = frozenset(
    {
        "ใช่",
        "ใช่ครับ",
        "ใช่ค่ะ",
        "ถูกต้อง",
        "ถูกต้องครับ",
        "ถูกต้องค่ะ",
    }
)
_NEGATIVE_PHRASES = frozenset(
    {
        "ไม่ใช่",
        "ไม่ใช่ครับ",
        "ไม่ใช่ค่ะ",
        "ยกเลิก",
        "ยกเลิกครับ",
    }
)
_TERMINAL_PUNCTUATION_RE = re.compile(r"[.?!。！？]+$")


@dataclass(frozen=True, slots=True)
class PendingCalendarClarification:
    conversation_id: UUID
    candidate_date: date
    expires_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.conversation_id, UUID):
            raise TypeError("conversation_id must be a UUID.")
        if type(self.candidate_date) is not date:
            raise TypeError("candidate_date must be an exact date.")
        if (
            not isinstance(self.expires_at, datetime)
            or self.expires_at.tzinfo is None
            or self.expires_at.utcoffset() is None
        ):
            raise ValueError("expires_at must be timezone-aware.")


@dataclass(frozen=True, slots=True)
class CalendarClarificationResolution:
    status: CalendarClarificationStatus
    candidate_date: date | None = None

    def __post_init__(self) -> None:
        if self.status not in {
            "none",
            "positive",
            "negative",
            "expired",
            "unrelated",
        }:
            raise ValueError("Unsupported Calendar clarification status.")
        if self.status == "positive":
            if type(self.candidate_date) is not date:
                raise ValueError(
                    "positive clarification requires candidate_date."
                )
        elif self.candidate_date is not None:
            raise ValueError(
                "non-positive clarification must not carry candidate_date."
            )


class CalendarClarificationStore:
    """Process-local bounded clarification only; grants no authority."""

    def __init__(
        self,
        *,
        max_items: int = CALENDAR_CLARIFICATION_MAX_ITEMS,
        ttl: timedelta = CALENDAR_CLARIFICATION_TTL,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if (
            isinstance(max_items, bool)
            or not isinstance(max_items, int)
            or max_items < 1
            or max_items > CALENDAR_CLARIFICATION_MAX_ITEMS
        ):
            raise ValueError("max_items must be between 1 and 128.")
        if not isinstance(ttl, timedelta) or ttl <= timedelta(0):
            raise ValueError("ttl must be a positive timedelta.")
        if ttl > CALENDAR_CLARIFICATION_TTL:
            raise ValueError("ttl must not exceed five minutes.")
        self._max_items = max_items
        self._ttl = ttl
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._items: dict[UUID, PendingCalendarClarification] = {}
        self._lock = threading.Lock()

    def add(
        self,
        conversation_id: UUID,
        candidate_date: date,
    ) -> PendingCalendarClarification:
        if not isinstance(conversation_id, UUID):
            raise TypeError("conversation_id must be a UUID.")
        if type(candidate_date) is not date:
            raise TypeError("candidate_date must be an exact date.")

        now = self._now()
        pending = PendingCalendarClarification(
            conversation_id=conversation_id,
            candidate_date=candidate_date,
            expires_at=now + self._ttl,
        )
        with self._lock:
            self._cleanup_expired(now, keep=conversation_id)
            if (
                conversation_id not in self._items
                and len(self._items) >= self._max_items
            ):
                raise RuntimeError("calendar_clarification_store_full")
            self._items[conversation_id] = pending
        return pending

    def classify(
        self,
        conversation_id: UUID | None,
        message: object,
    ) -> CalendarClarificationStatus:
        if not isinstance(conversation_id, UUID):
            return "none"
        normalized = self._normalize(message)
        with self._lock:
            pending = self._items.get(conversation_id)
            if pending is None:
                return "none"
            if normalized in _POSITIVE_PHRASES:
                if self._now() >= pending.expires_at:
                    return "expired"
                return "positive"
            if normalized in _NEGATIVE_PHRASES:
                if self._now() >= pending.expires_at:
                    return "expired"
                return "negative"
            return "unrelated"

    def consume_response(
        self,
        conversation_id: UUID,
        message: object,
    ) -> CalendarClarificationResolution:
        if not isinstance(conversation_id, UUID):
            return CalendarClarificationResolution(status="none")
        normalized = self._normalize(message)
        with self._lock:
            pending = self._items.get(conversation_id)
            if pending is None:
                return CalendarClarificationResolution(status="none")

            if normalized not in (_POSITIVE_PHRASES | _NEGATIVE_PHRASES):
                return CalendarClarificationResolution(status="unrelated")

            self._items.pop(conversation_id, None)
            if self._now() >= pending.expires_at:
                return CalendarClarificationResolution(status="expired")
            if normalized in _NEGATIVE_PHRASES:
                return CalendarClarificationResolution(status="negative")
            return CalendarClarificationResolution(
                status="positive",
                candidate_date=pending.candidate_date,
            )

    def clear(self, conversation_id: UUID | None) -> bool:
        if not isinstance(conversation_id, UUID):
            return False
        with self._lock:
            return self._items.pop(conversation_id, None) is not None

    def clear_all(self) -> None:
        with self._lock:
            self._items.clear()

    def _cleanup_expired(
        self,
        now: datetime,
        *,
        keep: UUID | None = None,
    ) -> None:
        expired = [
            conversation_id
            for conversation_id, pending in self._items.items()
            if conversation_id != keep and now >= pending.expires_at
        ]
        for conversation_id in expired:
            self._items.pop(conversation_id, None)

    def _now(self) -> datetime:
        try:
            value = self._clock()
        except Exception:
            raise ValueError("calendar_clarification_clock_invalid") from None
        if (
            not isinstance(value, datetime)
            or value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError("calendar_clarification_clock_invalid")
        return value.astimezone(timezone.utc)

    @staticmethod
    def _normalize(message: object) -> str:
        if not isinstance(message, str):
            return ""
        folded = message.strip().casefold().replace("’", "'")
        folded = " ".join(folded.split())
        return _TERMINAL_PUNCTUATION_RE.sub("", folded).strip()
