"""Public, provider-neutral representation of deterministic per-turn reasoning."""

from typing import Literal

from pydantic import BaseModel, Field


ReasoningIntent = Literal["factual_lookup", "explanation", "comparison", "procedure", "troubleshooting", "summary", "general"]
EvidenceKind = Literal["memory", "document"]


class ReasoningEvidence(BaseModel):
    kind: EvidenceKind
    reference: str
    label: str
    version: int | None = None


class ReasoningPlan(BaseModel):
    """Safe deterministic planning metadata, not hidden model reasoning or chain-of-thought."""

    intent: ReasoningIntent
    normalized_question: str
    required_information: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    evidence_map: list[ReasoningEvidence] = Field(default_factory=list)
