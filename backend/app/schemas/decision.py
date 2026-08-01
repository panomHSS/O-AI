"""Safe public contracts for deterministic, non-executable decision analysis."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.reasoning import ReasoningEvidence, ReasoningIntent


RecommendationStatus = Literal["not_applicable", "insufficient_information", "owner_decision_required"]


class DecisionAlternative(BaseModel):
    """An explicitly mentioned option, never a selected recommendation."""

    id: str = Field(description="Stable deterministic alternative slug, unique within the analysis.")
    label: str = Field(description="Sanitized label extracted from the user question, not evidence or a recommendation.")


class DecisionTradeOff(BaseModel):
    """A fixed advisory consideration for an alternative, not a score or ranking."""

    alternative_id: str = Field(description="Existing alternative ID to which this advisory consideration applies.")
    criterion: str = Field(description="Fixed evaluation criterion; no score, probability, or selection is implied.")
    description: str = Field(description="Fixed advisory wording based only on available structured context.")


class DecisionAnalysis(BaseModel):
    """Deterministic explanatory metadata, not chain-of-thought, a ranking, or an automatic recommendation."""

    intent: ReasoningIntent = Field(description="Reasoning intent used to determine whether decision analysis applies.")
    alternatives: list[DecisionAlternative] = Field(default_factory=list, description="Explicitly extracted alternatives in deterministic source order.")
    evaluation_criteria: list[str] = Field(default_factory=list, description="Fixed deterministic criteria with no weights or scores.")
    trade_offs: list[DecisionTradeOff] = Field(default_factory=list, description="Advisory considerations only; never rankings or recommendations.")
    evidence_map: list[ReasoningEvidence] = Field(default_factory=list, description="Exact existing reasoning evidence references only; no values or excerpts.")
    recommendation_status: RecommendationStatus = Field(description="Never selects an alternative; owner review remains required.")
    missing_information: list[str] = Field(default_factory=list, description="Existing normalized PlanningPlan gap codes, not evidence or facts.")

    @model_validator(mode="after")
    def validate_references(self) -> "DecisionAnalysis":
        alternative_ids = [item.id for item in self.alternatives]
        if len(alternative_ids) != len(set(alternative_ids)):
            raise ValueError("Decision alternative IDs must be unique.")
        if len(self.evaluation_criteria) != len(set(self.evaluation_criteria)):
            raise ValueError("Decision evaluation criteria must be unique.")
        evidence_ids = [(item.kind, item.reference, item.label, item.version) for item in self.evidence_map]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("Decision evidence references must be unique.")
        trade_off_ids = [(item.alternative_id, item.criterion) for item in self.trade_offs]
        if len(trade_off_ids) != len(set(trade_off_ids)):
            raise ValueError("Decision trade-offs must be unique per alternative and criterion.")
        if any(trade_off.alternative_id not in alternative_ids for trade_off in self.trade_offs):
            raise ValueError("Decision trade-offs must reference an existing alternative.")
        if self.recommendation_status == "owner_decision_required" and len(self.alternatives) < 2:
            raise ValueError("Owner decision status requires at least two explicit alternatives.")
        return self
