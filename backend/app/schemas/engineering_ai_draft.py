"""D110 owner-facing non-authoritative AI draft API schemas."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.engineering_ai_draft import (
    ENGINEERING_AI_DRAFT_INSTRUCTION_MAX_CHARS,
    EngineeringAIDraftResult,
)


_HEX_PATTERN = r"^[0-9a-f]{64}$"


class EngineeringAIDraftCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID
    relative_path: str
    instruction: str = Field(
        min_length=1,
        max_length=ENGINEERING_AI_DRAFT_INSTRUCTION_MAX_CHARS,
    )


class EngineeringAIDraftResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str
    conversation_id: UUID
    relative_path: str
    draft_operation: Literal["create_text", "replace_text"]
    source_state: Literal["absent", "present"]
    source_sha256: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        pattern=_HEX_PATTERN,
    )
    source_size_bytes: int | None = Field(default=None, ge=0)
    draft_content: str
    ai_adapter_id: str = Field(min_length=1)

    @classmethod
    def from_result(
        cls,
        result: EngineeringAIDraftResult,
    ) -> "EngineeringAIDraftResponse":
        return cls(
            contract_version=result.contract_version,
            conversation_id=result.conversation_id,
            relative_path=result.relative_path,
            draft_operation=result.draft_operation,
            source_state=result.source_state,
            source_sha256=result.source_sha256,
            source_size_bytes=result.source_size_bytes,
            draft_content=result.draft_content,
            ai_adapter_id=result.ai_adapter_id,
        )


__all__ = [
    "EngineeringAIDraftCreateRequest",
    "EngineeringAIDraftResponse",
]
