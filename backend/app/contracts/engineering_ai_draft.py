"""D110 non-authoritative AI-assisted Engineering draft contracts.

A D110 draft is candidate text only. It grants no repository path authority,
D107 proposal authority, owner approval, D108 apply authority, Tool/Module
authority, shell/process authority, Git authority, network authority, or
credential authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal, TypeAlias
from uuid import UUID

from app.contracts.engineering_change_proposal import (
    validate_engineering_change_content,
)
from app.contracts.engineering_read import validate_engineering_relative_path


ENGINEERING_AI_DRAFT_CONTRACT_VERSION = "d110.v1"
ENGINEERING_AI_DRAFT_INSTRUCTION_MAX_CHARS = 8_000

EngineeringAIDraftOperation: TypeAlias = Literal["create_text", "replace_text"]
EngineeringAIDraftSourceState: TypeAlias = Literal["absent", "present"]

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _validated_instruction(value: object) -> str:
    if type(value) is not str:
        raise ValueError("engineering_ai_draft_request_invalid")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("engineering_ai_draft_request_invalid") from None
    normalized = value.strip()
    if (
        not normalized
        or "\x00" in normalized
        or len(normalized) > ENGINEERING_AI_DRAFT_INSTRUCTION_MAX_CHARS
    ):
        raise ValueError("engineering_ai_draft_request_invalid")
    return normalized


def _validate_draft_content(value: object) -> str:
    try:
        return validate_engineering_change_content(value)
    except ValueError as exc:
        if str(exc) == "engineering_change_proposed_content_too_large":
            raise ValueError("engineering_ai_draft_too_large") from None
        raise ValueError("engineering_ai_draft_output_invalid") from None


@dataclass(frozen=True, slots=True)
class EngineeringAIDraftRequest:
    """Exact owner input for one non-authoritative D110 draft."""

    conversation_id: UUID
    relative_path: str
    instruction: str

    def __post_init__(self) -> None:
        if not isinstance(self.conversation_id, UUID):
            raise ValueError("engineering_ai_draft_request_invalid")
        try:
            validate_engineering_relative_path(self.relative_path)
        except ValueError:
            raise ValueError("engineering_ai_draft_path_invalid") from None
        normalized = _validated_instruction(self.instruction)
        object.__setattr__(self, "instruction", normalized)


@dataclass(frozen=True, slots=True)
class EngineeringAIDraftResult:
    """One non-authoritative candidate text result."""

    contract_version: str = field(
        default=ENGINEERING_AI_DRAFT_CONTRACT_VERSION,
        init=False,
    )
    conversation_id: UUID
    relative_path: str
    draft_operation: EngineeringAIDraftOperation
    source_state: EngineeringAIDraftSourceState
    source_sha256: str | None
    source_size_bytes: int | None
    draft_content: str
    ai_adapter_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.conversation_id, UUID):
            raise ValueError("engineering_ai_draft_output_invalid")
        try:
            validate_engineering_relative_path(self.relative_path)
        except ValueError:
            raise ValueError("engineering_ai_draft_path_invalid") from None

        if self.draft_operation not in {"create_text", "replace_text"}:
            raise ValueError("engineering_ai_draft_output_invalid")
        if self.source_state not in {"absent", "present"}:
            raise ValueError("engineering_ai_draft_output_invalid")

        if self.source_state == "absent":
            if (
                self.draft_operation != "create_text"
                or self.source_sha256 is not None
                or self.source_size_bytes is not None
            ):
                raise ValueError("engineering_ai_draft_output_invalid")
        else:
            if (
                self.draft_operation != "replace_text"
                or type(self.source_sha256) is not str
                or _SHA256_RE.fullmatch(self.source_sha256) is None
                or type(self.source_size_bytes) is not int
                or self.source_size_bytes < 0
            ):
                raise ValueError("engineering_ai_draft_output_invalid")

        _validate_draft_content(self.draft_content)

        if (
            type(self.ai_adapter_id) is not str
            or not self.ai_adapter_id
            or self.ai_adapter_id != self.ai_adapter_id.strip()
        ):
            raise ValueError("engineering_ai_draft_output_invalid")


__all__ = [
    "ENGINEERING_AI_DRAFT_CONTRACT_VERSION",
    "ENGINEERING_AI_DRAFT_INSTRUCTION_MAX_CHARS",
    "EngineeringAIDraftOperation",
    "EngineeringAIDraftRequest",
    "EngineeringAIDraftResult",
    "EngineeringAIDraftSourceState",
]
