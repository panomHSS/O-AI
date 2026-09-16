"""D79 durable automation authority contracts v1."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypeAlias
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


AUTOMATION_CONTRACT_VERSION = "1"
AUTOMATION_KIND_LOCAL_REMINDER = "local_reminder"
AUTOMATION_MESSAGE_MAX_CHARS = 1000
AUTOMATION_DAILY_MAX_RUNS = 31
AUTOMATION_ONCE_MAX_RUNS = 1
AUTOMATION_TIMEZONE_MAX_CHARS = 128

AutomationKind: TypeAlias = Literal["local_reminder"]
AutomationScheduleKind: TypeAlias = Literal["once", "daily"]
AutomationDefinitionStatus: TypeAlias = Literal[
    "pending",
    "approved",
    "denied",
    "cancelled",
    "completed",
]
AutomationRunStatus: TypeAlias = Literal[
    "claimed",
    "delivered",
    "missed",
    "indeterminate",
]

_DAILY_LOCAL_TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def _contains_disallowed_control(value: str, *, multiline: bool) -> bool:
    for character in value:
        if multiline and character in "\r\n\t":
            continue
        if unicodedata.category(character) == "Cc":
            return True
    return False


def _validated_message(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > AUTOMATION_MESSAGE_MAX_CHARS
        or _contains_disallowed_control(value, multiline=True)
    ):
        raise ValueError("automation_message_invalid")
    return value


def _validated_timezone(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > AUTOMATION_TIMEZONE_MAX_CHARS
        or _contains_disallowed_control(value, multiline=False)
    ):
        raise ValueError("automation_timezone_invalid")
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError("automation_timezone_invalid") from None
    return value


@dataclass(frozen=True, slots=True)
class OnceAutomationSchedule:
    """One absolute timezone-aware run time."""

    run_at: datetime
    kind: AutomationScheduleKind = "once"

    def __post_init__(self) -> None:
        if self.kind != "once":
            raise ValueError("automation_schedule_kind_invalid")
        if (
            not isinstance(self.run_at, datetime)
            or self.run_at.tzinfo is None
            or self.run_at.utcoffset() is None
        ):
            raise ValueError("automation_once_run_at_invalid")


@dataclass(frozen=True, slots=True)
class DailyAutomationSchedule:
    """One owner-timezone daily minute-resolution wall-clock time."""

    local_time: str
    kind: AutomationScheduleKind = "daily"

    def __post_init__(self) -> None:
        if self.kind != "daily":
            raise ValueError("automation_schedule_kind_invalid")
        if (
            not isinstance(self.local_time, str)
            or self.local_time != self.local_time.strip()
            or _DAILY_LOCAL_TIME_RE.fullmatch(self.local_time) is None
        ):
            raise ValueError("automation_daily_local_time_invalid")


AutomationSchedule: TypeAlias = OnceAutomationSchedule | DailyAutomationSchedule


@dataclass(frozen=True, slots=True)
class LocalReminderAutomationDefinition:
    """Exact owner-reviewable D79 automation definition."""

    message: str
    schedule: AutomationSchedule
    timezone: str
    max_runs: int
    kind: AutomationKind = AUTOMATION_KIND_LOCAL_REMINDER
    contract_version: str = AUTOMATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_version != AUTOMATION_CONTRACT_VERSION:
            raise ValueError("automation_contract_version_invalid")
        if self.kind != AUTOMATION_KIND_LOCAL_REMINDER:
            raise ValueError("automation_kind_invalid")

        _validated_message(self.message)
        _validated_timezone(self.timezone)

        if isinstance(self.max_runs, bool) or not isinstance(self.max_runs, int):
            raise ValueError("automation_max_runs_invalid")

        if isinstance(self.schedule, OnceAutomationSchedule):
            if self.max_runs != AUTOMATION_ONCE_MAX_RUNS:
                raise ValueError("automation_once_max_runs_invalid")
        elif isinstance(self.schedule, DailyAutomationSchedule):
            if not 1 <= self.max_runs <= AUTOMATION_DAILY_MAX_RUNS:
                raise ValueError("automation_daily_max_runs_invalid")
        else:
            raise TypeError("schedule must be an automation schedule.")


__all__ = [
    "AUTOMATION_CONTRACT_VERSION",
    "AUTOMATION_DAILY_MAX_RUNS",
    "AUTOMATION_KIND_LOCAL_REMINDER",
    "AUTOMATION_MESSAGE_MAX_CHARS",
    "AUTOMATION_ONCE_MAX_RUNS",
    "AutomationDefinitionStatus",
    "AutomationKind",
    "AutomationRunStatus",
    "AutomationSchedule",
    "AutomationScheduleKind",
    "DailyAutomationSchedule",
    "LocalReminderAutomationDefinition",
    "OnceAutomationSchedule",
]
