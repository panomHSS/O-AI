"""D82 fail-closed projection of exact first-party connector exceptions."""

from __future__ import annotations

from app.connectors.gmail import GmailConnectorError
from app.connectors.github_public_repository import (
    GitHubPublicRepositoryConnectorError,
)
from app.connectors.google_calendar import GoogleCalendarConnectorError
from app.contracts.connector_error_semantics import (
    GITHUB_PUBLIC_REPOSITORY_ERROR_SUBJECT,
    GMAIL_READ_ERROR_SUBJECT,
    GOOGLE_CALENDAR_READ_ERROR_SUBJECT,
    safe_connector_codes_for_subject,
)


_EXPECTED_EXCEPTION_TYPE_BY_SUBJECT: dict[
    tuple[str, str, str],
    type[BaseException],
] = {
    GITHUB_PUBLIC_REPOSITORY_ERROR_SUBJECT:
        GitHubPublicRepositoryConnectorError,
    GOOGLE_CALENDAR_READ_ERROR_SUBJECT:
        GoogleCalendarConnectorError,
    GMAIL_READ_ERROR_SUBJECT:
        GmailConnectorError,
}


def project_safe_connector_error(
    *,
    plugin_id: object,
    plugin_version: object,
    capability_name: object,
    error: object,
) -> str | None:
    """Project one exact allowlisted code or fail closed to ``None``."""

    subject = (plugin_id, plugin_version, capability_name)
    expected_type = _EXPECTED_EXCEPTION_TYPE_BY_SUBJECT.get(subject)
    if expected_type is None or type(error) is not expected_type:
        return None

    safe_codes = safe_connector_codes_for_subject(
        plugin_id,
        plugin_version,
        capability_name,
    )
    code = getattr(error, "code", None)
    if type(code) is not str or code not in safe_codes:
        return None
    return code


__all__ = ["project_safe_connector_error"]
