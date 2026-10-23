from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class ExecutionExperienceReviewRecord(Base):
    """D186 durable Owner-review record; explicitly not a trusted experience."""

    __tablename__ = "execution_experience_reviews"
    __table_args__ = (
        CheckConstraint("workspace_id IN ('personal', 'company')", name="ck_execution_experience_reviews_workspace"),
        CheckConstraint(
            "contract_version = 'o-ai.governed-execution-experience-owner-review.v1'",
            name="ck_execution_experience_reviews_contract",
        ),
        CheckConstraint(
            "length(source_artifact_digest)=64 "
            "AND length(intent_digest)=64 "
            "AND length(plan_digest)=64 "
            "AND length(source_feedback_fingerprint)=64 "
            "AND length(source_candidate_fingerprint)=64 "
            "AND length(source_review_fingerprint)=64 "
            "AND length(record_fingerprint)=64",
            name="ck_execution_experience_reviews_fingerprints",
        ),
        CheckConstraint("target_kind IN ('tool','module')", name="ck_execution_experience_reviews_target"),
        CheckConstraint("effect IN ('none','read')", name="ck_execution_experience_reviews_effect"),
        CheckConstraint("risk_class = 'R0'", name="ck_execution_experience_reviews_risk"),
        CheckConstraint(
            "source_classification = 'execution_succeeded' "
            "AND experience_outcome_class = 'success' "
            "AND experience_lesson_code = 'authorized_execution_succeeded' "
            "AND review_reason_code = 'authorized_execution_succeeded'",
            name="ck_execution_experience_reviews_success_only",
        ),
        CheckConstraint(
            "state IN ('PENDING_REVIEW','REVIEW_ACCEPTED','REVIEW_REJECTED')",
            name="ck_execution_experience_reviews_state",
        ),
        CheckConstraint(
            "(state='PENDING_REVIEW' AND current_revision=1) OR "
            "(state IN ('REVIEW_ACCEPTED','REVIEW_REJECTED') AND current_revision=2)",
            name="ck_execution_experience_reviews_state_revision",
        ),
        UniqueConstraint("source_review_fingerprint", name="uq_execution_experience_reviews_source_review"),
        UniqueConstraint("record_fingerprint", name="uq_execution_experience_reviews_record_fingerprint"),
        UniqueConstraint("workspace_id", "approval_id", name="uq_execution_experience_reviews_workspace_approval"),
        Index("ix_execution_experience_reviews_workspace_state", "workspace_id", "state"),
        Index("ix_execution_experience_reviews_updated_at", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workspace_id: Mapped[str] = mapped_column(String(16), nullable=False)
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source_turn_id: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_artifact_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    intent_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    approval_id: Mapped[str] = mapped_column(String(128), nullable=False)
    execution_request_id: Mapped[str] = mapped_column(String(1024), nullable=False)
    plan_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    source_feedback_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    source_candidate_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    source_review_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    target_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    capability_id: Mapped[str] = mapped_column(String(1024), nullable=False)
    adapter_id: Mapped[str] = mapped_column(String(1024), nullable=False)
    operation: Mapped[str] = mapped_column(String(1024), nullable=False)
    effect: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_class: Mapped[str] = mapped_column(String(8), nullable=False)
    source_classification: Mapped[str] = mapped_column(String(32), nullable=False)
    experience_outcome_class: Mapped[str] = mapped_column(String(32), nullable=False)
    experience_lesson_code: Mapped[str] = mapped_column(String(64), nullable=False)
    review_reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    record_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING_REVIEW")
    current_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class ExecutionExperienceReviewEventRecord(Base):
    """Append-only D186 lifecycle transition evidence."""

    __tablename__ = "execution_experience_review_events"
    __table_args__ = (
        CheckConstraint("sequence IN (1,2)", name="ck_execution_experience_review_events_sequence"),
        CheckConstraint(
            "event_type IN ('PROPOSED','OWNER_ACCEPTED','OWNER_REJECTED')",
            name="ck_execution_experience_review_events_type",
        ),
        CheckConstraint(
            "from_state IS NULL OR from_state = 'PENDING_REVIEW'",
            name="ck_execution_experience_review_events_from_state",
        ),
        CheckConstraint(
            "to_state IN ('PENDING_REVIEW','REVIEW_ACCEPTED','REVIEW_REJECTED')",
            name="ck_execution_experience_review_events_to_state",
        ),
        CheckConstraint("actor IN ('SYSTEM','OWNER')", name="ck_execution_experience_review_events_actor"),
        CheckConstraint(
            "(event_type='PROPOSED' AND sequence=1 "
            "AND from_state IS NULL AND to_state='PENDING_REVIEW' AND actor='SYSTEM') OR "
            "(event_type='OWNER_ACCEPTED' AND sequence=2 "
            "AND from_state='PENDING_REVIEW' AND to_state='REVIEW_ACCEPTED' AND actor='OWNER') OR "
            "(event_type='OWNER_REJECTED' AND sequence=2 "
            "AND from_state='PENDING_REVIEW' AND to_state='REVIEW_REJECTED' AND actor='OWNER')",
            name="ck_execution_experience_review_events_transition",
        ),
        UniqueConstraint(
            "execution_experience_review_id",
            "sequence",
            name="uq_execution_experience_review_event_sequence",
        ),
        Index(
            "ix_execution_experience_review_events_review_id",
            "execution_experience_review_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    execution_experience_review_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("execution_experience_reviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(24), nullable=False)
    from_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_state: Mapped[str] = mapped_column(String(32), nullable=False)
    actor: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
