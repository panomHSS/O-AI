"""Pure D79 due-slot calculation for approved local reminders."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.models.automation_definition import AutomationDefinitionRecord


UTC = timezone.utc
_DAILY_SEARCH_DAYS = 370


class AutomationScheduleError(ValueError):
    """Stored automation schedule cannot be evaluated safely."""


def _aware_utc(value: datetime) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise AutomationScheduleError("automation_schedule_datetime_invalid")
    return value.astimezone(UTC)


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        raise AutomationScheduleError(
            "automation_schedule_timezone_invalid"
        ) from None


def _daily_parts(local_time: str) -> tuple[int, int]:
    try:
        hour_text, minute_text = local_time.split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
    except (AttributeError, TypeError, ValueError):
        raise AutomationScheduleError(
            "automation_schedule_daily_time_invalid"
        ) from None
    if (
        f"{hour:02d}:{minute:02d}" != local_time
        or not 0 <= hour <= 23
        or not 0 <= minute <= 59
    ):
        raise AutomationScheduleError(
            "automation_schedule_daily_time_invalid"
        )
    return hour, minute


def _valid_local_candidate(
    day: date,
    hour: int,
    minute: int,
    zone: ZoneInfo,
) -> datetime | None:
    naive = datetime.combine(day, time(hour=hour, minute=minute))
    candidate = naive.replace(tzinfo=zone, fold=0)
    round_trip = candidate.astimezone(UTC).astimezone(zone)
    if round_trip.replace(tzinfo=None) != naive:
        return None
    return candidate.astimezone(UTC)


def next_daily_due_after(
    *,
    local_time: str,
    timezone_name: str,
    after_utc: datetime,
) -> datetime:
    """Return one deterministic future daily occurrence.

    Non-existent DST wall-clock minutes are skipped. Ambiguous wall-clock
    minutes use fold=0 only, so one local date can never produce two runs.
    """
    after = _aware_utc(after_utc)
    zone = _zone(timezone_name)
    hour, minute = _daily_parts(local_time)
    local_day = after.astimezone(zone).date()

    for offset in range(_DAILY_SEARCH_DAYS):
        candidate = _valid_local_candidate(
            local_day + timedelta(days=offset),
            hour,
            minute,
            zone,
        )
        if candidate is not None and candidate > after:
            return candidate

    raise AutomationScheduleError("automation_schedule_no_future_daily_slot")


def initial_due_at_utc(
    record: AutomationDefinitionRecord,
    *,
    approved_at: datetime,
) -> datetime:
    """Resolve the first exact due slot after owner approval."""
    approved = _aware_utc(approved_at)
    if record.schedule_kind == "once":
        if record.run_at_iso is None:
            raise AutomationScheduleError(
                "automation_schedule_once_missing"
            )
        try:
            parsed = datetime.fromisoformat(record.run_at_iso)
        except (TypeError, ValueError):
            raise AutomationScheduleError(
                "automation_schedule_once_invalid"
            ) from None
        return _aware_utc(parsed)

    if record.schedule_kind == "daily":
        if record.daily_local_time is None:
            raise AutomationScheduleError(
                "automation_schedule_daily_missing"
            )
        return next_daily_due_after(
            local_time=record.daily_local_time,
            timezone_name=record.timezone,
            after_utc=approved,
        )

    raise AutomationScheduleError("automation_schedule_kind_invalid")


def next_due_after(
    record: AutomationDefinitionRecord,
    *,
    after_utc: datetime,
) -> datetime | None:
    """Resolve the next slot after a processed occurrence."""
    if record.schedule_kind == "once":
        return None
    if record.schedule_kind != "daily":
        raise AutomationScheduleError("automation_schedule_kind_invalid")
    if record.daily_local_time is None:
        raise AutomationScheduleError(
            "automation_schedule_daily_missing"
        )
    return next_daily_due_after(
        local_time=record.daily_local_time,
        timezone_name=record.timezone,
        after_utc=after_utc,
    )


__all__ = [
    "AutomationScheduleError",
    "initial_due_at_utc",
    "next_daily_due_after",
    "next_due_after",
]
