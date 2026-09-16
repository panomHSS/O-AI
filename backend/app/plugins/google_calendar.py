"""D63/D67 authenticated read-only Google Calendar Plugin."""

from __future__ import annotations

import json

from app.connectors.google_calendar import (
    GOOGLE_CALENDAR_ERROR_CREDENTIAL_UNAVAILABLE,
    GOOGLE_CALENDAR_ERROR_INVALID_REQUEST,
    GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE,
    GOOGLE_CALENDAR_ERROR_NETWORK,
    GoogleCalendarClient,
    GoogleCalendarConnectorError,
    GoogleCalendarEvent,
    GoogleCalendarReadResult,
    GoogleCalendarReader,
)
from app.contracts.google_calendar import (
    GOOGLE_CALENDAR_ADAPTER_ID,
    GOOGLE_CALENDAR_CAPABILITY_ID,
    GOOGLE_CALENDAR_CAPABILITY_NAME,
    GOOGLE_CALENDAR_CREDENTIAL_AUTH_SCHEME,
    GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID,
    GOOGLE_CALENDAR_CREDENTIAL_PROVIDER_ID,
    GOOGLE_CALENDAR_CREDENTIAL_SCOPE,
    GOOGLE_CALENDAR_OPERATION,
    GOOGLE_CALENDAR_PLUGIN_ID,
    GOOGLE_CALENDAR_PLUGIN_VERSION,
    GoogleCalendarExecutionWindow,
)
from app.plugins.base import Plugin
from app.plugins.context import PluginExecutionContext
from app.plugins.request import PluginRequest
from app.plugins.response import PluginResult
from app.services.credential_access_broker import CredentialAccessBroker, CredentialAccessError

_GOOGLE_CALENDAR_MAX_PLUGIN_OUTPUT_BYTES = 16 * 1024
_GOOGLE_CALENDAR_MAX_PLUGIN_INPUT_BYTES = 1024


class GoogleCalendarPlugin(Plugin):
    """Read one approved bounded Calendar window using the D62 broker."""

    def __init__(
        self,
        *,
        credential_broker: CredentialAccessBroker,
        client: GoogleCalendarReader | None = None,
    ) -> None:
        if not isinstance(credential_broker, CredentialAccessBroker):
            raise TypeError("credential_broker must be CredentialAccessBroker.")
        self._credential_broker = credential_broker
        self._client = GoogleCalendarClient() if client is None else client

    @property
    def id(self) -> str:
        return GOOGLE_CALENDAR_PLUGIN_ID

    @property
    def name(self) -> str:
        return "Google Calendar Upcoming Events"

    @property
    def version(self) -> str:
        return GOOGLE_CALENDAR_PLUGIN_VERSION

    def execute(
        self,
        context: PluginExecutionContext,
        request: PluginRequest,
    ) -> PluginResult:
        window = self._validated_request_window(request)

        try:
            credential = self._credential_broker.resolve(
                GOOGLE_CALENDAR_PLUGIN_ID,
                GOOGLE_CALENDAR_PLUGIN_VERSION,
                GOOGLE_CALENDAR_CAPABILITY_NAME,
            )
        except CredentialAccessError:
            raise GoogleCalendarConnectorError(
                GOOGLE_CALENDAR_ERROR_CREDENTIAL_UNAVAILABLE
            ) from None
        except Exception:
            raise GoogleCalendarConnectorError(
                GOOGLE_CALENDAR_ERROR_CREDENTIAL_UNAVAILABLE
            ) from None

        if (
            credential.profile_id != GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID
            or credential.plugin_id != GOOGLE_CALENDAR_PLUGIN_ID
            or credential.plugin_version != GOOGLE_CALENDAR_PLUGIN_VERSION
            or credential.capability_name != GOOGLE_CALENDAR_CAPABILITY_NAME
            or credential.provider_id != GOOGLE_CALENDAR_CREDENTIAL_PROVIDER_ID
            or credential.auth_scheme != GOOGLE_CALENDAR_CREDENTIAL_AUTH_SCHEME
            or credential.required_scopes != (GOOGLE_CALENDAR_CREDENTIAL_SCOPE,)
        ):
            raise GoogleCalendarConnectorError(
                GOOGLE_CALENDAR_ERROR_CREDENTIAL_UNAVAILABLE
            )

        try:
            read_result = self._client.list_upcoming_events(
                credential.secret,
                time_min=window.start,
                time_max=window.end,
            )
        except GoogleCalendarConnectorError:
            raise
        except Exception:
            raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_NETWORK) from None

        if (
            not isinstance(read_result, GoogleCalendarReadResult)
            or any(
                not isinstance(event, GoogleCalendarEvent)
                for event in read_result.events
            )
        ):
            raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE)

        content = json.dumps(
            {
                "events": [event.as_dict() for event in read_result.events],
                "truncated": read_result.truncated,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        if len(content.encode("utf-8")) > _GOOGLE_CALENDAR_MAX_PLUGIN_OUTPUT_BYTES:
            raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE)
        return PluginResult(content=content)

    @staticmethod
    def _validated_request_window(
        request: object,
    ) -> GoogleCalendarExecutionWindow:
        if not isinstance(request, PluginRequest) or not isinstance(request.content, str):
            raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_INVALID_REQUEST)
        if len(request.content.encode("utf-8")) > _GOOGLE_CALENDAR_MAX_PLUGIN_INPUT_BYTES:
            raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_INVALID_REQUEST)
        try:
            payload = json.loads(request.content)
            return GoogleCalendarExecutionWindow.from_parameters(payload)
        except (json.JSONDecodeError, ValueError, TypeError):
            raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_INVALID_REQUEST) from None


__all__ = [
    "GOOGLE_CALENDAR_ADAPTER_ID",
    "GOOGLE_CALENDAR_CAPABILITY_ID",
    "GOOGLE_CALENDAR_CAPABILITY_NAME",
    "GOOGLE_CALENDAR_OPERATION",
    "GOOGLE_CALENDAR_PLUGIN_ID",
    "GOOGLE_CALENDAR_PLUGIN_VERSION",
    "GoogleCalendarPlugin",
]
