"""D76 immutable exact Google OAuth credential-subject contract."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


class GoogleOAuthSubjectError(ValueError):
    """Safe D76 subject validation error."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _text(value: object, *, code: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or "\r" in value
        or "\n" in value
    ):
        raise GoogleOAuthSubjectError(code)
    return value


@dataclass(frozen=True, slots=True)
class GoogleOAuthCredentialSubject:
    """One O-AI-controlled OAuth identity and exact single-scope grant."""

    profile_id: str
    provider_id: str
    plugin_id: str
    plugin_version: str
    capability_name: str
    scope: str
    secret_ref: str
    callback_path: str

    def __post_init__(self) -> None:
        for field_name in (
            "profile_id",
            "provider_id",
            "plugin_id",
            "plugin_version",
            "capability_name",
            "scope",
            "secret_ref",
            "callback_path",
        ):
            object.__setattr__(
                self,
                field_name,
                _text(
                    getattr(self, field_name),
                    code=f"invalid_google_oauth_{field_name}",
                ),
            )

        if (
            not self.scope.startswith("https://www.googleapis.com/auth/")
            or any(character.isspace() for character in self.scope)
        ):
            raise GoogleOAuthSubjectError("invalid_google_oauth_scope")

        parsed = urlsplit(self.callback_path)
        if (
            not self.callback_path.startswith("/")
            or self.callback_path.startswith("//")
            or parsed.scheme
            or parsed.netloc
            or parsed.query
            or parsed.fragment
            or parsed.path != self.callback_path
        ):
            raise GoogleOAuthSubjectError("invalid_google_oauth_callback_path")

    @property
    def aad(self) -> bytes:
        return (
            "oauth-v1|"
            f"{self.profile_id}|"
            f"{self.provider_id}|"
            f"{self.plugin_id}|"
            f"{self.plugin_version}|"
            f"{self.capability_name}|"
            f"{self.scope}"
        ).encode("utf-8")


__all__ = [
    "GoogleOAuthCredentialSubject",
    "GoogleOAuthSubjectError",
]
