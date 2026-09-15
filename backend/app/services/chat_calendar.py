"""D65 deterministic authenticated Google Calendar Chat integration."""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.contracts.chat_plugin_action import (
    CalendarChatWindow,
    ChatPluginActionBinding,
    ChatPluginIntentOutcome,
)
from app.contracts.google_calendar import (
    GOOGLE_CALENDAR_ADAPTER_ID,
    GOOGLE_CALENDAR_OPERATION,
    GOOGLE_CALENDAR_REQUEST_SENTINEL,
)

GOOGLE_CALENDAR_CHAT_ADAPTER_ID = GOOGLE_CALENDAR_ADAPTER_ID
GOOGLE_CALENDAR_CHAT_OPERATION = GOOGLE_CALENDAR_OPERATION
GOOGLE_CALENDAR_CHAT_REQUEST_SENTINEL = GOOGLE_CALENDAR_REQUEST_SENTINEL

_ALLOWED_EVENT_STATUSES = frozenset({"confirmed", "tentative", "cancelled"})
_EVENT_KEYS = frozenset({"all_day", "end", "start", "status", "summary"})
_MAX_EVENTS = 10
_MAX_SUMMARY_BYTES = 1024
_MAX_DISPLAY_SUMMARY_CHARS = 240

_TODAY_PHRASES = frozenset(
    {
        "วันนี้มีนัดอะไรบ้าง",
        "วันนี้มีอะไรในปฏิทิน",
        "ดูนัดวันนี้",
        "เปิดปฏิทินวันนี้",
        "what's on my calendar today",
        "what is on my calendar today",
        "show my calendar today",
        "show my calendar events today",
    }
)
_TOMORROW_PHRASES = frozenset(
    {
        "พรุ่งนี้มีนัดอะไรบ้าง",
        "พรุ่งนี้มีอะไรในปฏิทิน",
        "ดูนัดพรุ่งนี้",
        "เปิดปฏิทินพรุ่งนี้",
        "what's on my calendar tomorrow",
        "what is on my calendar tomorrow",
        "show my calendar tomorrow",
        "show my calendar events tomorrow",
    }
)
_NEXT_7_DAYS_PHRASES = frozenset(
    {
        "7 วันข้างหน้ามีนัดอะไรบ้าง",
        "7 วันข้างหน้ามีอะไรในปฏิทิน",
        "ดูนัด 7 วันข้างหน้า",
        "เปิดปฏิทิน 7 วันข้างหน้า",
        "show my upcoming calendar events",
        "what's on my calendar for the next 7 days",
        "what is on my calendar for the next 7 days",
        "show my calendar for the next 7 days",
    }
)

_NON_ACTION_MARKERS = (
    "สมมติ",
    "ตัวอย่าง",
    "ถ้าฉันถาม",
    "ถ้าถามว่า",
    "อย่า",
    "ไม่ต้อง",
    "example",
    "for example",
    "if i ask",
    "don't",
    "do not",
)
_CALENDAR_SIGNALS = ("calendar", "ปฏิทิน", "นัด")
_ACTION_SIGNALS = ("show", "what", "ดู", "เปิด", "มี")
_WINDOW_SIGNALS = {
    "today": ("today", "วันนี้"),
    "tomorrow": ("tomorrow", "พรุ่งนี้"),
    "next_7_days": (
        "next 7 days",
        "upcoming",
        "7 วันข้างหน้า",
        "7 วันข้างหน้",
    ),
}
_TERMINAL_PUNCTUATION_RE = re.compile(r"[.?!。！？]+$")


@dataclass(frozen=True, slots=True)
class CalendarWindowSnapshot:
    window: CalendarChatWindow
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.window not in {"today", "tomorrow", "next_7_days"}:
            raise ValueError("Unsupported Calendar window.")
        for value in (self.start, self.end):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("Calendar window boundaries must be timezone-aware.")
        if self.end <= self.start:
            raise ValueError("Calendar window end must follow start.")


