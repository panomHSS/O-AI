"""D65 non-secret Google OAuth connection-status preflight."""

from __future__ import annotations

from typing import Literal, TypeAlias

from app.contracts.google_calendar import (
    GOOGLE_CALENDAR_CAPABILITY_NAME,
    GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID,
    GOOGLE_CALENDAR_CREDENTIAL_PROVIDER_ID,
    GOOGLE_CALENDAR_CREDENTIAL_SCOPE,
    GOOGLE_CALENDAR_PLUGIN_ID,
    GOOGLE_CALENDAR_PLUGIN_VERSION,
)
from app.repositories.oauth_credentials import OAuthCredentialRepository


GoogleOAuthConnectionStatus: TypeAlias = Literal[
    "disconnected",
    "active",
    "reauthorization_required",
]


class GoogleOAuthConnectionStatusReader:
    """Read only non-secret credential metadata; never decrypt or refresh."""

    def __init__(self, repository: OAuthCredentialRepository) -> None:
        self._repository = repository

    def read_status(self) -> GoogleOAuthConnectionStatus:
        record = self._repository.get(GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID)
        if record is None:
            return "disconnected"

        exact_subject = (
            record.provider_id == GOOGLE_CALENDAR_CREDENTIAL_PROVIDER_ID
            and record.plugin_id == GOOGLE_CALENDAR_PLUGIN_ID
            and record.plugin_version == GOOGLE_CALENDAR_PLUGIN_VERSION
            and record.capability_name == GOOGLE_CALENDAR_CAPABILITY_NAME
            and record.granted_scopes == GOOGLE_CALENDAR_CREDENTIAL_SCOPE
            and record.cipher_version == "aesgcm-v1"
        )
        if not exact_subject:
            return "reauthorization_required"
        if record.status == "active":
            return "active"
        return "reauthorization_required"
