from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class TrustedExecutionExperienceRecord(Base):
    """D187 explicit Owner-promoted execution experience; advisory evidence only."""

    __tablename__ = "trusted_execution_experiences"
    __table_args__ = (
        CheckConstraint(
            "workspace_id IN ('personal','company')",
            name="ck_trusted_execution_experiences_workspace",
        ),
        CheckConstraint(
            "contract_version='o-ai.governed-execution-experience-trust.v1'",
            name="ck_trusted_execution_experiences_contract",
        ),
        CheckConstraint(
            "length(source_artifact_digest)=64 "
            "AND length(intent_digest)=64 "
            "AND length(plan_digest)=64 "
            "AND length(source_feedback_fingerprint)=64 "
            "AND length(source_candidate_fingerprint)=64 "
            "AND length(source_review_fingerprint)=64 "
            "AND length(source_d186_record_fingerprint)=64 "
            "AND length(promotion_fingerprint)=64",
            name="ck_trusted_execution_experiences_fingerprints",
        ),
        CheckConstraint(
            "target_kind IN ('tool','module')",
            name="ck_trusted_execution_experiences_target",
        ),
        CheckConstraint(
            "effect IN ('none','read')",
            name="ck_trusted_execution_experiences_effect",
        ),
        CheckConstraint(
            "risk_class='R0'",
            name="ck_trusted_execution_experiences_risk",
        ),
        CheckConstraint(
            "source_classification='execution_succeeded' "
            "AND experience_outcome_class='success' "
            "AND experience_lesson_code='authorized_execution_succeeded' "
            "AND review_reason_code='authorized_execution_succeeded'",
            name="ck_trusted_execution_experiences_success_only",
        ),
        CheckConstraint(
            "state IN ('TRUSTED','REVOKED')",
            name="ck_trusted_execution_experiences_state",
        ),
        CheckConstraint(
            "(state='TRUSTED' AND current_revision=1) OR "
            "(state='REVOKED' AND current_revision=2)",
            name="ck_trusted_execution_experiences_state_revision",
        ),
        UniqueConstraint(
            "source_review_id",
            name="uq_trusted_execution_experiences_source_review",
        ),
        UniqueConstraint(
            "promotion_fingerprint",
            name="uq_trusted_execution_experiences_promotion",
        ),
        Index(
            "ix_trusted_execution_experiences_workspace_state",
            "workspace_id",
            "state",
        ),
        Index(
            "ix_trusted_execution_experiences_updated_at",
            "updated_at",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    workspace_id: Mapped[str] = mapped_column(String(16), nullable=False)
    source_review_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("execution_experience_reviews.id", ondelete="RESTRICT"),
        nullable=False,
    )
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
    source_d186_record_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
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
    promotion_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="TRUSTED")
    current_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class TrustedExecutionExperienceEventRecord(Base):
    """Append-only D187 explicit Owner trust lifecycle evidence."""

    __tablename__ = "trusted_execution_experience_events"
    __table_args__ = (
        CheckConstraint(
            "sequence IN (1,2)",
            name="ck_trusted_execution_experience_events_sequence",
        ),
        CheckConstraint(
            "event_type IN ('OWNER_PROMOTED','OWNER_REVOKED')",
            name="ck_trusted_execution_experience_events_type",
        ),
        CheckConstraint(
            "from_state IS NULL OR from_state='TRUSTED'",
            name="ck_trusted_execution_experience_events_from_state",
        ),
        CheckConstraint(
            "to_state IN ('TRUSTED','REVOKED')",
            name="ck_trusted_execution_experience_events_to_state",
        ),
        CheckConstraint(
            "actor='OWNER'",
            name="ck_trusted_execution_experience_events_actor",
        ),
        CheckConstraint(
            "(event_type='OWNER_PROMOTED' AND sequence=1 "
            "AND from_state IS NULL AND to_state='TRUSTED' AND actor='OWNER') OR "
            "(event_type='OWNER_REVOKED' AND sequence=2 "
            "AND from_state='TRUSTED' AND to_state='REVOKED' AND actor='OWNER')",
            name="ck_trusted_execution_experience_events_transition",
        ),
        UniqueConstraint(
            "trusted_execution_experience_id",
            "sequence",
            name="uq_trusted_execution_experience_event_sequence",
        ),
        Index(
            "ix_trusted_execution_experience_events_experience_id",
            "trusted_execution_experience_id",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    trusted_execution_experience_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("trusted_execution_experiences.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(24), nullable=False)
    from_state: Mapped[str | None] = mapped_column(String(16), nullable=True)
    to_state: Mapped[str] = mapped_column(String(16), nullable=False)
    actor: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
