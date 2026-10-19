"""Persistence boundary for D156 cognitive quality observations."""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.contracts.cognitive_quality_observability import CognitiveQualityObservation
from app.contracts.workspace import WorkspaceId
from app.models.cognitive_quality_observation import CognitiveQualityObservationRecord


class CognitiveQualityObservationRepository:
    def __init__(self, session: Session) -> None: self._session = session
    def append(self, o: CognitiveQualityObservation) -> CognitiveQualityObservationRecord:
        if not isinstance(o, CognitiveQualityObservation): raise TypeError("observation invalid")
        r = CognitiveQualityObservationRecord(
            contract_version=o.contract_version, turn_digest=o.turn_digest, workspace_id=o.workspace_id.value,
            terminal_state=o.terminal_state.value, interaction_intent=o.interaction_intent, cognitive_intent=o.cognitive_intent,
            task_kind=o.authoritative_ai_task_kind.value if o.authoritative_ai_task_kind else None,
            quality_classification=o.quality_classification, quality_reason_code=o.quality_reason_code,
            verification_result=o.verification_result, publication_disposition=o.publication_disposition,
            critic_exhausted=o.critic_exhausted, revision_count=o.revision_count, confidence_class=o.confidence_class,
            experience_cohort=o.experience_cohort, adapter_id=o.adapter_id, model_id=o.model_id, profile_id=o.profile_id,
            source_candidate_fingerprint=o.source_candidate_fingerprint, source_feedback_fingerprint=o.source_feedback_fingerprint,
            projection_fingerprint=o.projection_fingerprint, occurred_at=o.occurred_at,
        )
        self._session.add(r); self._session.flush(); return r
    def get_by_turn_digest(self, turn_digest: str):
        if type(turn_digest) is not str or len(turn_digest) != 64: raise ValueError("turn_digest invalid")
        return self._session.scalar(select(CognitiveQualityObservationRecord).where(CognitiveQualityObservationRecord.turn_digest == turn_digest))
    def list_for_summary(self, *, workspace_id: WorkspaceId, since: datetime | None = None, until: datetime | None = None):
        if not isinstance(workspace_id, WorkspaceId): raise ValueError("workspace invalid")
        q = select(CognitiveQualityObservationRecord).where(CognitiveQualityObservationRecord.workspace_id == workspace_id.value)
        if since is not None: q = q.where(CognitiveQualityObservationRecord.occurred_at >= since)
        if until is not None: q = q.where(CognitiveQualityObservationRecord.occurred_at < until)
        q = q.order_by(CognitiveQualityObservationRecord.occurred_at.asc(), CognitiveQualityObservationRecord.id.asc())
        return list(self._session.scalars(q).all())
