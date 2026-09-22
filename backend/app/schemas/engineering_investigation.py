"""D113 owner-facing read-only Engineering Investigation API schemas."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.engineering_investigation import (
    ENGINEERING_INVESTIGATION_INSTRUCTION_MAX_CHARS,
    ENGINEERING_INVESTIGATION_MAX_FOCUS_PATHS,
    EngineeringInvestigationResult,
)


class EngineeringInvestigationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID
    instruction: str = Field(
        min_length=1,
        max_length=ENGINEERING_INVESTIGATION_INSTRUCTION_MAX_CHARS,
    )
    focus_paths: list[str] = Field(
        default_factory=list,
        max_length=ENGINEERING_INVESTIGATION_MAX_FOCUS_PATHS,
    )


class EngineeringInvestigationFindingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str
    title: str
    detail: str
    evidence_refs: list[str]
    confidence: Literal["low", "medium", "high"]


class EngineeringInvestigationChangePlanItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: int
    title: str
    rationale: str
    candidate_relative_path: str | None
    candidate_change_kind: Literal[
        "inspect",
        "create_text",
        "replace_text",
        "test",
        "documentation",
        "configuration",
        "other",
    ]
    evidence_refs: list[str]


class EngineeringInvestigationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    contract_version: str
    conversation_id: UUID
    summary: str
    findings: list[EngineeringInvestigationFindingResponse]
    change_plan: list[EngineeringInvestigationChangePlanItemResponse]
    evidence_refs: list[str]
    focus_paths: list[str]

    @classmethod
    def from_result(
        cls,
        *,
        workspace_id: str,
        focus_paths: tuple[str, ...],
        result: EngineeringInvestigationResult,
    ) -> "EngineeringInvestigationResponse":
        return cls(
            workspace_id=workspace_id,
            contract_version=result.contract_version,
            conversation_id=result.conversation_id,
            summary=result.summary,
            findings=[
                EngineeringInvestigationFindingResponse(
                    finding_id=item.finding_id,
                    title=item.title,
                    detail=item.detail,
                    evidence_refs=list(item.evidence_refs),
                    confidence=item.confidence,
                )
                for item in result.findings
            ],
            change_plan=[
                EngineeringInvestigationChangePlanItemResponse(
                    sequence=item.sequence,
                    title=item.title,
                    rationale=item.rationale,
                    candidate_relative_path=item.candidate_relative_path,
                    candidate_change_kind=item.candidate_change_kind,
                    evidence_refs=list(item.evidence_refs),
                )
                for item in result.change_plan
            ],
            evidence_refs=list(result.evidence_refs),
            focus_paths=list(focus_paths),
        )


__all__ = [
    "EngineeringInvestigationChangePlanItemResponse",
    "EngineeringInvestigationCreateRequest",
    "EngineeringInvestigationFindingResponse",
    "EngineeringInvestigationResponse",
]