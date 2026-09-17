"""D83 deterministic Calendar create-intent Chat bridge.

This module performs local parsing only.  It may construct a transient D72
GoogleCalendarCreateEventRequest candidate, but it does not create D73
approvals, authorize, resolve credentials, call connectors, invoke AI, or
execute Calendar mutations.
"""

from __future__ import annotations

import re
import threading
import unicodedata
from collections.abc import Callable
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.contracts.calendar_write_chat import (
    CalendarWriteChatParseOutcome,
    CalendarWriteChatTurnOutcome,
)
from app.contracts.google_calendar_write import (
    GoogleCalendarCreateEventRequest,
    GoogleCalendarEventDraft,
)
from app.services.conversations import ConversationService


CALENDAR_WRITE_CHAT_GUARD_TTL = timedelta(minutes=10)
CALENDAR_WRITE_CHAT_MAX_GUARDS = 128
CALENDAR_WRITE_CHAT_MAX_SUMMARY_CHARS = 256

_TH_CREATE_PREFIXES = ("สร้างนัด", "เพิ่มนัด")
_EN_CREATE_PREFIXES = ("create calendar event", "add calendar event")

_TH_UPDATE_PREFIXES = (
    "เลื่อนนัด",
    "แก้นัด",
    "แก้ไขนัด",
    "เปลี่ยนนัด",
)
_EN_UPDATE_PREFIXES = (
    "update calendar event",
    "move calendar event",
    "reschedule calendar event",
    "edit calendar event",
)
_TH_DELETE_PREFIXES = ("ลบนัด", "ยกเลิกนัด")
_EN_DELETE_PREFIXES = (
    "delete calendar event",
    "remove calendar event",
    "cancel calendar event",
)

_NON_ACTION_PREFIXES = (
    "สมมติ",
    "สมมติว่า",
    "ตัวอย่าง",
    "ถ้าฉันพูดว่า",
    "ถ้าฉันถามว่า",
    "ถ้าถามว่า",
    "อย่า",
    "อย่าสร้างนัด",
    "อย่าเพิ่มนัด",
    "ไม่ต้อง",
    "ไม่ต้องสร้างนัด",
    "ไม่ต้องเพิ่มนัด",
    "example",
    "for example",
    "if i say",
    "if i ask",
    "don't",
    "do not",
)

# Explicit semantics that D83 v1 must not silently discard into the summary.
_UNSUPPORTED_MARKERS = (
    " สถานที่ ",
    " สถานที่:",
    " เชิญ ",
    " ผู้เข้าร่วม",
    " แขก",
    " เตือน",
    " แจ้งเตือน",
    " ทุกวัน",
    " ทุกสัปดาห์",
    " ทุกเดือน",
    " ทำซ้ำ",
    " ทั้งวัน",
    " ลิงก์ประชุม",
    " แนบไฟล์",
    " location ",
    " location:",
    " description:",
    " attendee",
    " invite ",
    " guest",
    " reminder",
    " recurring",
    " recurrence",
    " recur ",
    " every day",
    " every week",
    " every month",
    " all-day",
    " all day",
    " conference",
    " meet link",
    " attachment",
    " timezone",
    " utc",
    " gmt",
)

_PLAINTEXT_APPROVALS = frozenset(
    {
        "อนุมัติ",
        "อนุมัติครับ",
        "อนุมัติครับผม",
        "อนุมัติค่ะ",
        "อนุมัติคะ",
        "approve",
        "approved",
    }
)