class CalendarChatIntentRouter:
    """Recognize only a deliberately narrow owner Calendar grammar."""

    def classify(self, message: object) -> ChatPluginIntentOutcome:
        if not isinstance(message, str) or not message.strip():
            return ChatPluginIntentOutcome(status="none")

        raw = message.strip()
        if any(marker in raw for marker in ('"', "“", "”", "`")):
            return ChatPluginIntentOutcome(status="none")

        normalized = self._normalize(message)
        if any(marker in normalized for marker in _NON_ACTION_MARKERS):
            return ChatPluginIntentOutcome(status="none")

        window = self._exact_window(normalized)
        if window is not None:
            return ChatPluginIntentOutcome(
                status="matched",
                calendar_window=window,
                calendar_intent=True,
            )

        if not (
            any(signal in normalized for signal in _CALENDAR_SIGNALS)
            and any(signal in normalized for signal in _ACTION_SIGNALS)
        ):
            return ChatPluginIntentOutcome(status="none")

        window_hits = {
            name
            for name, signals in _WINDOW_SIGNALS.items()
            if any(signal in normalized for signal in signals)
        }
        if len(window_hits) >= 1:
            return ChatPluginIntentOutcome(
                status="invalid",
                calendar_intent=True,
            )
        return ChatPluginIntentOutcome(status="none")

    @staticmethod
    def _normalize(value: str) -> str:
        folded = value.strip().casefold().replace("’", "'")
        folded = " ".join(folded.split())
        return _TERMINAL_PUNCTUATION_RE.sub("", folded).strip()

    @staticmethod
    def _exact_window(normalized: str) -> CalendarChatWindow | None:
        if normalized in _TODAY_PHRASES:
            return "today"
        if normalized in _TOMORROW_PHRASES:
            return "tomorrow"
        if normalized in _NEXT_7_DAYS_PHRASES:
            return "next_7_days"
        return None


