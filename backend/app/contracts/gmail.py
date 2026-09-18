"""D76/D77 exact Gmail credential identity and bounded read contracts."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Literal


GMAIL_PLUGIN_ID = "gmail"
GMAIL_PLUGIN_VERSION = "1.0.0"
GMAIL_READ_CAPABILITY_NAME = "read_messages"
GMAIL_READ_CREDENTIAL_PROFILE_ID = "gmail.messages.readonly"
GMAIL_CREDENTIAL_PROVIDER_ID = "google"
GMAIL_CREDENTIAL_AUTH_SCHEME = "oauth2_bearer"
GMAIL_CREDENTIAL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
GMAIL_CREDENTIAL_SECRET_REF = "gmail.access_token"

GMAIL_ADAPTER_ID = "module.plugin.gmail"
GMAIL_OPERATION = "read_messages"
GMAIL_CAPABILITY_ID = "exec.plugin.gmail.read_messages"

GMAIL_READ_MODE_RECENT = "recent"
GMAIL_READ_MODE_UNREAD = "unread"
GMAIL_READ_MODE_FROM = "from"
GMAIL_READ_MODES = frozenset(
    {
        GMAIL_READ_MODE_RECENT,
        GMAIL_READ_MODE_UNREAD,
        GMAIL_READ_MODE_FROM,
    }
)
GMAIL_MAX_RESULTS = 5
GMAIL_MAX_SENDER_QUERY_BYTES = 320
GMAIL_MAX_MESSAGE_ID_BYTES = 1024
GMAIL_MAX_FROM_CHARS = 1024
GMAIL_MAX_SUBJECT_CHARS = 1024
GMAIL_MAX_SNIPPET_CHARS = 512
GMAIL_MAX_BODY_CHARS = 4096

_EMAIL_ADDRESS_RE = re.compile(
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+"
)


def _contains_control(value: str) -> bool:
    return any(unicodedata.category(character) == "Cc" for character in value)


def _validated_sender(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > GMAIL_MAX_SENDER_QUERY_BYTES
        or _contains_control(value)
        or _EMAIL_ADDRESS_RE.fullmatch(value) is None
    ):
        raise ValueError("gmail_query_sender_invalid")
    return value


def _validated_text(value: object, *, max_chars: int, code: str) -> str:
    if not isinstance(value, str) or len(value) > max_chars:
        raise ValueError(code)
    return value


@dataclass(frozen=True, slots=True)
class GmailReadQuery:
    """One exact, bounded Gmail read intent; never accepts raw Gmail search."""

    mode: Literal["recent", "unread", "from"]
    sender: str | None = None

    def __post_init__(self) -> None:
        if self.mode not in GMAIL_READ_MODES:
            raise ValueError("gmail_query_mode_invalid")
        if self.mode == GMAIL_READ_MODE_FROM:
            _validated_sender(self.sender)
        elif self.sender is not None:
            raise ValueError("gmail_query_sender_not_allowed")

    @property
    def provider_query(self) -> str | None:
        if self.mode == GMAIL_READ_MODE_RECENT:
            return None
        if self.mode == GMAIL_READ_MODE_UNREAD:
            return "is:unread"
        assert self.sender is not None
        return f"from:{self.sender}"

    def to_parameters(self) -> dict[str, str]:
        result = {"mode": self.mode}
        if self.sender is not None:
            result["sender"] = self.sender
        return result

    @classmethod
    def from_parameters(cls, parameters: object) -> "GmailReadQuery":
        if not isinstance(parameters, Mapping):
            raise ValueError("gmail_query_invalid")
        mode = parameters.get("mode")
        if mode == GMAIL_READ_MODE_FROM:
            if set(parameters) != {"mode", "sender"}:
                raise ValueError("gmail_query_invalid")
            sender = parameters.get("sender")
            try:
                return cls(mode=mode, sender=sender)
            except (TypeError, ValueError):
                raise ValueError("gmail_query_invalid") from None
        if mode in (GMAIL_READ_MODE_RECENT, GMAIL_READ_MODE_UNREAD):
            if set(parameters) != {"mode"}:
                raise ValueError("gmail_query_invalid")
            try:
                return cls(mode=mode)
            except (TypeError, ValueError):
                raise ValueError("gmail_query_invalid") from None
        raise ValueError("gmail_query_invalid")


@dataclass(frozen=True, slots=True)
class GmailMessage:
    """Bounded provider-neutral message projection safe for D77 completion."""

    message_id: str
    sender: str
    subject: str
    received_at: str
    unread: bool
    snippet: str
    body: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.message_id, str)
            or not self.message_id
            or self.message_id != self.message_id.strip()
            or len(self.message_id.encode("utf-8")) > GMAIL_MAX_MESSAGE_ID_BYTES
            or _contains_control(self.message_id)
        ):
            raise ValueError("gmail_message_id_invalid")
        _validated_text(
            self.sender,
            max_chars=GMAIL_MAX_FROM_CHARS,
            code="gmail_message_sender_invalid",
        )
        _validated_text(
            self.subject,
            max_chars=GMAIL_MAX_SUBJECT_CHARS,
            code="gmail_message_subject_invalid",
        )
        _validated_text(
            self.snippet,
            max_chars=GMAIL_MAX_SNIPPET_CHARS,
            code="gmail_message_snippet_invalid",
        )
        _validated_text(
            self.body,
            max_chars=GMAIL_MAX_BODY_CHARS,
            code="gmail_message_body_invalid",
        )
        if (
            not isinstance(self.received_at, str)
            or not self.received_at.endswith("Z")
        ):
            raise ValueError("gmail_message_received_at_invalid")
        try:
            parsed = datetime.fromisoformat(
                self.received_at.replace("Z", "+00:00")
            )
        except ValueError:
            raise ValueError("gmail_message_received_at_invalid") from None
        if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
            raise ValueError("gmail_message_received_at_invalid")
        if type(self.unread) is not bool:
            raise ValueError("gmail_message_unread_invalid")

    def as_dict(self) -> dict[str, object]:
        return {
            "body": self.body,
            "from": self.sender,
            "message_id": self.message_id,
            "received_at": self.received_at,
            "snippet": self.snippet,
            "subject": self.subject,
            "unread": self.unread,
        }


@dataclass(frozen=True, slots=True)
class GmailReadDisplayMessage:
    """Transient owner-display projection with no provider message identity."""

    sender: str
    subject: str
    received_at: str
    unread: bool
    snippet: str
    body: str

    def __post_init__(self) -> None:
        _validated_text(
            self.sender,
            max_chars=GMAIL_MAX_FROM_CHARS,
            code="gmail_display_sender_invalid",
        )
        _validated_text(
            self.subject,
            max_chars=GMAIL_MAX_SUBJECT_CHARS,
            code="gmail_display_subject_invalid",
        )
        _validated_text(
            self.snippet,
            max_chars=GMAIL_MAX_SNIPPET_CHARS,
            code="gmail_display_snippet_invalid",
        )
        _validated_text(
            self.body,
            max_chars=GMAIL_MAX_BODY_CHARS,
            code="gmail_display_body_invalid",
        )
        if (
            not isinstance(self.received_at, str)
            or not self.received_at.endswith("Z")
        ):
            raise ValueError("gmail_display_received_at_invalid")
        try:
            parsed = datetime.fromisoformat(
                self.received_at.replace("Z", "+00:00")
            )
        except ValueError:
            raise ValueError("gmail_display_received_at_invalid") from None
        if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
            raise ValueError("gmail_display_received_at_invalid")
        if type(self.unread) is not bool:
            raise ValueError("gmail_display_unread_invalid")


@dataclass(frozen=True, slots=True)
class GmailReadResult:
    """One bounded D77 read result with no provider pagination token."""

    messages: tuple[GmailMessage, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.messages, tuple)
            or len(self.messages) > GMAIL_MAX_RESULTS
            or any(
                not isinstance(message, GmailMessage)
                for message in self.messages
            )
        ):
            raise ValueError("gmail_read_result_invalid")


__all__ = [
    "GMAIL_ADAPTER_ID",
    "GMAIL_CAPABILITY_ID",
    "GMAIL_CREDENTIAL_AUTH_SCHEME",
    "GMAIL_CREDENTIAL_PROVIDER_ID",
    "GMAIL_CREDENTIAL_SCOPE",
    "GMAIL_CREDENTIAL_SECRET_REF",
    "GMAIL_MAX_BODY_CHARS",
    "GMAIL_MAX_FROM_CHARS",
    "GMAIL_MAX_MESSAGE_ID_BYTES",
    "GMAIL_MAX_RESULTS",
    "GMAIL_MAX_SENDER_QUERY_BYTES",
    "GMAIL_MAX_SNIPPET_CHARS",
    "GMAIL_MAX_SUBJECT_CHARS",
    "GMAIL_OPERATION",
    "GMAIL_PLUGIN_ID",
    "GMAIL_PLUGIN_VERSION",
    "GMAIL_READ_CAPABILITY_NAME",
    "GMAIL_READ_CREDENTIAL_PROFILE_ID",
    "GMAIL_READ_MODE_FROM",
    "GMAIL_READ_MODE_RECENT",
    "GMAIL_READ_MODE_UNREAD",
    "GmailMessage",
    "GmailReadDisplayMessage",
    "GmailReadQuery",
    "GmailReadResult",
]
