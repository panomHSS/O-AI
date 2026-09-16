"""D65 non-secret Google OAuth connection-status preflight."""

from __future__ import annotations

from typing import Literal, TypeAlias

from app.contracts.google_oauth import GoogleOAuthCredentialSubject
from app.services.google_oauth_subjects import GOOGLE_CALENDAR_OAUTH_SUBJECT
from app.repositories.oauth_credentials import OAuthCredentialRepository


GoogleOAuthConnectionStatus: TypeAlias = Literal[
    "disconnected",
    "active",
    "reauthorization_required",
]


class GoogleOAuthConnectionStatusReader:
    """Read only non-secret credential metadata; never decrypt or refresh."""

    def __init__(
        self,
        repository: OAuthCredentialRepository,
        *,
        subject: GoogleOAuthCredentialSubject = GOOGLE_CALENDAR_OAUTH_SUBJECT,
    ) -> None:
        if not isinstance(subject, GoogleOAuthCredentialSubject):
            raise TypeError("subject must be GoogleOAuthCredentialSubject.")
        self._repository = repository
        self._subject = subject

    def read_status(self) -> GoogleOAuthConnectionStatus:
        record = self._repository.get(self._subject.profile_id)
        if record is None:
            return "disconnected"

        exact_subject = (
            record.provider_id == self._subject.provider_id
            and record.plugin_id == self._subject.plugin_id
            and record.plugin_version == self._subject.plugin_version
            and record.capability_name == self._subject.capability_name
            and record.granted_scopes == self._subject.scope
            and record.cipher_version == "aesgcm-v1"
        )
        if not exact_subject:
            return "reauthorization_required"
        if record.status == "active":
            return "active"
        return "reauthorization_required"