class CalendarChatWindowResolver:
    """Snapshot relative Calendar words in the configured owner timezone."""

    def __init__(
        self,
        owner_timezone: str,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if (
            not isinstance(owner_timezone, str)
            or not owner_timezone
            or owner_timezone != owner_timezone.strip()
            or len(owner_timezone) > 128
        ):
            raise ValueError("owner_timezone must be a non-empty timezone name.")
        self._owner_timezone = owner_timezone
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def snapshot(self, window: CalendarChatWindow) -> CalendarWindowSnapshot:
        zone = self._zone()
        now = self._now().astimezone(zone)

        if window == "next_7_days":
            return CalendarWindowSnapshot(
                window=window,
                start=now,
                end=now + timedelta(days=7),
            )

        target_date = now.date()
        if window == "tomorrow":
            target_date += timedelta(days=1)
        elif window != "today":
            raise ValueError("Unsupported Calendar window.")

        start = datetime.combine(target_date, time.min, tzinfo=zone)
        end = datetime.combine(
            target_date + timedelta(days=1),
            time.min,
            tzinfo=zone,
        )
        return CalendarWindowSnapshot(window=window, start=start, end=end)

    def _zone(self):
        try:
            return ZoneInfo(self._owner_timezone)
        except (ZoneInfoNotFoundError, ValueError):
            if self._owner_timezone == "Asia/Bangkok":
                return timezone(timedelta(hours=7), name="Asia/Bangkok")
            raise ValueError("calendar_owner_timezone_invalid") from None

    def _now(self) -> datetime:
        try:
            value = self._clock()
        except Exception:
            raise ValueError("calendar_owner_clock_invalid") from None
        if (
            not isinstance(value, datetime)
            or value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError("calendar_owner_clock_invalid")
        return value


@dataclass(frozen=True, slots=True)
class _DisplayEvent:
    summary: str
    status: str
    all_day: bool
    start: datetime
    end: datetime


class CalendarChatCompletionComposer:
    """Validate, filter and render authorized Calendar output without an AI model."""

    DENIED_REPLY = (
        "ยกเลิกการอ่าน Google Calendar "
        "ตามการตัดสินใจของเจ้าของแล้วครับ"
    )
    FAILURE_REPLY = "ไม่สามารถอ่านข้อมูลจาก Google Calendar ได้ในครั้งนี้ครับ"

    def reply_for_approved(self, binding, outcome) -> str:
        if binding.calendar_window is None:
            raise ValueError("Calendar completion requires Calendar binding.")

        execution = outcome.execution
        result = execution.result
        if (
            execution.status != "completed"
            or result is None
            or result.status != "succeeded"
        ):
            return self.FAILURE_REPLY

        events = self._validated_events(result.output, binding)
        if events is None:
            return self.FAILURE_REPLY

        filtered = tuple(
            event
            for event in events
            if event.start < binding.calendar_window_end
            and event.end > binding.calendar_window_start
        )
        filtered = tuple(sorted(filtered, key=lambda item: (item.start, item.end)))

        if not filtered:
            return self._empty_reply(binding.calendar_window)

        header = self._header(binding.calendar_window, len(filtered))
        lines = [header, ""]
        for index, event in enumerate(filtered, start=1):
            lines.append(
                f"{index}. {self._event_when(event, binding.calendar_window)} "
                f"— {self._safe_summary(event.summary)}"
                f"{self._status_suffix(event.status)}"
            )
        return "\n".join(lines)

    def _validated_events(
        self,
        output: object,
        binding: ChatPluginActionBinding,
    ) -> tuple[_DisplayEvent, ...] | None:
        if not isinstance(output, Mapping) or set(output) != {"content"}:
            return None
        content = output.get("content")
        if not isinstance(content, str) or len(content.encode("utf-8")) > 16 * 1024:
            return None
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict) or set(payload) != {"events"}:
            return None
        raw_events = payload.get("events")
        if not isinstance(raw_events, list) or len(raw_events) > _MAX_EVENTS:
            return None

        zone = binding.calendar_window_start.tzinfo
        if zone is None:
            return None

        events: list[_DisplayEvent] = []
        for raw in raw_events:
            event = self._validated_event(raw, zone)
            if event is None:
                return None
            events.append(event)
        return tuple(events)

    @classmethod
    def _validated_event(cls, raw: object, zone) -> _DisplayEvent | None:
        if not isinstance(raw, dict) or set(raw) != _EVENT_KEYS:
            return None

        summary = raw.get("summary")
        status = raw.get("status")
        all_day = raw.get("all_day")
        start_raw = raw.get("start")
        end_raw = raw.get("end")
        if (
            not isinstance(summary, str)
            or not summary
            or len(summary.encode("utf-8")) > _MAX_SUMMARY_BYTES
            or status not in _ALLOWED_EVENT_STATUSES
            or type(all_day) is not bool
            or not isinstance(start_raw, str)
            or not isinstance(end_raw, str)
        ):
            return None

        try:
            if all_day:
                if len(start_raw.encode("utf-8")) > 32 or len(end_raw.encode("utf-8")) > 32:
                    return None
                start_date = date.fromisoformat(start_raw)
                end_date = date.fromisoformat(end_raw)
                start = datetime.combine(start_date, time.min, tzinfo=zone)
                end = datetime.combine(end_date, time.min, tzinfo=zone)
            else:
                if len(start_raw.encode("utf-8")) > 128 or len(end_raw.encode("utf-8")) > 128:
                    return None
                start = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
                end = datetime.fromisoformat(end_raw.replace("Z", "+00:00"))
                if (
                    start.tzinfo is None
                    or start.utcoffset() is None
                    or end.tzinfo is None
                    or end.utcoffset() is None
                ):
                    return None
                start = start.astimezone(zone)
                end = end.astimezone(zone)
        except ValueError:
            return None

        if end <= start:
            return None
        return _DisplayEvent(
            summary=summary,
            status=status,
            all_day=all_day,
            start=start,
            end=end,
        )

    @staticmethod
    def _header(window: CalendarChatWindow, count: int) -> str:
        if window == "today":
            return f"วันนี้มี {count} รายการครับ"
        if window == "tomorrow":
            return f"พรุ่งนี้มี {count} รายการครับ"
        return f"7 วันข้างหน้ามี {count} รายการครับ"

    @staticmethod
    def _empty_reply(window: CalendarChatWindow) -> str:
        if window == "today":
            label = "วันนี้"
        elif window == "tomorrow":
            label = "พรุ่งนี้"
        else:
            label = "7 วันข้างหน้า"
        return (
            f"{label}ไม่มีนัดใน Google Calendar "
            "ที่พบในช่วงที่ตรวจสอบครับ"
        )

    @staticmethod
    def _event_when(event: _DisplayEvent, window: CalendarChatWindow) -> str:
        if event.all_day:
            if window == "next_7_days":
                return f"{event.start:%d/%m} ทั้งวัน"
            return "ทั้งวัน"

        same_day = event.start.date() == event.end.date()
        if window != "next_7_days" and same_day:
            return f"{event.start:%H:%M}–{event.end:%H:%M}"
        return f"{event.start:%d/%m %H:%M}–{event.end:%d/%m %H:%M}"

    @staticmethod
    def _status_suffix(status: str) -> str:
        if status == "tentative":
            return " (ยังไม่ยืนยัน)"
        if status == "cancelled":
            return " (ยกเลิก)"
        return ""

    @staticmethod
    def _safe_summary(value: str) -> str:
        cleaned = "".join(
            " " if unicodedata.category(character).startswith("C") else character
            for character in value
        )
        cleaned = " ".join(cleaned.split())
        if len(cleaned) > _MAX_DISPLAY_SUMMARY_CHARS:
            cleaned = cleaned[: _MAX_DISPLAY_SUMMARY_CHARS - 1].rstrip() + "…"
        if not cleaned:
            cleaned = "—"
        markdown_chars = "\\`*_{}[]()#+-.!>|~"
        escaped: list[str] = []
        for character in cleaned:
            if character in markdown_chars:
                escaped.append("\\")
            escaped.append(character)
        return "".join(escaped)
