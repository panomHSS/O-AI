"""D82 exact first-party connector safe-error subjects and allowlists."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from app.contracts.gmail import (
    GMAIL_PLUGIN_ID,
    GMAIL_PLUGIN_VERSION,
    GMAIL_READ_CAPABILITY_NAME,
)
from app.contracts.google_calendar import (
    GOOGLE_CALENDAR_CAPABILITY_NAME,
    GOOGLE_CALENDAR_PLUGIN_ID,
    GOOGLE_CALENDAR_PLUGIN_VERSION,
)


ConnectorErrorSubjectKey = tuple[str, str, str]

GITHUB_PUBLIC_REPOSITORY_ERROR_SUBJECT: ConnectorErrorSubjectKey = (
    "github_public_repo",
    "1.0.0",
    "repository_metadata",
)
GOOGLE_CALENDAR_READ_ERROR_SUBJECT: ConnectorErrorSubjectKey = (
    GOOGLE_CALENDAR_PLUGIN_ID,
    GOOGLE_CALENDAR_PLUGIN_VERSION,
    GOOGLE_CALENDAR_CAPABILITY_NAME,
)
GMAIL_READ_ERROR_SUBJECT: ConnectorErrorSubjectKey = (
    GMAIL_PLUGIN_ID,
    GMAIL_PLUGIN_VERSION,
    GMAIL_READ_CAPABILITY_NAME,
)

GITHUB_PUBLIC_REPOSITORY_SAFE_ERROR_CODES = frozenset(
    {
        "invalid_repository_reference",
        "connector_timeout",
        "connector_network_error",
        "connector_http_error",
        "connector_response_too_large",
        "connector_invalid_json",
        "connector_invalid_response",
    }
)
GOOGLE_CALENDAR_READ_SAFE_ERROR_CODES = frozenset(
    {
        "calendar_invalid_credential",
        "calendar_invalid_clock",
        "calendar_connector_timeout",
        "calendar_connector_network_error",
        "calendar_connector_http_error",
        "calendar_authentication_failed",
        "calendar_response_too_large",
        "calendar_invalid_json",
        "calendar_invalid_response",
        "calendar_credential_unavailable",
        "calendar_invalid_request",
    }
)
GMAIL_READ_SAFE_ERROR_CODES = frozenset(
    {
        "gmail_auth_failed",
        "gmail_unavailable",
        "gmail_rate_limited",
        "gmail_response_invalid",
        "gmail_response_too_large",
        "gmail_message_not_found",
        "gmail_query_invalid",
    }
)

_D82_SAFE_CODES_BY_SUBJECT: dict[
    ConnectorErrorSubjectKey,
    frozenset[str],
] = {
    GITHUB_PUBLIC_REPOSITORY_ERROR_SUBJECT:
        GITHUB_PUBLIC_REPOSITORY_SAFE_ERROR_CODES,
    GOOGLE_CALENDAR_READ_ERROR_SUBJECT:
        GOOGLE_CALENDAR_READ_SAFE_ERROR_CODES,
    GMAIL_READ_ERROR_SUBJECT:
        GMAIL_READ_SAFE_ERROR_CODES,
}
D82_SAFE_CONNECTOR_ERROR_CODES_BY_SUBJECT: Mapping[
    ConnectorErrorSubjectKey,
    frozenset[str],
] = MappingProxyType(_D82_SAFE_CODES_BY_SUBJECT)


def safe_connector_codes_for_subject(
    plugin_id: object,
    plugin_version: object,
    capability_name: object,
) -> frozenset[str]:
    """Return only the exact D82 allowlist for one known first-party subject."""

    if (
        not isinstance(plugin_id, str)
        or not isinstance(plugin_version, str)
        or not isinstance(capability_name, str)
    ):
        return frozenset()
    return D82_SAFE_CONNECTOR_ERROR_CODES_BY_SUBJECT.get(
        (plugin_id, plugin_version, capability_name),
        frozenset(),
    )


__all__ = [
    "ConnectorErrorSubjectKey",
    "D82_SAFE_CONNECTOR_ERROR_CODES_BY_SUBJECT",
    "GITHUB_PUBLIC_REPOSITORY_ERROR_SUBJECT",
    "GITHUB_PUBLIC_REPOSITORY_SAFE_ERROR_CODES",
    "GMAIL_READ_ERROR_SUBJECT",
    "GMAIL_READ_SAFE_ERROR_CODES",
    "GOOGLE_CALENDAR_READ_ERROR_SUBJECT",
    "GOOGLE_CALENDAR_READ_SAFE_ERROR_CODES",
    "safe_connector_codes_for_subject",
]
