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

from app.contracts.cross_connector_context import CalendarContextEvent
from app.contracts.chat_plugin_action import (
    CalendarChatWindow,
    ChatPluginActionBinding,
    ChatPluginIntentOutcome,
)
from app.contracts.google_calendar import (
    GOOGLE_CALENDAR_ADAPTER_ID,
    GOOGLE_CALENDAR_OPERATION,
    GOOGLE_CALENDAR_REQUEST_SENTINEL,
    GOOGLE_CALENDAR_TIME_MAX_PARAMETER,
    GOOGLE_CALENDAR_TIME_MIN_PARAMETER,
)

GOOGLE_CALENDAR_CHAT_ADAPTER_ID = GOOGLE_CALENDAR_ADAPTER_ID
GOOGLE_CALENDAR_CHAT_OPERATION = GOOGLE_CALENDAR_OPERATION
GOOGLE_CALENDAR_CHAT_REQUEST_SENTINEL = GOOGLE_CALENDAR_REQUEST_SENTINEL
GOOGLE_CALENDAR_CHAT_TIME_MIN_PARAMETER = GOOGLE_CALENDAR_TIME_MIN_PARAMETER
GOOGLE_CALENDAR_CHAT_TIME_MAX_PARAMETER = GOOGLE_CALENDAR_TIME_MAX_PARAMETER

_ALLOWED_EVENT_STATUSES = frozenset({"confirmed", "tentative", "cancelled"})
_EVENT_KEYS = frozenset({"all_day", "end", "event_id", "start", "status", "summary"})
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
        "พรุ่งนี้ผมมีนัดอะไรบ้าง",
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
_THIS_WEEK_PHRASES = frozenset(
    {
        "สัปดาห์นี้มีนัดอะไรบ้าง",
        "อาทิตย์นี้มีนัดอะไรบ้าง",
        "สัปดาห์นี้มีอะไรในปฏิทิน",
        "ดูนัดสัปดาห์นี้",
        "what's on my calendar this week",
        "what is on my calendar this week",
        "show my calendar this week",
    }
)
_NEXT_WEEK_PHRASES = frozenset(
    {
        "สัปดาห์หน้ามีนัดอะไรบ้าง",
        "อาทิตย์หน้ามีนัดอะไรบ้าง",
        "สัปดาห์หน้ามีอะไรในปฏิทิน",
        "ดูนัดสัปดาห์หน้า",
        "what's on my calendar next week",
        "what is on my calendar next week",
        "show my calendar next week",
    }
)
_THIS_MONTH_PHRASES = frozenset(
    {
        "เดือนนี้มีนัดอะไรบ้าง",
        "เดือนนี้มีอะไรในปฏิทิน",
        "ดูนัดเดือนนี้",
        "what's on my calendar this month",
        "what is on my calendar this month",
        "show my calendar this month",
    }
)


