"""D88 immutable Gmail send execution contracts and exact plan projection.

D88 execution contracts bind one exact D87-approved D86 request to a fixed
deployment-controlled sender and a private module execution plan. Constructing
these values grants no authorization, credential access, network access, or
provider send authority.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.gmail_send import (
    GMAIL_SEND_CONTRACT_VERSION,
    GMAIL_SEND_OPERATION,
    GmailSendDraft,
    GmailSendRequest,
)

GMAIL_SEND_MAX_PROVIDER_MESSAGE_ID_BYTES = 1024

GMAIL_SEND_ADAPTER_ID = "module.gmail.send_message"
GMAIL_SEND_CAPABILITY_ID = "exec.gmail.send_message"
GMAIL_SEND_MODULE_NAME = "Gmail Send Message"
GMAIL_SEND_CAPABILITY_NAME = "send_message"
GMAIL_SEND_CREDENTIAL_PROFILE_ID = "gmail.messages.send"
GMAIL_SEND_CREDENTIAL_SCOPE = "https://www.googleapis.com/auth/gmail.send"
GMAIL_SEND_CREDENTIAL_SECRET_REF = "gmail.send.access_token"

GmailSendExecutionStatus: TypeAlias = Literal[
    "succeeded",
    "failed",
    "indeterminate",
]

_REQUIRED_EXECUTION_PARAMETER_KEYS = frozenset(
    {
        "contract_version",
        "send_digest",
        "sender",
        "recipient",
        "subject",
        "body",
    }
)
_HEX = frozenset("0123456789abcdef")


def _trimmed_text(value: object, *, code: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
    ):
        raise ValueError(code)
    return value


def validate_send_digest(value: object) -> str:
    digest = _trimmed_text(
        value,
        code="gmail_send_execution_send_digest_invalid",
    )
    if len(digest) != 64 or any(ch not in _HEX for ch in digest):
        raise ValueError("gmail_send_execution_send_digest_invalid")
    return digest


def validate_plan_digest(value: object) -> str:
    digest = _trimmed_text(
        value,
        code="gmail_send_execution_plan_digest_invalid",
    )
    if len(digest) != 64 or any(ch not in _HEX for ch in digest):
        raise ValueError("gmail_send_execution_plan_digest_invalid")
    return digest


def validate_sender(value: object) -> str:
    sender = _trimmed_text(
        value,
        code="gmail_send_execution_sender_invalid",
    )
    try:
        # D86 recipient validation is the canonical exact-one-mailbox rule.
        GmailSendDraft(
            recipient=sender,
            subject="D88 sender validation",
            body="D88 sender validation",
        )
    except (TypeError, ValueError):
        raise ValueError("gmail_send_execution_sender_invalid") from None
    return sender


def gmail_send_execution_parameters(
    request: GmailSendRequest,
    send_digest: str,
    *,
    sender: str,
) -> dict[str, str]:
    """Project one exact D86 request into one private D88 plan payload."""
    if not isinstance(request, GmailSendRequest):
        raise ValueError("gmail_send_execution_request_invalid")
    return {
        "contract_version": request.contract_version,
        "send_digest": validate_send_digest(send_digest),
        "sender": validate_sender(sender),
        "recipient": request.message.recipient,
        "subject": request.message.subject,
        "body": request.message.body,
    }


def gmail_send_request_from_parameters(
    parameters: object,
) -> tuple[GmailSendRequest, str, str]:
    """Reconstruct the exact D86 request, digest, and fixed sender."""
    if (
        not isinstance(parameters, Mapping)
        or frozenset(parameters) != _REQUIRED_EXECUTION_PARAMETER_KEYS
        or parameters.get("contract_version") != GMAIL_SEND_CONTRACT_VERSION
    ):
        raise ValueError("gmail_send_execution_parameters_invalid")

    try:
        digest = validate_send_digest(parameters.get("send_digest"))
        sender = validate_sender(parameters.get("sender"))
        request = GmailSendRequest(
            message=GmailSendDraft(
                recipient=parameters.get("recipient"),  # type: ignore[arg-type]
                subject=parameters.get("subject"),  # type: ignore[arg-type]
                body=parameters.get("body"),  # type: ignore[arg-type]
            )
        )
    except (TypeError, ValueError):
        raise ValueError("gmail_send_execution_parameters_invalid") from None

    if (
        request.contract_version != GMAIL_SEND_CONTRACT_VERSION
        or request.operation != GMAIL_SEND_OPERATION
    ):
        raise ValueError("gmail_send_execution_parameters_invalid")
    return request, digest, sender


@dataclass(frozen=True, slots=True)
class GmailSendExecutionClaim:
    """One immutable one-shot claim; not proof that a send was attempted."""

    approval_id: str
    send_digest: str
    plan_digest: str
    sender: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "approval_id",
            _trimmed_text(
                self.approval_id,
                code="gmail_send_execution_approval_id_invalid",
            ),
        )
        object.__setattr__(
            self,
            "send_digest",
            validate_send_digest(self.send_digest),
        )
        object.__setattr__(
            self,
            "plan_digest",
            validate_plan_digest(self.plan_digest),
        )
        object.__setattr__(
            self,
            "sender",
            validate_sender(self.sender),
        )
        if self.send_digest == self.plan_digest:
            raise ValueError("gmail_send_execution_digest_domain_collision")


@dataclass(frozen=True, slots=True)
class GmailSendExecutionOutcome:
    """Bounded truthful D88 terminal result with no secret/provider body."""

    approval_id: str
    send_digest: str
    status: GmailSendExecutionStatus
    reason_code: str
    provider_attempted: bool
    message_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "approval_id",
            _trimmed_text(
                self.approval_id,
                code="gmail_send_execution_approval_id_invalid",
            ),
        )
        object.__setattr__(
            self,
            "send_digest",
            validate_send_digest(self.send_digest),
        )
        object.__setattr__(
            self,
            "reason_code",
            _trimmed_text(
                self.reason_code,
                code="gmail_send_execution_reason_code_invalid",
            ),
        )
        if self.status not in {"succeeded", "failed", "indeterminate"}:
            raise ValueError("gmail_send_execution_status_invalid")
        if type(self.provider_attempted) is not bool:
            raise ValueError("gmail_send_execution_provider_attempted_invalid")

        if self.status == "succeeded":
            if not self.provider_attempted:
                raise ValueError(
                    "gmail_send_execution_success_requires_provider_attempt"
                )
            object.__setattr__(
                self,
                "message_id",
                _provider_message_id(self.message_id),
            )
        elif self.status == "indeterminate":
            if not self.provider_attempted:
                raise ValueError(
                    "gmail_send_execution_indeterminate_requires_provider_attempt"
                )
            if self.message_id is not None:
                raise ValueError(
                    "gmail_send_execution_message_id_unexpected"
                )
        elif self.message_id is not None:
            raise ValueError("gmail_send_execution_message_id_unexpected")


def _provider_message_id(value: object) -> str:
    message_id = _trimmed_text(
        value,
        code="gmail_send_execution_message_id_invalid",
    )
    if (
        len(message_id.encode("utf-8"))
        > GMAIL_SEND_MAX_PROVIDER_MESSAGE_ID_BYTES
        or any(
            unicodedata.category(character) == "Cc"
            for character in message_id
        )
    ):
        raise ValueError("gmail_send_execution_message_id_invalid")
    return message_id


__all__ = [
    "GMAIL_SEND_ADAPTER_ID",
    "GMAIL_SEND_CAPABILITY_ID",
    "GMAIL_SEND_CAPABILITY_NAME",
    "GMAIL_SEND_CREDENTIAL_PROFILE_ID",
    "GMAIL_SEND_CREDENTIAL_SCOPE",
    "GMAIL_SEND_CREDENTIAL_SECRET_REF",
    "GMAIL_SEND_MAX_PROVIDER_MESSAGE_ID_BYTES",
    "GMAIL_SEND_MODULE_NAME",
    "GmailSendExecutionClaim",
    "GmailSendExecutionOutcome",
    "GmailSendExecutionStatus",
    "gmail_send_execution_parameters",
    "gmail_send_request_from_parameters",
    "validate_plan_digest",
    "validate_send_digest",
    "validate_sender",
]
