"""D156 read-only longitudinal quality aggregation and comparison."""
from __future__ import annotations
from dataclasses import dataclass, fields
from datetime import datetime
from decimal import Decimal
from app.contracts.workspace import WorkspaceId
from app.repositories.cognitive_quality_observations import CognitiveQualityObservationRepository


def _period(since, until):
    for label, value in (("since", since), ("until", until)):
        if value is not None and (not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None):
            raise ValueError(f"{label} must be timezone-aware")
    if since is not None and until is not None and since >= until: raise ValueError("invalid period")
    return since, until


def rate_text(numerator: int, denominator: int) -> str | None:
    if any(type(v) is not int or v < 0 for v in (numerator, denominator)): raise ValueError("invalid rate")
    return None if denominator == 0 else format(Decimal(numerator) / Decimal(denominator), ".6f")


@dataclass(frozen=True, slots=True)
class CognitiveQualityCounts:
    observed_count: int = 0
    verified_success_count: int = 0
    bounded_insufficiency_count: int = 0
    adverse_outcome_count: int = 0
    invalid_evidence_count: int = 0
    terminal_completed_count: int = 0
    terminal_insufficient_count: int = 0
    terminal_failed_count: int = 0
    verification_pass_count: int = 0
    verification_revise_count: int = 0
    verification_insufficient_evidence_count: int = 0
    verification_invalid_cognition_count: int = 0
    revised_turn_count: int = 0
    critic_exhausted_count: int = 0
    confidence_sufficient_count: int = 0
    confidence_limited_count: int = 0
    confidence_insufficient_count: int = 0
    confidence_unknown_count: int = 0
    def __post_init__(self):
        if any(type(getattr(self, f.name)) is not int or getattr(self, f.name) < 0 for f in fields(self)): raise ValueError("invalid counts")
        if self.verified_success_count+self.bounded_insufficiency_count+self.adverse_outcome_count+self.invalid_evidence_count != self.observed_count: raise ValueError("classification totals")
        if self.terminal_completed_count+self.terminal_insufficient_count+self.terminal_failed_count != self.observed_count: raise ValueError("terminal totals")


@dataclass(frozen=True, slots=True)
class CognitiveQualityBreakdown:
    key: str
    counts: CognitiveQualityCounts


@dataclass(frozen=True, slots=True)
class CognitiveQualitySummary:
    workspace_id: WorkspaceId
    since: datetime | None
    until: datetime | None
    counts: CognitiveQualityCounts
    by_experience_cohort: tuple[CognitiveQualityBreakdown, ...]
    by_task_kind: tuple[CognitiveQualityBreakdown, ...]


@dataclass(frozen=True, slots=True)
class CognitiveQualityMetricDelta:
    metric: str
    reference_count: int
    candidate_count: int
    delta_count: int


@dataclass(frozen=True, slots=True)
class CognitiveQualityRateDelta:
    metric: str
    reference_numerator: int
    candidate_numerator: int
    reference_denominator: int
    candidate_denominator: int
    reference_rate: str | None
    candidate_rate: str | None
    delta_rate: str | None


@dataclass(frozen=True, slots=True)
class CognitiveQualityComparison:
    reference: CognitiveQualitySummary
    candidate: CognitiveQualitySummary
    count_deltas: tuple[CognitiveQualityMetricDelta, ...]
    rate_deltas: tuple[CognitiveQualityRateDelta, ...]


class CognitiveQualitySummaryService:
    def __init__(self, repository: CognitiveQualityObservationRepository, *, workspace_id: WorkspaceId):
        if not isinstance(workspace_id, WorkspaceId): raise ValueError("workspace invalid")
        self._repository, self._workspace_id = repository, workspace_id
    @staticmethod
    def _aggregate(records):
        v = {f.name: 0 for f in fields(CognitiveQualityCounts)}
        for r in records:
            v["observed_count"] += 1
            v[f"{r.quality_classification}_count"] += 1
            v[f"terminal_{r.terminal_state}_count"] += 1
            if r.verification_result is not None: v[f"verification_{r.verification_result}_count"] += 1
            if r.revision_count > 0: v["revised_turn_count"] += 1
            if r.critic_exhausted is True: v["critic_exhausted_count"] += 1
            if r.confidence_class is not None: v[f"confidence_{r.confidence_class}_count"] += 1
        return CognitiveQualityCounts(**v)
    def summarize(self, *, since=None, until=None):
        since, until = _period(since, until)
        records = self._repository.list_for_summary(workspace_id=self._workspace_id, since=since, until=until)
        cohorts, tasks = {}, {}
        for r in records:
            cohorts.setdefault(r.experience_cohort, []).append(r)
            tasks.setdefault(r.task_kind or "unknown", []).append(r)
        return CognitiveQualitySummary(self._workspace_id, since, until, self._aggregate(records),
            tuple(CognitiveQualityBreakdown(k,self._aggregate(v)) for k,v in sorted(cohorts.items())),
            tuple(CognitiveQualityBreakdown(k,self._aggregate(v)) for k,v in sorted(tasks.items())))
    def compare(self, *, reference_since, reference_until, candidate_since, candidate_until):
        reference_since, reference_until = _period(reference_since, reference_until)
        candidate_since, candidate_until = _period(candidate_since, candidate_until)
        if None in (reference_since, reference_until, candidate_since, candidate_until): raise ValueError("compare requires closed periods")
        ref = self.summarize(since=reference_since, until=reference_until)
        cand = self.summarize(since=candidate_since, until=candidate_until)
        metrics = ("observed_count","verified_success_count","bounded_insufficiency_count","adverse_outcome_count","invalid_evidence_count","revised_turn_count","critic_exhausted_count")
        cd = tuple(CognitiveQualityMetricDelta(m,getattr(ref.counts,m),getattr(cand.counts,m),getattr(cand.counts,m)-getattr(ref.counts,m)) for m in metrics)
        rd=[]
        for metric, num_name in (("verified_success_rate","verified_success_count"),("bounded_insufficiency_rate","bounded_insufficiency_count"),("adverse_outcome_rate","adverse_outcome_count"),("invalid_evidence_rate","invalid_evidence_count")):
            rn, cn, rden, cden = getattr(ref.counts,num_name), getattr(cand.counts,num_name), ref.counts.observed_count, cand.counts.observed_count
            rr, cr = rate_text(rn,rden), rate_text(cn,cden)
            delta = None if rr is None or cr is None else format(Decimal(cr)-Decimal(rr), ".6f")
            rd.append(CognitiveQualityRateDelta(metric,rn,cn,rden,cden,rr,cr,delta))
        return CognitiveQualityComparison(ref,cand,cd,tuple(rd))
