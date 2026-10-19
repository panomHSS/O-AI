"""D156 safe read-only cognitive quality schemas."""
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.services.cognitive_quality_summary import CognitiveQualityCounts, CognitiveQualitySummary, CognitiveQualityComparison, rate_text


class CognitiveQualityCountsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    observed_count:int; verified_success_count:int; bounded_insufficiency_count:int; adverse_outcome_count:int; invalid_evidence_count:int
    terminal_completed_count:int; terminal_insufficient_count:int; terminal_failed_count:int
    verification_pass_count:int; verification_revise_count:int; verification_insufficient_evidence_count:int; verification_invalid_cognition_count:int
    revised_turn_count:int; critic_exhausted_count:int
    confidence_sufficient_count:int; confidence_limited_count:int; confidence_insufficient_count:int; confidence_unknown_count:int
    verified_success_rate:str|None; bounded_insufficiency_rate:str|None; adverse_outcome_rate:str|None; invalid_evidence_rate:str|None
    @classmethod
    def from_contract(cls,c:CognitiveQualityCounts):
        base={f:getattr(c,f) for f in c.__dataclass_fields__}; d=c.observed_count
        return cls(**base, verified_success_rate=rate_text(c.verified_success_count,d), bounded_insufficiency_rate=rate_text(c.bounded_insufficiency_count,d), adverse_outcome_rate=rate_text(c.adverse_outcome_count,d), invalid_evidence_rate=rate_text(c.invalid_evidence_count,d))


class CognitiveQualityBreakdownResponse(BaseModel):
    model_config=ConfigDict(extra="forbid")
    key:str; counts:CognitiveQualityCountsResponse


class CognitiveQualitySummaryResponse(BaseModel):
    model_config=ConfigDict(extra="forbid")
    workspace_id:str; since:datetime|None; until:datetime|None; counts:CognitiveQualityCountsResponse
    by_experience_cohort:list[CognitiveQualityBreakdownResponse]; by_task_kind:list[CognitiveQualityBreakdownResponse]
    @classmethod
    def from_contract(cls,s:CognitiveQualitySummary):
        conv=lambda x:CognitiveQualityBreakdownResponse(key=x.key,counts=CognitiveQualityCountsResponse.from_contract(x.counts))
        return cls(workspace_id=s.workspace_id.value,since=s.since,until=s.until,counts=CognitiveQualityCountsResponse.from_contract(s.counts),by_experience_cohort=[conv(x) for x in s.by_experience_cohort],by_task_kind=[conv(x) for x in s.by_task_kind])


class CognitiveQualityMetricDeltaResponse(BaseModel):
    model_config=ConfigDict(extra="forbid")
    metric:str; reference_count:int; candidate_count:int; delta_count:int


class CognitiveQualityRateDeltaResponse(BaseModel):
    model_config=ConfigDict(extra="forbid")
    metric:str; reference_numerator:int; candidate_numerator:int; reference_denominator:int; candidate_denominator:int
    reference_rate:str|None; candidate_rate:str|None; delta_rate:str|None


class CognitiveQualityComparisonResponse(BaseModel):
    model_config=ConfigDict(extra="forbid")
    reference:CognitiveQualitySummaryResponse; candidate:CognitiveQualitySummaryResponse
    count_deltas:list[CognitiveQualityMetricDeltaResponse]; rate_deltas:list[CognitiveQualityRateDeltaResponse]
    @classmethod
    def from_contract(cls,c:CognitiveQualityComparison):
        return cls(reference=CognitiveQualitySummaryResponse.from_contract(c.reference),candidate=CognitiveQualitySummaryResponse.from_contract(c.candidate),count_deltas=[CognitiveQualityMetricDeltaResponse(**{f:getattr(x,f) for f in x.__dataclass_fields__}) for x in c.count_deltas],rate_deltas=[CognitiveQualityRateDeltaResponse(**{f:getattr(x,f) for f in x.__dataclass_fields__}) for x in c.rate_deltas])
