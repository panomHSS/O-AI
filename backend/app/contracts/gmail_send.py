"""D86 immutable provider-neutral Gmail send contracts.

Contract construction grants no approval, authorization, credential access,
provider/network access, or send authority.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Literal


GMAIL_SEND_CONTRACT_VERSION = "1"
GMAIL_SEND_OPERATION = "send_message"

GMAIL_SEND_MAX_RECIPIENT_BYTES = 320
GMAIL_SEND_MAX_SUBJECT_BYTES = 1024
GMAIL_SEND_MAX_BODY_BYTES = 16 * 1024

_EMAIL_ADDRESS_RE = re.compile(
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+"
)

_BODY_ALLOWED_CONTROLS = frozenset({"\n", "\t"})


def _contains_control(value: str) -> bool:
    return any(unicodedata.category(character) == "Cc" for character in value)


def _contains_forbidden_body_control(value: str) -> bool:
    return any(
        unicodedata.category(character) == "Cc"
        and character not in _BODY_ALLOWED_CONTROLS
        for character in value
    )


def _validate_recipient(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > GMAIL_SEND_MAX_RECIPIENT_BYTES
        or _contains_control(value)
        or _EMAIL_ADDRESS_RE.fullmatch(value) is None
    ):
        raise ValueError("gmail_send_recipient_invalid")

    local_part, _, _ = value.partition("@")
    if (
        local_part.startswith(".")
        or local_part.endswith(".")
        or ".." in local_part
    ):
        raise ValueError("gmail_send_recipient_invalid")
    return value


def _validate_subject(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or not value.strip()
        or value != value.strip()
        or len(value.encode("utf-8")) > GMAIL_SEND_MAX_SUBJECT_BYTES
        or _contains_control(value)
    ):
        raise ValueError("gmail_send_subject_invalid")
    return value


def _validate_body(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or not value.strip()
        or len(value.encode("utf-8")) > GMAIL_SEND_MAX_BODY_BYTES
        or _contains_forbidden_body_control(value)
    ):
        raise ValueError("gmail_send_body_invalid")
    return value


@dataclass(frozen=True, slots=True)
class GmailSendDraft:
    """One bounded plain-text Gmail message draft; never sends email."""

    recipient: str
    subject: str
    body: str

    def __post_init__(self) -> None:
        _validate_recipient(self.recipient)
        _validate_subject(self.subject)
        _validate_body(self.body)


@dataclass(frozen=True, slots=True)
class GmailSendRequest:
    """D86 contract-only request; approval and execution belong to D87/D88."""

    message: GmailSendDraft
    contract_version: Literal["1"] = field(
        default=GMAIL_SEND_CONTRACT_VERSION,
        init=False,
    )
    operation: Literal["send_message"] = field(
        default=GMAIL_SEND_OPERATION,
        init=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.message, GmailSendDraft):
            raise ValueError("gmail_send_draft_invalid")


__all__ = [
    "GMAIL_SEND_CONTRACT_VERSION",
    "GMAIL_SEND_MAX_BODY_BYTES",
    "GMAIL_SEND_MAX_RECIPIENT_BYTES",
    "GMAIL_SEND_MAX_SUBJECT_BYTES",
    "GMAIL_SEND_OPERATION",
    "GmailSendDraft",
    "GmailSendRequest",
]