_TH_CREATE_RE = re.compile(
    r"^(?P<prefix>สร้างนัด|เพิ่มนัด)\s+"
    r"(?P<summary>.+?)\s+"
    r"(?P<date>วันนี้|พรุ่งนี้|(?:วันที่\s*)?\d{1,2}/\d{1,2}/\d{4})\s+"
    r"เวลา\s+"
    r"(?P<start>\d{1,2}:\d{2})\s*"
    r"(?P<separator>-|–|ถึง|to)\s*"
    r"(?P<end>\d{1,2}:\d{2})"
    r"(?:\s*(?:ครับผม|ครับ|ค่ะ|คะ))?$",
    re.IGNORECASE,
)
_EN_CREATE_RE = re.compile(
    r"^(?P<prefix>create calendar event|add calendar event)\s+"
    r"(?P<summary>.+?)\s+"
    r"(?P<date>today|tomorrow|(?:on\s+)?\d{1,2}/\d{1,2}/\d{4})\s+"
    r"(?P<start>\d{1,2}:\d{2})\s*"
    r"(?P<separator>-|–|to)\s*"
    r"(?P<end>\d{1,2}:\d{2})$",
    re.IGNORECASE,
)

_DATE_TOKEN_RE = re.compile(
    r"(?<!\w)(?:วันนี้|พรุ่งนี้|today|tomorrow|"
    r"(?:วันที่\s*)?\d{1,2}/\d{1,2}/\d{4}|"
    r"on\s+\d{1,2}/\d{1,2}/\d{4})(?!\w)",
    re.IGNORECASE,
)
_TIME_TOKEN_RE = re.compile(r"(?<!\d)\d{1,2}:\d{2}(?!\d)")
_NUMERIC_DATE_RE = re.compile(
    r"^(?:วันที่\s*|on\s+)?"
    r"(?P<day>\d{1,2})/(?P<month>\d{1,2})/(?P<year>\d{4})$",
    re.IGNORECASE,
)
_MISSING_YEAR_DATE_RE = re.compile(
    r"(?<!\d)\d{1,2}/\d{1,2}(?!/\d{4})(?!\d)"
)

_QUOTE_PAIRS = {
    '"': '"',
    "'": "'",
    "“": "”",
    "‘": "’",
}


class CalendarWriteChatGuardStoreFullError(RuntimeError):
    reason_code = "calendar_write_chat_guard_unavailable"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalized_spaces(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).strip().split())


def _normalized_key(value: str) -> str:
    return _normalized_spaces(value).casefold()


def _starts_with_any(value: str, prefixes: tuple[str, ...]) -> bool:
    lowered = value.casefold()
    return any(
        lowered == prefix.casefold()
        or lowered.startswith(prefix.casefold() + " ")
        for prefix in prefixes
    )


def _starts_with_thai_any(value: str, prefixes: tuple[str, ...]) -> bool:
    lowered = value.casefold()
    return any(lowered.startswith(prefix.casefold()) for prefix in prefixes)


def _has_non_action_prefix(value: str) -> bool:
    lowered = value.casefold()
    for marker in _NON_ACTION_PREFIXES:
        marker_key = marker.casefold()
        if any("\u0e00" <= character <= "\u0e7f" for character in marker_key):
            if lowered.startswith(marker_key):
                return True
        elif lowered == marker_key or lowered.startswith(marker_key + " "):
            return True
    return False


def _language_for_prefix(value: str) -> str | None:
    if _starts_with_any(value, _TH_CREATE_PREFIXES):
        return "th"
    if _starts_with_any(value, _EN_CREATE_PREFIXES):
        return "en"
    return None


def _strip_matching_quotes(value: str) -> str:
    candidate = value.strip()
    if len(candidate) >= 2:
        expected = _QUOTE_PAIRS.get(candidate[0])
        if expected is not None and candidate[-1] == expected:
            candidate = candidate[1:-1].strip()
    return candidate


