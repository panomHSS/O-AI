"""D109 owner-facing Engineering API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.engineering_read import (
    EngineeringDirectoryListing,
    EngineeringPathStat,
    EngineeringRepositoryOverview,
    EngineeringTextRead,
)
from app.services.engineering_owner_binding import EngineeringOwnerBinding


_HEX_PATTERN = r"^[0-9a-f]{64}$"


class EngineeringOwnerReadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID
    operation: Literal[
        "repository_overview",
        "list_directory",
        "stat_path",
        "read_text",
    ]
    relative_path: str | None = None


class EngineeringOwnerReadEntryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relative_path: str
    kind: Literal["file", "directory"]
    size_bytes: int | None = None


class EngineeringOwnerReadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    conversation_id: UUID
    operation: str
    relative_path: str | None = None
    entries: list[EngineeringOwnerReadEntryResponse] | None = None
    entry: EngineeringOwnerReadEntryResponse | None = None
    content: str | None = None
    size_bytes: int | None = None
    content_sha256: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        pattern=_HEX_PATTERN,
    )

    @classmethod
    def from_observation(
        cls,
        *,
        workspace_id: str,
        conversation_id: UUID,
        observation: (
            EngineeringRepositoryOverview
            | EngineeringDirectoryListing
            | EngineeringPathStat
            | EngineeringTextRead
        ),
    ) -> "EngineeringOwnerReadResponse":
        if isinstance(observation, EngineeringRepositoryOverview):
            return cls(
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                operation="repository_overview",
                entries=[
                    EngineeringOwnerReadEntryResponse(
                        relative_path=item.relative_path,
                        kind=item.kind,
                        size_bytes=item.size_bytes,
                    )
                    for item in observation.entries
                ],
            )
        if isinstance(observation, EngineeringDirectoryListing):
            return cls(
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                operation="list_directory",
                relative_path=observation.relative_path,
                entries=[
                    EngineeringOwnerReadEntryResponse(
                        relative_path=item.relative_path,
                        kind=item.kind,
                        size_bytes=item.size_bytes,
                    )
                    for item in observation.entries
                ],
            )
        if isinstance(observation, EngineeringPathStat):
            item = observation.entry
            return cls(
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                operation="stat_path",
                relative_path=item.relative_path,
                entry=EngineeringOwnerReadEntryResponse(
                    relative_path=item.relative_path,
                    kind=item.kind,
                    size_bytes=item.size_bytes,
                ),
            )
        if isinstance(observation, EngineeringTextRead):
            return cls(
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                operation="read_text",
                relative_path=observation.relative_path,
                content=observation.content,
                size_bytes=observation.size_bytes,
                content_sha256=observation.content_sha256,
            )
        raise ValueError("engineering_owner_request_invalid")


class EngineeringOwnerProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID
    operation: Literal["create_text", "replace_text"]
    relative_path: str
    proposed_content: str


class EngineeringOwnerReviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["create_text", "replace_text"]
    relative_path: str
    base_state: Literal["absent", "present"]
    before_content: str | None
    before_sha256: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        pattern=_HEX_PATTERN,
    )
    before_size_bytes: int | None
    after_content: str
    after_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=_HEX_PATTERN,
    )
    after_size_bytes: int


class EngineeringOwnerWorkflowResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    conversation_id: UUID
    approval_id: str
    proposal_digest: str = Field(
        min_length=64,
        max_length=64,
        pattern=_HEX_PATTERN,
    )
    presentation_state: Literal["pending"]
    expires_at: datetime
    review: EngineeringOwnerReviewResponse

    @classmethod
    def from_binding(
        cls,
        *,
        workspace_id: str,
        binding: EngineeringOwnerBinding,
    ) -> "EngineeringOwnerWorkflowResponse":
        review = binding.review
        return cls(
            workspace_id=workspace_id,
            conversation_id=binding.conversation_id,
            approval_id=binding.approval_id,
            proposal_digest=binding.proposal_digest,
            presentation_state=binding.presentation_state,
            expires_at=binding.expires_at,
            review=EngineeringOwnerReviewResponse(
                operation=review.operation,
                relative_path=review.relative_path,
                base_state=review.base_state,
                before_content=review.before_content,
                before_sha256=review.before_sha256,
                before_size_bytes=review.before_size_bytes,
                after_content=review.after_content,
                after_sha256=review.after_sha256,
                after_size_bytes=review.after_size_bytes,
            ),
        )


class EngineeringOwnerActiveWorkflowResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    conversation_id: UUID
    active: EngineeringOwnerWorkflowResponse | None


__all__ = [
    "EngineeringOwnerActiveWorkflowResponse",
    "EngineeringOwnerProposalRequest",
    "EngineeringOwnerReadEntryResponse",
    "EngineeringOwnerReadRequest",
    "EngineeringOwnerReadResponse",
    "EngineeringOwnerReviewResponse",
    "EngineeringOwnerWorkflowResponse",
]
