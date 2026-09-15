"""D62 immutable credential access boundary contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pydantic import SecretStr


class CredentialContractError(ValueError):
    """Safe D62 contract error with a stable reason code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _text(value: object, *, code: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise CredentialContractError(code)
    return value


def _scopes(value: object) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise CredentialContractError("invalid_credential_required_scopes")
    scopes = tuple(
        _text(item, code="invalid_credential_required_scopes")
        for item in value
    )
    if len(set(scopes)) != len(scopes):
        raise CredentialContractError("invalid_credential_required_scopes")
    return tuple(sorted(scopes))


@dataclass(frozen=True, slots=True)
class CredentialProfile:
    """O-AI-controlled credential metadata for one exact Plugin capability."""

    profile_id: str
    plugin_id: str
    plugin_version: str
    capability_name: str
    provider_id: str
    auth_scheme: str
    required_scopes: tuple[str, ...]
    secret_ref: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "profile_id",
            _text(self.profile_id, code="invalid_credential_profile_id"),
        )
        object.__setattr__(
            self,
            "plugin_id",
            _text(self.plugin_id, code="invalid_credential_plugin_id"),
        )
        object.__setattr__(
            self,
            "plugin_version",
            _text(
                self.plugin_version,
                code="invalid_credential_plugin_version",
            ),
        )
        object.__setattr__(
            self,
            "capability_name",
            _text(
                self.capability_name,
                code="invalid_credential_capability_name",
            ),
        )
        object.__setattr__(
            self,
            "provider_id",
            _text(self.provider_id, code="invalid_credential_provider_id"),
        )
        object.__setattr__(
            self,
            "auth_scheme",
            _text(
                self.auth_scheme,
                code="invalid_credential_auth_scheme",
            ),
        )
        object.__setattr__(
            self,
            "required_scopes",
            _scopes(self.required_scopes),
        )
        object.__setattr__(
            self,
            "secret_ref",
            _text(self.secret_ref, code="invalid_credential_secret_ref"),
        )


@dataclass(frozen=True, slots=True)
class ResolvedCredential:
    """Internal resolved credential; secret_ref is intentionally not exposed."""

    profile_id: str
    plugin_id: str
    plugin_version: str
    capability_name: str
    provider_id: str
    auth_scheme: str
    required_scopes: tuple[str, ...]
    secret: SecretStr

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "profile_id",
            _text(self.profile_id, code="invalid_credential_profile_id"),
        )
        object.__setattr__(
            self,
            "plugin_id",
            _text(self.plugin_id, code="invalid_credential_plugin_id"),
        )
        object.__setattr__(
            self,
            "plugin_version",
            _text(
                self.plugin_version,
                code="invalid_credential_plugin_version",
            ),
        )
        object.__setattr__(
            self,
            "capability_name",
            _text(
                self.capability_name,
                code="invalid_credential_capability_name",
            ),
        )
        object.__setattr__(
            self,
            "provider_id",
            _text(self.provider_id, code="invalid_credential_provider_id"),
        )
        object.__setattr__(
            self,
            "auth_scheme",
            _text(
                self.auth_scheme,
                code="invalid_credential_auth_scheme",
            ),
        )
        object.__setattr__(
            self,
            "required_scopes",
            _scopes(self.required_scopes),
        )
        if not isinstance(self.secret, SecretStr):
            raise CredentialContractError("invalid_credential_secret")
        if not self.secret.get_secret_value():
            raise CredentialContractError("invalid_credential_secret")


class CredentialSecretSource(Protocol):
    """Infrastructure-only source for one O-AI-selected secret reference."""

    def resolve(self, secret_ref: str) -> SecretStr | None:
        """Resolve a fixed secret reference without creating authority."""
        ...
