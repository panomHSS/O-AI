"""D156 append-only longitudinal cognitive quality ledger model."""
from datetime import datetime
from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class CognitiveQualityObservationRecord(Base):
    __tablename__ = "cognitive_quality_observations"
    __table_args__ = (
        CheckConstraint("contract_version = '1'", name="ck_cognitive_quality_contract_version"),
        CheckConstraint("length(turn_digest)=64 AND length(projection_fingerprint)=64", name="ck_cognitive_quality_digest_lengths"),
        CheckConstraint("workspace_id IN ('personal','company')", name="ck_cognitive_quality_workspace"),
        CheckConstraint("terminal_state IN ('completed','insufficient','failed')", name="ck_cognitive_quality_terminal_state"),
        CheckConstraint("quality_classification IN ('verified_success','bounded_insufficiency','adverse_outcome','invalid_evidence')", name="ck_cognitive_quality_classification"),
        CheckConstraint("quality_reason_code IN ('verified_success','bounded_insufficiency','critic_exhausted','invalid_cognition','terminal_failure','invalid_experience_candidate')", name="ck_cognitive_quality_reason"),
        CheckConstraint("verification_result IS NULL OR verification_result IN ('pass','revise','insufficient_evidence','invalid_cognition')", name="ck_cognitive_quality_verification"),
        CheckConstraint("publication_disposition IS NULL OR publication_disposition IN ('eligible','bounded_insufficiency_only','revision_required','blocked')", name="ck_cognitive_quality_publication"),
        CheckConstraint("revision_count >= 0", name="ck_cognitive_quality_revision"),
        CheckConstraint("confidence_class IS NULL OR confidence_class IN ('sufficient','limited','insufficient','unknown')", name="ck_cognitive_quality_confidence"),
        CheckConstraint("experience_cohort IN ('verification_active','reasoning_active','projected','restricted','no_evidence','unavailable','absent','not_evaluated')", name="ck_cognitive_quality_cohort"),
        CheckConstraint("(source_candidate_fingerprint IS NULL OR length(source_candidate_fingerprint)=64) AND (source_feedback_fingerprint IS NULL OR length(source_feedback_fingerprint)=64)", name="ck_cognitive_quality_source_digests"),
        Index("uq_cognitive_quality_turn_digest", "turn_digest", unique=True),
        Index("ix_cognitive_quality_workspace_occurred_at", "workspace_id", "occurred_at"),
        Index("ix_cognitive_quality_workspace_cohort_occurred_at", "workspace_id", "experience_cohort", "occurred_at"),
        Index("ix_cognitive_quality_workspace_task_occurred_at", "workspace_id", "task_kind", "occurred_at"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_version: Mapped[str] = mapped_column(String(16), nullable=False)
    turn_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(16), nullable=False)
    terminal_state: Mapped[str] = mapped_column(String(32), nullable=False)
    interaction_intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cognitive_intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    task_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    quality_classification: Mapped[str] = mapped_column(String(32), nullable=False)
    quality_reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    verification_result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    publication_disposition: Mapped[str | None] = mapped_column(String(32), nullable=True)
    critic_exhausted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    revision_count: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence_class: Mapped[str | None] = mapped_column(String(32), nullable=True)
    experience_cohort: Mapped[str] = mapped_column(String(32), nullable=False)
    adapter_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_candidate_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_feedback_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    projection_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