def _summary_valid(value: str) -> bool:
    if not value or len(value) > CALENDAR_WRITE_CHAT_MAX_SUMMARY_CHARS:
        return False
    if value != value.strip():
        return False
    if "\n" in value or "\r" in value:
        return False
    if any(unicodedata.category(character) == "Cc" for character in value):
        return False

    # Thai text does not reliably behave like whitespace-delimited words for
    # regex ``\w`` boundaries.  A relative date embedded directly in a Thai
    # summary (for example ``คุยพรุ่งนี้``) is therefore semantically ambiguous
    # with the explicit date slot and must fail closed.
    summary_key = _normalized_key(value)
    if "วันนี้" in summary_key or "พรุ่งนี้" in summary_key:
        return False

    if _DATE_TOKEN_RE.search(value) is not None:
        return False
    if _TIME_TOKEN_RE.search(value) is not None:
        return False
    return True


def _contains_unsupported_semantics(value: str) -> bool:
    padded = " " + _normalized_key(value) + " "
    return any(marker.casefold() in padded for marker in _UNSUPPORTED_MARKERS)


def _parse_clock(value: str) -> time:
    match = re.fullmatch(r"(?P<hour>\d{1,2}):(?P<minute>\d{2})", value)
    if match is None:
        raise ValueError("calendar_write_chat_time_invalid")
    hour = int(match.group("hour"))
    minute = int(match.group("minute"))
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("calendar_write_chat_time_invalid")
    return time(hour=hour, minute=minute)


def _resolve_calendar_date(
    value: str,
    *,
    now_local: datetime,
) -> date:
    key = _normalized_key(value)
    if key in {"วันนี้", "today"}:
        return now_local.date()
    if key in {"พรุ่งนี้", "tomorrow"}:
        return now_local.date() + timedelta(days=1)

    match = _NUMERIC_DATE_RE.fullmatch(key)
    if match is None:
        raise ValueError("calendar_write_chat_date_invalid")
    year = int(match.group("year"))
    if year >= 2400:
        year -= 543
    return date(
        year=year,
        month=int(match.group("month")),
        day=int(match.group("day")),
    )


def _strict_local_datetime(
    day: date,
    clock_value: time,
    zone: ZoneInfo,
) -> datetime:
    naive = datetime.combine(day, clock_value)
    valid_by_utc: dict[datetime, datetime] = {}
    for fold in (0, 1):
        candidate = naive.replace(tzinfo=zone, fold=fold)
        utc_value = candidate.astimezone(timezone.utc)
        roundtrip = utc_value.astimezone(zone)
        if roundtrip.replace(tzinfo=None) == naive:
            valid_by_utc[utc_value] = candidate

    if len(valid_by_utc) != 1:
        # 0 = nonexistent local wall clock; 2 = ambiguous fold.
        raise ValueError("calendar_write_chat_time_invalid")
    return next(iter(valid_by_utc.values()))


