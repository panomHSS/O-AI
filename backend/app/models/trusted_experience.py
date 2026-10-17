from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class TrustedExperienceRecord(Base):
    """D147 durable owner-review lifecycle root; never learning authority."""

    __tablename__ = "trusted_experiences"
    __table_args__ = (
        CheckConstraint(
            "workspace_id IN ('personal', 'company')",
            name="ck_trusted_experiences_workspace",
        ),
        CheckConstraint(
            "contract_version = '1'",
            name="ck_trusted_experiences_contract_version",
        ),
        CheckConstraint(
            "length(source_candidate_fingerprint) = 64 "
            "AND length(source_feedback_fingerprint) = 64 "
            "AND length(proposal_fingerprint) = 64",
            name="ck_trusted_experiences_fingerprints",
        ),
        CheckConstraint(
            "quality_classification = 'verified_success' "
            "AND quality_reason_code = 'verified_success' "
            "AND lesson_code = 'verified_success'",
            name="ck_trusted_experiences_verified_success_only",
        ),
        CheckConstraint(
            "source_revision_count >= 0 AND source_revision_count <= 1",
            name="ck_trusted_experiences_source_revision",
        ),
        CheckConstraint(
            "state IN ('PENDING_REVIEW', 'TRUSTED', 'REJECTED', 'REVOKED')",
            name="ck_trusted_experiences_state",
        ),
        CheckConstraint(
            "(state = 'PENDING_REVIEW' AND current_revision = 1) OR "
            "(state IN ('TRUSTED', 'REJECTED') AND current_revision = 2) OR "
            "(state = 'REVOKED' AND current_revision = 3)",
            name="ck_trusted_experiences_state_revision",
        ),
        Index(
            "ix_trusted_experiences_workspace_state",
            "workspace_id",
            "state",
        ),
        Index(
            "ix_trusted_experiences_updated_at",
            "updated_at",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    workspace_id: Mapped[str] = mapped_column(String(16), nullable=False)
    contract_version: Mapped[str] = mapped_column(
        String(16), nullable=False, default="1"
    )
    source_candidate_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    source_feedback_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    proposal_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    quality_classification: Mapped[str] = mapped_column(String(32), nullable=False)
    quality_reason_code: Mapped[str] = mapped_column(String(32), nullable=False)
    lesson_code: Mapped[str] = mapped_column(String(32), nullable=False)
    interaction_intent: Mapped[str] = mapped_column(String(64), nullable=False)
    cognitive_intent: Mapped[str] = mapped_column(String(64), nullable=False)
    authoritative_ai_task_kind: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    observed_confidence_class: Mapped[str] = mapped_column(
        String(32), nullable=False
    )
    authorized_adapter_id: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    authorized_model_id: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    authorized_profile_id: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    source_revision_count: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PENDING_REVIEW"
    )
    current_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class TrustedExperienceEventRecord(Base):
    """Append-only D147 lifecycle event evidence."""

    __tablename__ = "trusted_experience_events"
    __table_args__ = (
        CheckConstraint("sequence >= 1", name="ck_trusted_experience_events_sequence"),
        CheckConstraint(
            "event_type IN ('PROPOSED', 'APPROVED', 'REJECTED', 'REVOKED')",
            name="ck_trusted_experience_events_type",
        ),
        CheckConstraint(
            "from_state IS NULL OR from_state IN "
            "('PENDING_REVIEW', 'TRUSTED', 'REJECTED', 'REVOKED')",
            name="ck_trusted_experience_events_from_state",
        ),
        CheckConstraint(
            "to_state IN ('PENDING_REVIEW', 'TRUSTED', 'REJECTED', 'REVOKED')",
            name="ck_trusted_experience_events_to_state",
        ),
        CheckConstraint(
            "actor IN ('SYSTEM', 'OWNER')",
            name="ck_trusted_experience_events_actor",
        ),
        CheckConstraint(
            "decision_comment IS NULL OR "
            "(length(trim(decision_comment)) > 0 AND length(decision_comment) <= 2000)",
            name="ck_trusted_experience_events_comment",
        ),
        CheckConstraint(
            "(event_type = 'PROPOSED' AND sequence = 1 "
            "AND from_state IS NULL AND to_state = 'PENDING_REVIEW' "
            "AND actor = 'SYSTEM' AND decision_comment IS NULL) OR "
            "(event_type = 'APPROVED' AND from_state = 'PENDING_REVIEW' "
            "AND to_state = 'TRUSTED' AND actor = 'OWNER' "
            "AND decision_comment IS NOT NULL) OR "
            "(event_type = 'REJECTED' AND from_state = 'PENDING_REVIEW' "
            "AND to_state = 'REJECTED' AND actor = 'OWNER' "
            "AND decision_comment IS NOT NULL) OR "
            "(event_type = 'REVOKED' AND from_state = 'TRUSTED' "
            "AND to_state = 'REVOKED' AND actor = 'OWNER' "
            "AND decision_comment IS NOT NULL)",
            name="ck_trusted_experience_events_transition",
        ),
        UniqueConstraint(
            "trusted_experience_id",
            "sequence",
            name="uq_trusted_experience_event_sequence",
        ),
        Index(
            "ix_trusted_experience_events_experience_id",
            "trusted_experience_id",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    trusted_experience_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("trusted_experiences.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(16), nullable=False)
    from_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_state: Mapped[str] = mapped_column(String(32), nullable=False)
    actor: Mapped[str] = mapped_column(String(16), nullable=False)
    decision_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
