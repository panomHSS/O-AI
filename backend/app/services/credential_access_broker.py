"""D62 fail-closed credential access broker."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import SecretStr

from app.contracts.credential import (
    CredentialProfile,
    CredentialSecretSource,
    ResolvedCredential,
)
from app.services.credential_profile_catalog import (
    CredentialProfileCatalog,
    CredentialProfileCatalogError,
)

CREDENTIAL_ACCESS_ERROR_INVALID_PLUGIN_ID = (
    "invalid_credential_access_plugin_id"
)
CREDENTIAL_ACCESS_ERROR_INVALID_PLUGIN_VERSION = (
    "invalid_credential_access_plugin_version"
)
CREDENTIAL_ACCESS_ERROR_INVALID_CAPABILITY_NAME = (
    "invalid_credential_access_capability_name"
)
CREDENTIAL_ACCESS_ERROR_PROFILE_NOT_FOUND = (
    "credential_access_profile_not_found"
)
CREDENTIAL_ACCESS_ERROR_SECRET_NOT_FOUND = (
    "credential_access_secret_not_found"
)
CREDENTIAL_ACCESS_ERROR_SECRET_RESOLUTION_FAILED = (
    "credential_access_secret_resolution_failed"
)
CREDENTIAL_ACCESS_ERROR_INVALID_SECRET = (
    "credential_access_invalid_secret"
)


class CredentialAccessError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _subject_text(value: object, *, code: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise CredentialAccessError(code)
    return value


class EmptyCredentialSecretSource:
    """Default-deny source used until an approved credential source exists."""

    def resolve(self, secret_ref: str) -> SecretStr | None:
        return None


class StaticCredentialSecretSource:
    """Exact in-process source for tests and future trusted composition only."""

    __slots__ = ("_secrets",)

    def __init__(
        self,
        secrets: Mapping[str, SecretStr] | None = None,
    ) -> None:
        validated: dict[str, SecretStr] = {}
        for secret_ref, secret in (secrets or {}).items():
            if (
                not isinstance(secret_ref, str)
                or not secret_ref
                or secret_ref != secret_ref.strip()
            ):
                raise ValueError("invalid_static_credential_secret_ref")
            if not isinstance(secret, SecretStr):
                raise TypeError(
                    "D62 static source accepts SecretStr values only."
                )
            validated[secret_ref] = secret
        self._secrets = validated

    def resolve(self, secret_ref: str) -> SecretStr | None:
        return self._secrets.get(secret_ref)


class CredentialAccessBroker:
    """Resolve a secret only through an exact O-AI-controlled Plugin subject."""

    def __init__(
        self,
        *,
        profile_catalog: CredentialProfileCatalog,
        secret_source: CredentialSecretSource,
    ) -> None:
        self._profile_catalog = profile_catalog
        self._secret_source = secret_source

    def resolve(
        self,
        plugin_id: str,
        plugin_version: str,
        capability_name: str,
    ) -> ResolvedCredential:
        plugin_id = _subject_text(
            plugin_id,
            code=CREDENTIAL_ACCESS_ERROR_INVALID_PLUGIN_ID,
        )
        plugin_version = _subject_text(
            plugin_version,
            code=CREDENTIAL_ACCESS_ERROR_INVALID_PLUGIN_VERSION,
        )
        capability_name = _subject_text(
            capability_name,
            code=CREDENTIAL_ACCESS_ERROR_INVALID_CAPABILITY_NAME,
        )
        profile = self._resolve_profile(
            plugin_id,
            plugin_version,
            capability_name,
        )
        secret = self._resolve_secret(profile)
        return ResolvedCredential(
            profile_id=profile.profile_id,
            plugin_id=profile.plugin_id,
            plugin_version=profile.plugin_version,
            capability_name=profile.capability_name,
            provider_id=profile.provider_id,
            auth_scheme=profile.auth_scheme,
            required_scopes=profile.required_scopes,
            secret=secret,
        )

    def _resolve_profile(
        self,
        plugin_id: str,
        plugin_version: str,
        capability_name: str,
    ) -> CredentialProfile:
        try:
            return self._profile_catalog.resolve(
                plugin_id,
                plugin_version,
                capability_name,
            )
        except CredentialProfileCatalogError:
            raise CredentialAccessError(
                CREDENTIAL_ACCESS_ERROR_PROFILE_NOT_FOUND
            ) from None
        except Exception:
            raise CredentialAccessError(
                CREDENTIAL_ACCESS_ERROR_PROFILE_NOT_FOUND
            ) from None

    def _resolve_secret(self, profile: CredentialProfile) -> SecretStr:
        try:
            secret = self._secret_source.resolve(profile.secret_ref)
        except Exception:
            raise CredentialAccessError(
                CREDENTIAL_ACCESS_ERROR_SECRET_RESOLUTION_FAILED
            ) from None

        if secret is None:
            raise CredentialAccessError(
                CREDENTIAL_ACCESS_ERROR_SECRET_NOT_FOUND
            )
        if not isinstance(secret, SecretStr):
            raise CredentialAccessError(
                CREDENTIAL_ACCESS_ERROR_INVALID_SECRET
            )
        if not secret.get_secret_value():
            raise CredentialAccessError(
                CREDENTIAL_ACCESS_ERROR_INVALID_SECRET
            )
        return secret