class CalendarWriteChatGuardStore:
    """Bounded process-local anti-hallucination marker store.

    The dict key is the conversation_id and its only value is expires_at.
    No D72 request, summary, date/time, approval, credential, or execution
    material is retained here.
    """

    def __init__(
        self,
        *,
        ttl: timedelta = CALENDAR_WRITE_CHAT_GUARD_TTL,
        max_records: int = CALENDAR_WRITE_CHAT_MAX_GUARDS,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        if not isinstance(ttl, timedelta) or ttl.total_seconds() <= 0:
            raise ValueError("ttl must be a positive timedelta.")
        if (
            isinstance(max_records, bool)
            or not isinstance(max_records, int)
            or max_records < 1
        ):
            raise ValueError("max_records must be a positive integer.")
        self._ttl = ttl
        self._max_records = max_records
        self._clock = clock
        self._items: dict[UUID, datetime] = {}
        self._lock = threading.Lock()

    @property
    def record_count(self) -> int:
        now = self._clock()
        with self._lock:
            self._cleanup(now)
            return len(self._items)

    def mark(self, conversation_id: UUID) -> datetime:
        if not isinstance(conversation_id, UUID):
            raise TypeError("conversation_id must be a UUID.")
        now = self._clock()
        expires_at = now + self._ttl
        with self._lock:
            self._cleanup(now)
            if (
                conversation_id not in self._items
                and len(self._items) >= self._max_records
            ):
                raise CalendarWriteChatGuardStoreFullError(
                    "Calendar write Chat guard capacity is full."
                )
            self._items[conversation_id] = expires_at
        return expires_at

    def is_fresh(self, conversation_id: UUID | None) -> bool:
        if conversation_id is None:
            return False
        if not isinstance(conversation_id, UUID):
            return False
        now = self._clock()
        with self._lock:
            self._cleanup(now)
            expires_at = self._items.get(conversation_id)
            return expires_at is not None and now < expires_at

    def clear(self, conversation_id: UUID | None) -> None:
        if not isinstance(conversation_id, UUID):
            return
        with self._lock:
            self._items.pop(conversation_id, None)

    def _cleanup(self, now: datetime) -> None:
        expired = [
            conversation_id
            for conversation_id, expires_at in self._items.items()
            if now >= expires_at
        ]
        for conversation_id in expired:
            self._items.pop(conversation_id, None)


class CalendarWriteChatParser:
    """Strict local-only D83 parser for Calendar create candidates."""

    def __init__(
        self,
        *,
        owner_timezone: str,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        if (
            not isinstance(owner_timezone, str)
            or not owner_timezone
            or owner_timezone != owner_timezone.strip()
        ):
            raise ValueError("owner_timezone must be a non-empty trimmed string.")
        try:
            self._zone = ZoneInfo(owner_timezone)
        except ZoneInfoNotFoundError as error:
            raise ValueError("owner_timezone is invalid.") from error
        self._owner_timezone = owner_timezone
        self._clock = clock

    @property
    def owner_timezone(self) -> str:
        return self._owner_timezone

    def classify(self, message: object) -> CalendarWriteChatParseOutcome:
        if not isinstance(message, str) or not message.strip():
            return self._none()

        raw_nfkc = unicodedata.normalize("NFKC", message).strip()
        key = _normalized_key(raw_nfkc)
        if not key:
            return self._none()

        if _has_non_action_prefix(key):
            return self._none()

        if _starts_with_thai_any(key, _TH_UPDATE_PREFIXES):
            return self._unsupported("update", "th")
        if _starts_with_any(key, _EN_UPDATE_PREFIXES):
            return self._unsupported("update", "en")
        if _starts_with_thai_any(key, _TH_DELETE_PREFIXES):
            return self._unsupported("delete", "th")
        if _starts_with_any(key, _EN_DELETE_PREFIXES):
            return self._unsupported("delete", "en")

        language = _language_for_prefix(key)
        if language is None:
            return self._none()

        if "\n" in raw_nfkc or "\r" in raw_nfkc:
            return self._invalid(language)
        if _MISSING_YEAR_DATE_RE.search(key) is not None:
            return self._invalid(language)
        if _contains_unsupported_semantics(key):
            return self._invalid(language)

        prefixes = (
            _TH_CREATE_PREFIXES
            if language == "th"
            else _EN_CREATE_PREFIXES
        )
        lowered = key.casefold()
        prefix_count = sum(
            lowered.count(prefix.casefold())
            for prefix in prefixes
        )
        if prefix_count != 1:
            return self._invalid(language)

        pattern = _TH_CREATE_RE if language == "th" else _EN_CREATE_RE
        match = pattern.fullmatch(_normalized_spaces(raw_nfkc))
        if match is None:
            return self._invalid(language)

        summary = _strip_matching_quotes(match.group("summary"))
        if not _summary_valid(summary):
            return self._invalid(language)

        try:
            now = self._clock()
            if (
                not isinstance(now, datetime)
                or now.tzinfo is None
                or now.utcoffset() is None
            ):
                raise ValueError("clock must return an aware datetime.")
            now_local = now.astimezone(self._zone)
            calendar_day = _resolve_calendar_date(
                match.group("date"),
                now_local=now_local,
            )
            start_clock = _parse_clock(match.group("start"))
            end_clock = _parse_clock(match.group("end"))
            if end_clock <= start_clock:
                raise ValueError("calendar_write_chat_time_invalid")
            start_local = _strict_local_datetime(
                calendar_day,
                start_clock,
                self._zone,
            )
            end_local = _strict_local_datetime(
                calendar_day,
                end_clock,
                self._zone,
            )
            request = GoogleCalendarCreateEventRequest(
                event=GoogleCalendarEventDraft(
                    summary=summary,
                    start=start_local,
                    end=end_local,
                    description=None,
                    location=None,
                    calendar_id="primary",
                )
            )
        except (TypeError, ValueError):
            return self._invalid(language)

        return CalendarWriteChatParseOutcome(
            disposition="supported_create",
            reason_code="calendar_write_chat_create_candidate_ready",
            language=language,  # type: ignore[arg-type]
            request=request,
            summary=summary,
            start_local=start_local,
            end_local=end_local,
        )

    @staticmethod
    def _none() -> CalendarWriteChatParseOutcome:
        return CalendarWriteChatParseOutcome(
            disposition="none",
            reason_code="calendar_write_chat_not_requested",
        )

    @staticmethod
    def _invalid(language: str) -> CalendarWriteChatParseOutcome:
        return CalendarWriteChatParseOutcome(
            disposition="invalid_create",
            reason_code="calendar_write_chat_create_invalid",
            language=language,  # type: ignore[arg-type]
        )

    @staticmethod
    def _unsupported(
        operation: str,
        language: str,
    ) -> CalendarWriteChatParseOutcome:
        disposition = (
            "unsupported_update"
            if operation == "update"
            else "unsupported_delete"
        )
        reason_code = (
            "calendar_write_chat_update_unsupported"
            if operation == "update"
            else "calendar_write_chat_delete_unsupported"
        )
        return CalendarWriteChatParseOutcome(
            disposition=disposition,  # type: ignore[arg-type]
            reason_code=reason_code,
            language=language,  # type: ignore[arg-type]
        )


class CalendarWriteChatResponseComposer:
    """Render deterministic owner-facing D83 replies only."""

    def compose(
        self,
        outcome: CalendarWriteChatParseOutcome,
        *,
        owner_timezone: str,
    ) -> str:
        if outcome.disposition == "supported_create":
            assert outcome.summary is not None
            assert outcome.start_local is not None
            assert outcome.end_local is not None
            day_text = outcome.start_local.strftime("%d/%m/%Y")
            start_text = outcome.start_local.strftime("%H:%M")
            end_text = outcome.end_local.strftime("%H:%M")
            if outcome.language == "en":
                return "\n".join(
                    (
                        "I parsed this as a D83 Calendar create candidate.",
                        f"- Title: {outcome.summary}",
                        (
                            f"- Local time: {day_text} "
                            f"{start_text}–{end_text} ({owner_timezone})"
                        ),
                        (
                            "No D73 structured approval has been created, "
                            "and Calendar has not been changed."
                        ),
                    )
                )
            return "\n".join(
                (
                    "ผมตีความคำขอนี้เป็น D83 Calendar create candidate ได้ครับ",
                    f"- ชื่อ: {outcome.summary}",
                    (
                        f"- เวลาท้องถิ่น: {day_text} "
                        f"{start_text}–{end_text} ({owner_timezone})"
                    ),
                    (
                        "ยังไม่ได้สร้าง D73 structured approval "
                        "และยังไม่มีการเปลี่ยนแปลงใน Calendar ครับ"
                    ),
                )
            )

        if outcome.disposition == "unsupported_update":
            if outcome.language == "en":
                return (
                    "Calendar update through natural Chat is not supported "
                    "in D83 because an exact event_id is required. "
                    "No Calendar change was made."
                )
            return (
                "D83 ยังไม่รองรับการแก้/เลื่อนนัดผ่านภาษาธรรมชาติครับ "
                "เพราะต้องใช้อ้างอิง event_id ที่แน่นอน "
                "และยังไม่มีการเปลี่ยน Calendar"
            )

        if outcome.disposition == "unsupported_delete":
            if outcome.language == "en":
                return (
                    "Calendar delete through natural Chat is not supported "
                    "in D83 because an exact event_id is required. "
                    "No Calendar change was made."
                )
            return (
                "D83 ยังไม่รองรับการลบนัดผ่านภาษาธรรมชาติครับ "
                "เพราะต้องใช้อ้างอิง event_id ที่แน่นอน "
                "และยังไม่มีการเปลี่ยน Calendar"
            )

        if outcome.language == "en":
            return (
                "I could not build a safe D83 Calendar create candidate. "
                "Please provide one title, an explicit date, and explicit "
                "same-day start and end times. No Calendar change was made."
            )
        return (
            "ยังสร้าง D83 Calendar create candidate อย่างปลอดภัยไม่ได้ครับ "
            "กรุณาระบุชื่อนัด วันที่ และเวลาเริ่ม-สิ้นสุดในวันเดียวกันให้ครบ "
            "และยังไม่มีการเปลี่ยน Calendar"
        )

    @staticmethod
    def structured_approval_required(language: str) -> str:
        if language == "en":
            return (
                "Plain Chat text cannot approve or execute this Calendar "
                "write. D83 has not created a D73 structured approval, "
                "and Calendar has not been changed."
            )
        return (
            "ข้อความอนุมัติใน Chat ไม่มีสิทธิ์อนุมัติหรือดำเนินการ "
            "Calendar write ครับ D83 ยังไม่ได้สร้าง D73 structured approval "
            "และยังไม่มีการเปลี่ยน Calendar"
        )


class CalendarWriteChatService:
    """D83 local deterministic service; no approval or execution authority."""

    def __init__(
        self,
        *,
        parser: CalendarWriteChatParser,
        guard_store: CalendarWriteChatGuardStore,
        composer: CalendarWriteChatResponseComposer | None = None,
        conversation_service: ConversationService | None = None,
    ) -> None:
        if not isinstance(parser, CalendarWriteChatParser):
            raise TypeError("parser must be CalendarWriteChatParser.")
        if not isinstance(guard_store, CalendarWriteChatGuardStore):
            raise TypeError("guard_store must be CalendarWriteChatGuardStore.")
        self._parser = parser
        self._guard_store = guard_store
        self._composer = composer or CalendarWriteChatResponseComposer()
        self._conversation_service = conversation_service

    def classify(self, message: object) -> CalendarWriteChatParseOutcome:
        return self._parser.classify(message)

    def is_request(self, message: object) -> bool:
        return self.classify(message).disposition != "none"

    def process_candidate(
        self,
        *,
        message: str,
        conversation_id: UUID,
    ) -> CalendarWriteChatTurnOutcome:
        if not isinstance(conversation_id, UUID):
            raise TypeError("conversation_id must be a UUID.")
        outcome = self.classify(message)
        if outcome.disposition == "none":
            raise ValueError("Message is not a D83 Calendar write request.")

        request = outcome.request
        if outcome.disposition == "supported_create":
            try:
                self._guard_store.mark(conversation_id)
            except CalendarWriteChatGuardStoreFullError:
                return CalendarWriteChatTurnOutcome(
                    conversation_id=conversation_id,
                    disposition="invalid_create",
                    reason_code="calendar_write_chat_guard_unavailable",
                    reply=(
                        "ไม่สามารถเปิด D83 approval guard อย่างปลอดภัยได้ครับ "
                        "จึงไม่รับ Calendar create candidate นี้ "
                        "และยังไม่มีการเปลี่ยน Calendar"
                        if outcome.language != "en"
                        else (
                            "The D83 approval guard is unavailable, so this "
                            "Calendar create candidate was not accepted. "
                            "Calendar has not been changed."
                        )
                    ),
                )

        return CalendarWriteChatTurnOutcome(
            conversation_id=conversation_id,
            disposition=outcome.disposition,
            reason_code=outcome.reason_code,
            reply=self._composer.compose(
                outcome,
                owner_timezone=self._parser.owner_timezone,
            ),
            request=request,
        )

    def pending_plaintext_approval_disposition(
        self,
        *,
        conversation_id: UUID | None,
        message: object,
    ) -> str:
        if (
            not isinstance(message, str)
            or not self._guard_store.is_fresh(conversation_id)
        ):
            return "none"

        key = _normalized_key(message)
        if key in _PLAINTEXT_APPROVALS:
            return "block"

        self._guard_store.clear(conversation_id)
        return "clear"

    def process_pending_plaintext_approval(
        self,
        *,
        conversation_id: UUID,
        message: str,
    ) -> CalendarWriteChatTurnOutcome:
        disposition = self.pending_plaintext_approval_disposition(
            conversation_id=conversation_id,
            message=message,
        )
        if disposition != "block":
            raise ValueError(
                "No pending D83 plaintext approval guard matches this message."
            )
        language = "en" if _normalized_key(message) in {"approve", "approved"} else "th"
        return CalendarWriteChatTurnOutcome(
            conversation_id=conversation_id,
            disposition="invalid_create",
            reason_code="calendar_write_chat_structured_approval_required",
            reply=self._composer.structured_approval_required(language),
        )

    def clear_pending_guard(self, conversation_id: UUID | None) -> None:
        self._guard_store.clear(conversation_id)

    def process_chat_turn(
        self,
        *,
        message: str,
        conversation_id: UUID | None,
        project_id: UUID | None,
    ) -> CalendarWriteChatTurnOutcome:
        """Persist one deterministic D83 mutation-intent turn.

        The transient D72 request candidate is never passed to ConversationService
        and is never serialized into ChatResponse.
        """

        if self._conversation_service is None:
            raise RuntimeError("calendar_write_chat_conversation_service_required")

        parsed = self.classify(message)
        if parsed.disposition == "none":
            raise ValueError("Message is not a D83 Calendar write request.")

        conversation, _ = self._conversation_service.begin_turn(
            message,
            conversation_id,
            project_id,
        )
        resolved_conversation_id = UUID(str(conversation.id))
        turn = self.process_candidate(
            message=message,
            conversation_id=resolved_conversation_id,
        )
        self._conversation_service.complete_turn(
            str(resolved_conversation_id),
            turn.reply,
        )
        return turn

    def process_pending_plaintext_approval_turn(
        self,
        *,
        message: str,
        conversation_id: UUID,
        project_id: UUID | None,
    ) -> CalendarWriteChatTurnOutcome:
        """Persist one deterministic non-authoritative plaintext-approval guard turn."""

        if self._conversation_service is None:
            raise RuntimeError("calendar_write_chat_conversation_service_required")
        turn = self.process_pending_plaintext_approval(
            conversation_id=conversation_id,
            message=message,
        )
        conversation, _ = self._conversation_service.begin_turn(
            message,
            conversation_id,
            project_id,
        )
        resolved_conversation_id = UUID(str(conversation.id))
        if resolved_conversation_id != conversation_id:
            raise RuntimeError("calendar_write_chat_conversation_mismatch")
        self._conversation_service.complete_turn(
            str(conversation_id),
            turn.reply,
        )
        return turn


__all__ = [
    "CALENDAR_WRITE_CHAT_GUARD_TTL",
    "CALENDAR_WRITE_CHAT_MAX_GUARDS",
    "CALENDAR_WRITE_CHAT_MAX_SUMMARY_CHARS",
    "CalendarWriteChatGuardStore",
    "CalendarWriteChatGuardStoreFullError",
    "CalendarWriteChatParser",
    "CalendarWriteChatResponseComposer",
    "CalendarWriteChatService",
]