_TODAY_MORNING_PHRASES = frozenset(
    {
        "วันนี้ตอนเช้ามีนัดอะไรบ้าง",
        "วันนี้ช่วงเช้ามีนัดอะไรบ้าง",
        "วันนี้ตอนเช้ามีอะไรในปฏิทิน",
        "วันนี้ช่วงเช้ามีอะไรในปฏิทิน",
        "วันนี้ตอนเช้ามีนัดไหม",
        "วันนี้ช่วงเช้ามีนัดไหม",
        "what's on my calendar this morning",
        "what is on my calendar this morning",
        "show my calendar this morning",
    }
)
_TODAY_AFTERNOON_PHRASES = frozenset(
    {
        "วันนี้ตอนบ่ายมีนัดอะไรบ้าง",
        "วันนี้ช่วงบ่ายมีนัดอะไรบ้าง",
        "วันนี้ตอนบ่ายมีอะไรในปฏิทิน",
        "วันนี้ช่วงบ่ายมีอะไรในปฏิทิน",
        "วันนี้ตอนบ่ายมีนัดไหม",
        "วันนี้ช่วงบ่ายมีนัดไหม",
        "what's on my calendar this afternoon",
        "what is on my calendar this afternoon",
        "show my calendar this afternoon",
    }
)
_TODAY_EVENING_PHRASES = frozenset(
    {
        "วันนี้ตอนเย็นมีนัดอะไรบ้าง",
        "วันนี้ช่วงเย็นมีนัดอะไรบ้าง",
        "วันนี้ตอนเย็นมีอะไรในปฏิทิน",
        "วันนี้ช่วงเย็นมีอะไรในปฏิทิน",
        "วันนี้ตอนเย็นมีนัดไหม",
        "วันนี้ช่วงเย็นมีนัดไหม",
        "what's on my calendar this evening",
        "what is on my calendar this evening",
        "show my calendar this evening",
    }
)
_TOMORROW_MORNING_PHRASES = frozenset(
    {
        "พรุ่งนี้ตอนเช้ามีนัดอะไรบ้าง",
        "พรุ่งนี้ช่วงเช้ามีนัดอะไรบ้าง",
        "พรุ่งนี้ตอนเช้ามีอะไรในปฏิทิน",
        "พรุ่งนี้ช่วงเช้ามีอะไรในปฏิทิน",
        "พรุ่งนี้ตอนเช้ามีนัดไหม",
        "พรุ่งนี้ช่วงเช้ามีนัดไหม",
        "what's on my calendar tomorrow morning",
        "what is on my calendar tomorrow morning",
        "show my calendar tomorrow morning",
    }
)
_TOMORROW_AFTERNOON_PHRASES = frozenset(
    {
        "พรุ่งนี้ตอนบ่ายมีนัดอะไรบ้าง",
        "พรุ่งนี้ช่วงบ่ายมีนัดอะไรบ้าง",
        "พรุ่งนี้ตอนบ่ายมีอะไรในปฏิทิน",
        "พรุ่งนี้ช่วงบ่ายมีอะไรในปฏิทิน",
        "พรุ่งนี้ตอนบ่ายมีนัดไหม",
        "พรุ่งนี้ช่วงบ่ายมีนัดไหม",
        "what's on my calendar tomorrow afternoon",
        "what is on my calendar tomorrow afternoon",
        "show my calendar tomorrow afternoon",
    }
)
_TOMORROW_EVENING_PHRASES = frozenset(
    {
        "พรุ่งนี้ตอนเย็นมีนัดอะไรบ้าง",
        "พรุ่งนี้ช่วงเย็นมีนัดอะไรบ้าง",
        "พรุ่งนี้ตอนเย็นมีอะไรในปฏิทิน",
        "พรุ่งนี้ช่วงเย็นมีอะไรในปฏิทิน",
        "พรุ่งนี้ตอนเย็นมีนัดไหม",
        "พรุ่งนี้ช่วงเย็นมีนัดไหม",
        "what's on my calendar tomorrow evening",
        "what is on my calendar tomorrow evening",
        "show my calendar tomorrow evening",
    }
)
_UPCOMING_WEEKEND_PHRASES = frozenset(
    {
        "เสาร์-อาทิตย์มีนัดอะไรบ้าง",
        "เสาร์-อาทิตย์มีอะไรในปฏิทิน",
        "สุดสัปดาห์นี้มีนัดอะไรบ้าง",
        "สุดสัปดาห์นี้มีอะไรในปฏิทิน",
        "ดูนัดสุดสัปดาห์นี้",
        "what's on my calendar this weekend",
        "what is on my calendar this weekend",
        "show my calendar this weekend",
    }
)
_NEXT_WEEKEND_PHRASES = frozenset(
    {
        "สุดสัปดาห์หน้ามีนัดอะไรบ้าง",
        "สุดสัปดาห์หน้ามีอะไรในปฏิทิน",
        "ดูนัดสุดสัปดาห์หน้า",
        "what's on my calendar next weekend",
        "what is on my calendar next weekend",
        "show my calendar next weekend",
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
    "this_week": ("this week", "สัปดาห์นี้", "อาทิตย์นี้"),
    "next_week": ("next week", "สัปดาห์หน้า", "อาทิตย์หน้า"),
    "this_month": ("this month", "เดือนนี้"),
    "today_morning": ("this morning", "today morning", "วันนี้ตอนเช้า", "วันนี้ช่วงเช้า"),
    "today_afternoon": ("this afternoon", "today afternoon", "วันนี้ตอนบ่าย", "วันนี้ช่วงบ่าย"),
    "today_evening": ("this evening", "today evening", "วันนี้ตอนเย็น", "วันนี้ช่วงเย็น"),
    "tomorrow_morning": ("tomorrow morning", "พรุ่งนี้ตอนเช้า", "พรุ่งนี้ช่วงเช้า"),
    "tomorrow_afternoon": ("tomorrow afternoon", "พรุ่งนี้ตอนบ่าย", "พรุ่งนี้ช่วงบ่าย"),
    "tomorrow_evening": ("tomorrow evening", "พรุ่งนี้ตอนเย็น", "พรุ่งนี้ช่วงเย็น"),
    "upcoming_weekend": ("this weekend", "weekend", "เสาร์-อาทิตย์", "สุดสัปดาห์นี้"),
    "next_weekend": ("next weekend", "สุดสัปดาห์หน้า"),
}
_TERMINAL_PUNCTUATION_RE = re.compile(r"[.?!。！？]+$")


_POLITE_SUFFIXES = (
    "\u0e04\u0e23\u0e31\u0e1a\u0e1c\u0e21",
    "\u0e04\u0e23\u0e31\u0e1a",
    "\u0e04\u0e48\u0e30",
    "\u0e04\u0e30",
    "\u0e2b\u0e19\u0e48\u0e2d\u0e22",
)
_VOCATIVE_SUFFIX_RE = re.compile(r"\s+\u0e42\u0e2d$")


def _strip_bounded_calendar_suffixes(value: str) -> str:
    candidate = _VOCATIVE_SUFFIX_RE.sub("", value).rstrip()

    for _ in range(2):
        for suffix in _POLITE_SUFFIXES:
            if candidate.endswith(suffix):
                candidate = candidate[:-len(suffix)].rstrip()
                break
        else:
            break

    return candidate



CalendarSpecificDateStatus = str

_SPECIFIC_DATE_RE = re.compile(
    r"(?<!\d)(?:วันที่\s*)?(\d{1,2})/(\d{1,2})(?:/(\d{4}))?(?!\d)"
)


@dataclass(frozen=True, slots=True)
class CalendarSpecificDateParse:
    status: CalendarSpecificDateStatus
    date: date | None = None
    source_year: int | None = None
    reason_code: str | None = None

    def __post_init__(self) -> None:
        if self.status not in {"none", "exact", "needs_confirmation", "invalid"}:
            raise ValueError("Unsupported specific-date parse status.")
        if self.status in {"exact", "needs_confirmation"}:
            if type(self.date) is not date:
                raise ValueError("specific-date parse requires one Gregorian date.")
            if self.reason_code is not None:
                raise ValueError("successful specific-date parse cannot carry reason_code.")
            return
        if self.date is not None or self.source_year is not None:
            raise ValueError("non-date parse must not carry date metadata.")
        if self.status == "none" and self.reason_code is not None:
            raise ValueError("none parse must not carry reason_code.")
        if self.status == "invalid" and self.reason_code not in {
            "calendar_specific_date_invalid",
            "calendar_specific_date_ambiguous",
            "calendar_specific_date_multiple",
        }:
            raise ValueError("invalid specific-date parse requires bounded reason_code.")


class CalendarSpecificDateParser:
    """Parse one bounded numeric Calendar date without AI or connector access."""

    def __init__(self, owner_timezone: str, *, clock: Callable[[], datetime] | None = None) -> None:
        if (not isinstance(owner_timezone, str) or not owner_timezone or
                owner_timezone != owner_timezone.strip() or len(owner_timezone) > 128):
            raise ValueError("owner_timezone must be a non-empty timezone name.")
        self._owner_timezone = owner_timezone
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def parse(self, message: object) -> CalendarSpecificDateParse:
        if not isinstance(message, str) or not message.strip():
            return CalendarSpecificDateParse(status="none")
        raw = message.strip()
        if any(marker in raw for marker in ('"', "“", "”", "`")):
            return CalendarSpecificDateParse(status="none")
        normalized = CalendarChatIntentRouter._normalize(raw)
        if any(marker in normalized for marker in _NON_ACTION_MARKERS):
            return CalendarSpecificDateParse(status="none")
        if not (any(signal in normalized for signal in _CALENDAR_SIGNALS) and
                any(signal in normalized for signal in _ACTION_SIGNALS)):
            return CalendarSpecificDateParse(status="none")
        matches = tuple(_SPECIFIC_DATE_RE.finditer(normalized))
        if not matches:
            return CalendarSpecificDateParse(status="none")
        if len(matches) > 1:
            return CalendarSpecificDateParse(status="invalid", reason_code="calendar_specific_date_multiple")
        match = matches[0]
        day = int(match.group(1))
        month = int(match.group(2))
        year_text = match.group(3)
        if year_text is None:
            candidate = self._validated_date(self._owner_now().year, month, day)
            if candidate is None:
                return CalendarSpecificDateParse(status="invalid", reason_code="calendar_specific_date_invalid")
            return CalendarSpecificDateParse(status="needs_confirmation", date=candidate)
        source_year = int(year_text)
        year = source_year - 543 if source_year >= 2400 else source_year
        candidate = self._validated_date(year, month, day)
        if candidate is None:
            return CalendarSpecificDateParse(status="invalid", reason_code="calendar_specific_date_invalid")
        return CalendarSpecificDateParse(status="exact", date=candidate, source_year=source_year)

    @staticmethod
    def _validated_date(year: int, month: int, day: int) -> date | None:
        try:
            return date(year, month, day)
        except ValueError:
            return None

    def _owner_now(self) -> datetime:
        try:
            value = self._clock()
        except Exception:
            raise ValueError("calendar_owner_clock_invalid") from None
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("calendar_owner_clock_invalid")
        return value.astimezone(self._zone())

    def _zone(self):
        try:
            return ZoneInfo(self._owner_timezone)
        except (ZoneInfoNotFoundError, ValueError):
            if self._owner_timezone == "Asia/Bangkok":
                return timezone(timedelta(hours=7), name="Asia/Bangkok")
            raise ValueError("calendar_owner_timezone_invalid") from None

@dataclass(frozen=True, slots=True)
class CalendarWindowSnapshot:
    window: CalendarChatWindow
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.window not in {
            "today",
            "tomorrow",
            "next_7_days",
            "this_week",
            "next_week",
            "this_month",
            "today_morning",
            "today_afternoon",
            "today_evening",
            "tomorrow_morning",
            "tomorrow_afternoon",
            "tomorrow_evening",
            "upcoming_weekend",
            "next_weekend",
            "exact_date",
        }:
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
        candidate = _strip_bounded_calendar_suffixes(normalized)

        if candidate in _TODAY_PHRASES:
            return "today"
        if candidate in _TOMORROW_PHRASES:
            return "tomorrow"
        if candidate in _NEXT_7_DAYS_PHRASES:
            return "next_7_days"
        if candidate in _THIS_WEEK_PHRASES:
            return "this_week"
        if candidate in _NEXT_WEEK_PHRASES:
            return "next_week"
        if candidate in _THIS_MONTH_PHRASES:
            return "this_month"
        if candidate in _TODAY_MORNING_PHRASES:
            return "today_morning"
        if candidate in _TODAY_AFTERNOON_PHRASES:
            return "today_afternoon"
        if candidate in _TODAY_EVENING_PHRASES:
            return "today_evening"
        if candidate in _TOMORROW_MORNING_PHRASES:
            return "tomorrow_morning"
        if candidate in _TOMORROW_AFTERNOON_PHRASES:
            return "tomorrow_afternoon"
        if candidate in _TOMORROW_EVENING_PHRASES:
            return "tomorrow_evening"
        if candidate in _UPCOMING_WEEKEND_PHRASES:
            return "upcoming_weekend"
        if candidate in _NEXT_WEEKEND_PHRASES:
            return "next_weekend"
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

    def snapshot_exact_date(self, target_date: date) -> CalendarWindowSnapshot:
        if type(target_date) is not date:
            raise TypeError("target_date must be an exact date.")
        zone = self._zone()
        start = datetime.combine(target_date, time.min, tzinfo=zone)
        end = datetime.combine(target_date + timedelta(days=1), time.min, tzinfo=zone)
        return CalendarWindowSnapshot(window="exact_date", start=start, end=end)

    def snapshot(self, window: CalendarChatWindow) -> CalendarWindowSnapshot:
        if window == "exact_date":
            raise ValueError("exact_date requires snapshot_exact_date().")
        zone = self._zone()
        now = self._now().astimezone(zone).replace(microsecond=0)

        if window == "next_7_days":
            return CalendarWindowSnapshot(
                window=window,
                start=now,
                end=now + timedelta(days=7),
            )

        daypart_windows = {
            "today_morning": (0, time(6, 0), time(12, 0)),
            "today_afternoon": (0, time(12, 0), time(17, 0)),
            "today_evening": (0, time(17, 0), time(21, 0)),
            "tomorrow_morning": (1, time(6, 0), time(12, 0)),
            "tomorrow_afternoon": (1, time(12, 0), time(17, 0)),
            "tomorrow_evening": (1, time(17, 0), time(21, 0)),
        }
        daypart = daypart_windows.get(window)
        if daypart is not None:
            day_offset, start_time, end_time = daypart
            target_date = now.date() + timedelta(days=day_offset)
            start = datetime.combine(target_date, start_time, tzinfo=zone)
            end = datetime.combine(target_date, end_time, tzinfo=zone)
            return CalendarWindowSnapshot(window=window, start=start, end=end)

        if window in {"upcoming_weekend", "next_weekend"}:
            weekday = now.weekday()
            if weekday == 5:
                saturday = now.date()
            elif weekday == 6:
                saturday = now.date() - timedelta(days=1)
            else:
                saturday = now.date() + timedelta(days=5 - weekday)
            if window == "next_weekend":
                saturday += timedelta(days=7)
            start = datetime.combine(saturday, time.min, tzinfo=zone)
            end = datetime.combine(
                saturday + timedelta(days=2),
                time.min,
                tzinfo=zone,
            )
            return CalendarWindowSnapshot(window=window, start=start, end=end)

        if window in {"today", "tomorrow"}:
            target_date = now.date()
            if window == "tomorrow":
                target_date += timedelta(days=1)
            start = datetime.combine(target_date, time.min, tzinfo=zone)
            end = datetime.combine(
                target_date + timedelta(days=1),
                time.min,
                tzinfo=zone,
            )
            return CalendarWindowSnapshot(window=window, start=start, end=end)

        if window in {"this_week", "next_week"}:
            week_start_date = now.date() - timedelta(days=now.weekday())
            if window == "next_week":
                week_start_date += timedelta(days=7)
            start = datetime.combine(week_start_date, time.min, tzinfo=zone)
            end = datetime.combine(
                week_start_date + timedelta(days=7),
                time.min,
                tzinfo=zone,
            )
            return CalendarWindowSnapshot(window=window, start=start, end=end)

        if window == "this_month":
            month_start_date = now.date().replace(day=1)
            if month_start_date.month == 12:
                next_month_date = month_start_date.replace(
                    year=month_start_date.year + 1,
                    month=1,
                )
            else:
                next_month_date = month_start_date.replace(
                    month=month_start_date.month + 1,
                )
            start = datetime.combine(month_start_date, time.min, tzinfo=zone)
            end = datetime.combine(next_month_date, time.min, tzinfo=zone)
            return CalendarWindowSnapshot(window=window, start=start, end=end)

        raise ValueError("Unsupported Calendar window.")

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
    event_id: str
    summary: str
    status: str
    all_day: bool
    start: datetime
    end: datetime


class CalendarChatCompletionComposer:
    """Validate, filter and render authorized Calendar output without an AI model."""

    HISTORY_SAFE_REPLY = (
        "Google Calendar result was displayed as untrusted external data; "
        "calendar content was not retained in AI conversation context."
    )

    DENIED_REPLY = (
        "ยกเลิกการอ่าน Google Calendar "
        "ตามการตัดสินใจของเจ้าของแล้วครับ"
    )
    FAILURE_REPLY = "ไม่สามารถอ่านข้อมูลจาก Google Calendar ได้ในครั้งนี้ครับ"

    _ERROR_REPLIES = {
        "calendar_invalid_credential": (
            "อ่าน Calendar ไม่สำเร็จ: ข้อมูลรับรองการเชื่อมต่อไม่พร้อมครับ"
        ),
        "calendar_invalid_clock": (
            "อ่าน Calendar ไม่สำเร็จ: เวลาระบบไม่ถูกต้องครับ"
        ),
        "calendar_connector_timeout": (
            "อ่าน Calendar ไม่สำเร็จ: การเชื่อมต่อใช้เวลานานเกินกำหนดครับ"
        ),
        "calendar_connector_network_error": (
            "อ่าน Calendar ไม่สำเร็จ: การเชื่อมต่อเครือข่ายผิดพลาดครับ"
        ),
        "calendar_connector_http_error": (
            "อ่าน Calendar ไม่สำเร็จ: บริการ Calendar ตอบกลับผิดพลาดครับ"
        ),
        "calendar_authentication_failed": (
            "อ่าน Calendar ไม่สำเร็จ: สิทธิ์การเชื่อมต่อไม่พร้อมครับ"
        ),
        "calendar_response_too_large": (
            "อ่าน Calendar ไม่สำเร็จ: ผลลัพธ์เกินขีดจำกัดที่ปลอดภัยครับ"
        ),
        "calendar_invalid_json": (
            "อ่าน Calendar ไม่สำเร็จ: รูปแบบข้อมูลตอบกลับไม่ถูกต้องครับ"
        ),
        "calendar_invalid_response": (
            "อ่าน Calendar ไม่สำเร็จ: ข้อมูลตอบกลับไม่ถูกต้องครับ"
        ),
        "calendar_credential_unavailable": (
            "อ่าน Calendar ไม่สำเร็จ: ยังไม่มีสิทธิ์การเชื่อมต่อที่พร้อมใช้งานครับ"
        ),
        "calendar_invalid_request": (
            "อ่าน Calendar ไม่สำเร็จ: คำขอ Calendar ไม่ถูกต้องครับ"
        ),
    }

    def reply_for_approved(self, binding, outcome) -> str:
        if binding.calendar_window is None:
            raise ValueError("Calendar completion requires Calendar binding.")

        execution = outcome.execution
        result = execution.result
        if execution.status != "completed" or result is None:
            return self.FAILURE_REPLY
        if result.status != "succeeded":
            return self._ERROR_REPLIES.get(result.error, self.FAILURE_REPLY)

        validated = self._validated_payload(result.output, binding)
        if validated is None:
            return self.FAILURE_REPLY
        events, truncated = validated

        filtered = tuple(
            event
            for event in events
            if event.start < binding.calendar_window_end
            and event.end > binding.calendar_window_start
        )
        filtered = tuple(sorted(filtered, key=lambda item: (item.start, item.end)))

        if not filtered:
            return self._with_truncation_note(
                self._empty_reply(binding.calendar_window),
                truncated,
            )

        header = self._header(binding.calendar_window, len(filtered))
        lines = [header, ""]
        for index, event in enumerate(filtered, start=1):
            lines.append(
                f"{index}. {self._event_when(event, binding.calendar_window)} "
                f"— {self._safe_summary(event.summary)}"
                f"{self._status_suffix(event.status)}"
            )
        return self._with_truncation_note("\n".join(lines), truncated)

    def display_events_for_approved(
        self,
        binding: ChatPluginActionBinding,
        outcome: object,
    ) -> tuple[_DisplayEvent, ...] | None:
        """Return validated owner-visible Calendar events with server-only identity."""
        if binding.calendar_window is None:
            return None
        execution = getattr(outcome, "execution", None)
        result = getattr(execution, "result", None)
        if (
            getattr(execution, "status", None) != "completed"
            or result is None
            or getattr(result, "status", None) != "succeeded"
        ):
            return None

        validated = self._validated_payload(
            getattr(result, "output", None),
            binding,
        )
        if validated is None:
            return None
        events, _ = validated
        filtered = tuple(
            event
            for event in events
            if event.start < binding.calendar_window_end
            and event.end > binding.calendar_window_start
        )
        return tuple(
            sorted(filtered, key=lambda item: (item.start, item.end))
        )

    def context_events_for_approved(
        self,
        binding: ChatPluginActionBinding,
        outcome: object,
    ) -> tuple[CalendarContextEvent, ...] | None:
        """Project only strictly validated events from the approved window."""
        if binding.calendar_window is None:
            return None
        execution = getattr(outcome, "execution", None)
        result = getattr(execution, "result", None)
        if (
            getattr(execution, "status", None) != "completed"
            or result is None
            or getattr(result, "status", None) != "succeeded"
        ):
            return None

        validated = self._validated_payload(
            getattr(result, "output", None),
            binding,
        )
        if validated is None:
            return None
        events, _ = validated
        filtered = tuple(
            event
            for event in events
            if event.start < binding.calendar_window_end
            and event.end > binding.calendar_window_start
        )
        filtered = tuple(
            sorted(filtered, key=lambda item: (item.start, item.end))
        )

        projected: list[CalendarContextEvent] = []
        for event in filtered:
            if event.all_day:
                start_value = event.start.date().isoformat()
                end_value = event.end.date().isoformat()
            else:
                start_value = event.start.isoformat()
                end_value = event.end.isoformat()
            try:
                projected.append(
                    CalendarContextEvent(
                        summary=event.summary,
                        status=event.status,
                        start=start_value,
                        end=end_value,
                        all_day=event.all_day,
                    )
                )
            except (TypeError, ValueError):
                return None
        return tuple(projected)

    def _validated_payload(
        self,
        output: object,
        binding: ChatPluginActionBinding,
    ) -> tuple[tuple[_DisplayEvent, ...], bool] | None:
        if not isinstance(output, Mapping) or set(output) != {"content"}:
            return None
        content = output.get("content")
        if not isinstance(content, str) or len(content.encode("utf-8")) > 16 * 1024:
            return None
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict) or set(payload) != {"events", "truncated"}:
            return None
        raw_events = payload.get("events")
        truncated = payload.get("truncated")
        if (
            not isinstance(raw_events, list)
            or len(raw_events) > _MAX_EVENTS
            or type(truncated) is not bool
        ):
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
        return tuple(events), truncated

    @classmethod
    def _validated_event(cls, raw: object, zone) -> _DisplayEvent | None:
        if not isinstance(raw, dict) or set(raw) != _EVENT_KEYS:
            return None

        event_id = raw.get("event_id")
        summary = raw.get("summary")
        status = raw.get("status")
        all_day = raw.get("all_day")
        start_raw = raw.get("start")
        end_raw = raw.get("end")
        if (
            not isinstance(event_id, str)
            or not event_id
            or len(event_id.encode("utf-8")) > 1024
            or not isinstance(summary, str)
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
            event_id=event_id,
            summary=summary,
            status=status,
            all_day=all_day,
            start=start,
            end=end,
        )

    @staticmethod
    def _window_label(window: CalendarChatWindow) -> str:
        labels = {
            "today": "วันนี้",
            "tomorrow": "พรุ่งนี้",
            "next_7_days": "7 วันข้างหน้า",
            "this_week": "สัปดาห์นี้",
            "next_week": "สัปดาห์หน้า",
            "this_month": "เดือนนี้",
            "today_morning": "วันนี้ช่วงเช้า",
            "today_afternoon": "วันนี้ช่วงบ่าย",
            "today_evening": "วันนี้ช่วงเย็น",
            "tomorrow_morning": "พรุ่งนี้ช่วงเช้า",
            "tomorrow_afternoon": "พรุ่งนี้ช่วงบ่าย",
            "tomorrow_evening": "พรุ่งนี้ช่วงเย็น",
            "upcoming_weekend": "สุดสัปดาห์นี้",
            "next_weekend": "สุดสัปดาห์หน้า",
            "exact_date": "วันที่ที่ระบุ",
        }
        return labels[window]

    @classmethod
    def _header(cls, window: CalendarChatWindow, count: int) -> str:
        return f"{cls._window_label(window)}มี {count} รายการครับ"

    @classmethod
    def _empty_reply(cls, window: CalendarChatWindow) -> str:
        return (
            f"{cls._window_label(window)}ไม่มีนัดใน Google Calendar "
            "ที่พบในช่วงที่ตรวจสอบครับ"
        )

    @staticmethod
    def _event_when(event: _DisplayEvent, window: CalendarChatWindow) -> str:
        multi_day_window = window in {
            "next_7_days",
            "this_week",
            "next_week",
            "this_month",
            "upcoming_weekend",
            "next_weekend",
        }
        if event.all_day:
            if multi_day_window:
                return f"{event.start:%d/%m} ทั้งวัน"
            return "ทั้งวัน"

        same_day = event.start.date() == event.end.date()
        if not multi_day_window and same_day:
            return f"{event.start:%H:%M}–{event.end:%H:%M}"
        return f"{event.start:%d/%m %H:%M}–{event.end:%d/%m %H:%M}"

    @staticmethod
    def _with_truncation_note(reply: str, truncated: bool) -> str:
        if not truncated:
            return reply
        return (
            f"{reply}\n\n"
            "Google Calendar มีรายการเพิ่มเติมในช่วงนี้ "
            "โดยคำขอนี้แสดงได้สูงสุด 10 รายการครับ"
        )

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
