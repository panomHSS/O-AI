"""D61 immutable contracts for Chat-to-Plugin action correlation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypeAlias
from uuid import UUID


ChatPluginIntentStatus: TypeAlias = Literal["none", "matched", "invalid"]


@dataclass(frozen=True, slots=True)
class ChatPluginIntentOutcome:
    """Deterministic classification only; carries no execution authority."""

    status: ChatPluginIntentStatus
    repository_reference: str | None = None

    def __post_init__(self) -> None:
        if self.status not in {"none", "matched", "invalid"}:
            raise ValueError("Unsupported Chat Plugin intent status.")
        if self.status == "matched":
            if (
                not isinstance(self.repository_reference, str)
                or not self.repository_reference
                or self.repository_reference
                != self.repository_reference.strip()
            ):
                raise ValueError(
                    "matched intent requires one repository_reference."
                )
        elif self.repository_reference is not None:
            raise ValueError(
                "non-matched intent must not carry repository_reference."
            )


@dataclass(frozen=True, slots=True)
class ChatPluginActionBinding:
    """Non-authoritative correlation from one D45 ticket to one chat turn."""

    approval_id: str
    conversation_id: UUID
    repository_reference: str
    expires_at: datetime

    def __post_init__(self) -> None:
        for label, value in (
            ("approval_id", self.approval_id),
            ("repository_reference", self.repository_reference),
        ):
            if (
                not isinstance(value, str)
                or not value
                or value != value.strip()
            ):
                raise ValueError(
                    f"{label} must be a non-empty trimmed string."
                )
        if not isinstance(self.conversation_id, UUID):
            raise TypeError("conversation_id must be a UUID.")
        if self.expires_at.tzinfo is None:
            raise ValueError("expires_at must be timezone-aware.")


@dataclass(frozen=True, slots=True)
class ChatPluginActionCompletion:
    """Safe final Chat message derived from an already-decided D45 outcome."""

    conversation_id: UUID
    reply: str

    def __post_init__(self) -> None:
        if not isinstance(self.conversation_id, UUID):
            raise TypeError("conversation_id must be a UUID.")
        if (
            not isinstance(self.reply, str)
            or not self.reply
            or self.reply != self.reply.strip()
        ):
            raise ValueError("reply must be a non-empty trimmed string.")
