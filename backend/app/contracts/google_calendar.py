"""D63/D67/D74 exact Google Calendar credential and capability identity."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

GOOGLE_CALENDAR_PLUGIN_ID = "google_calendar"
GOOGLE_CALENDAR_PLUGIN_VERSION = "1.0.0"
GOOGLE_CALENDAR_CAPABILITY_NAME = "upcoming_events"
GOOGLE_CALENDAR_CREATE_CAPABILITY_NAME = "create_event"
GOOGLE_CALENDAR_CREATE_CREDENTIAL_PROFILE_ID = "google_calendar.events.create"
GOOGLE_CALENDAR_ADAPTER_ID = "module.plugin.google_calendar"
GOOGLE_CALENDAR_OPERATION = "list_upcoming_events"
GOOGLE_CALENDAR_CAPABILITY_ID = "exec.plugin.google_calendar.upcoming_events"

GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID = "google_calendar.events.readonly"
GOOGLE_CALENDAR_CREDENTIAL_PROVIDER_ID = "google"
GOOGLE_CALENDAR_CREDENTIAL_AUTH_SCHEME = "oauth2_bearer"
GOOGLE_CALENDAR_CREDENTIAL_SCOPE = (
    "https://www.googleapis.com/auth/calendar.events.owned"
)
GOOGLE_CALENDAR_CREDENTIAL_SECRET_REF = "google_calendar.access_token"

# D63 compatibility constant. D67 execution no longer authorizes this sentinel;
# approved actions carry an exact absolute time window instead.
GOOGLE_CALENDAR_REQUEST_SENTINEL = "upcoming"
GOOGLE_CALENDAR_TIME_MIN_PARAMETER = "time_min"
GOOGLE_CALENDAR_TIME_MAX_PARAMETER = "time_max"
GOOGLE_CALENDAR_EXECUTION_PARAMETER_KEYS = frozenset(
    {GOOGLE_CALENDAR_TIME_MIN_PARAMETER, GOOGLE_CALENDAR_TIME_MAX_PARAMETER}
)
GOOGLE_CALENDAR_MAX_WINDOW_DAYS = 32
_GOOGLE_CALENDAR_MAX_BOUNDARY_BYTES = 128


@dataclass(frozen=True, slots=True)
class GoogleCalendarExecutionWindow:
    """One immutable approved Calendar window with preserved wire values."""

    time_min: str
    time_max: str
    start: datetime
    end: datetime

    @classmethod
    def from_parameters(
        cls,
        parameters: object,
    ) -> "GoogleCalendarExecutionWindow":
        if (
            not isinstance(parameters, Mapping)
            or set(parameters) != GOOGLE_CALENDAR_EXECUTION_PARAMETER_KEYS
        ):
            raise ValueError("calendar_execution_window_invalid")

        time_min = parameters.get(GOOGLE_CALENDAR_TIME_MIN_PARAMETER)
        time_max = parameters.get(GOOGLE_CALENDAR_TIME_MAX_PARAMETER)
        for value in (time_min, time_max):
            if (
                not isinstance(value, str)
                or not value
                or value != value.strip()
                or len(value.encode("utf-8")) > _GOOGLE_CALENDAR_MAX_BOUNDARY_BYTES
            ):
                raise ValueError("calendar_execution_window_invalid")

        assert isinstance(time_min, str)
        assert isinstance(time_max, str)
        try:
            start = datetime.fromisoformat(time_min.replace("Z", "+00:00"))
            end = datetime.fromisoformat(time_max.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("calendar_execution_window_invalid") from None

        if (
            start.tzinfo is None
            or start.utcoffset() is None
            or end.tzinfo is None
            or end.utcoffset() is None
        ):
            raise ValueError("calendar_execution_window_invalid")

        elapsed = end.astimezone(timezone.utc) - start.astimezone(timezone.utc)
        if elapsed <= timedelta(0) or elapsed > timedelta(
            days=GOOGLE_CALENDAR_MAX_WINDOW_DAYS
        ):
            raise ValueError("calendar_execution_window_invalid")

        return cls(
            time_min=time_min,
            time_max=time_max,
            start=start,
            end=end,
        )
