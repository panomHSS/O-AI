"""Create D186 governed execution experience Owner-review lifecycle.

Revision ID: 0017_execution_experience_review_lifecycle
Revises: 0016_cognitive_quality_observability
"""

from alembic import op
import sqlalchemy as sa


revision = "0017_execution_experience_review_lifecycle"
down_revision = "0016_cognitive_quality_observability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "execution_experience_reviews",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("workspace_id", sa.String(16), nullable=False),
        sa.Column("conversation_id", sa.String(36), nullable=False),
        sa.Column("source_turn_id", sa.String(1024), nullable=False),
        sa.Column("source_artifact_digest", sa.String(64), nullable=False),
        sa.Column("intent_digest", sa.String(64), nullable=False),
        sa.Column("approval_id", sa.String(128), nullable=False),
        sa.Column("execution_request_id", sa.String(1024), nullable=False),
        sa.Column("plan_digest", sa.String(64), nullable=False),
        sa.Column("source_feedback_fingerprint", sa.String(64), nullable=False),
        sa.Column("source_candidate_fingerprint", sa.String(64), nullable=False),
        sa.Column("source_review_fingerprint", sa.String(64), nullable=False),
        sa.Column("target_kind", sa.String(16), nullable=False),
        sa.Column("capability_id", sa.String(1024), nullable=False),
        sa.Column("adapter_id", sa.String(1024), nullable=False),
        sa.Column("operation", sa.String(1024), nullable=False),
        sa.Column("effect", sa.String(32), nullable=False),
        sa.Column("risk_class", sa.String(8), nullable=False),
        sa.Column("source_classification", sa.String(32), nullable=False),
        sa.Column("experience_outcome_class", sa.String(32), nullable=False),
        sa.Column("experience_lesson_code", sa.String(64), nullable=False),
        sa.Column("review_reason_code", sa.String(64), nullable=False),
        sa.Column("record_fingerprint", sa.String(64), nullable=False),
        sa.Column("contract_version", sa.String(64), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("current_revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("workspace_id IN ('personal','company')", name="ck_execution_experience_reviews_workspace"),
        sa.CheckConstraint(
            "contract_version = 'o-ai.governed-execution-experience-owner-review.v1'",
            name="ck_execution_experience_reviews_contract",
        ),
        sa.CheckConstraint(
            "length(source_artifact_digest)=64 "
            "AND length(intent_digest)=64 "
            "AND length(plan_digest)=64 "
            "AND length(source_feedback_fingerprint)=64 "
            "AND length(source_candidate_fingerprint)=64 "
            "AND length(source_review_fingerprint)=64 "
            "AND length(record_fingerprint)=64",
            name="ck_execution_experience_reviews_fingerprints",
        ),
        sa.CheckConstraint("target_kind IN ('tool','module')", name="ck_execution_experience_reviews_target"),
        sa.CheckConstraint("effect IN ('none','read')", name="ck_execution_experience_reviews_effect"),
        sa.CheckConstraint("risk_class='R0'", name="ck_execution_experience_reviews_risk"),
        sa.CheckConstraint(
            "source_classification='execution_succeeded' "
            "AND experience_outcome_class='success' "
            "AND experience_lesson_code='authorized_execution_succeeded' "
            "AND review_reason_code='authorized_execution_succeeded'",
            name="ck_execution_experience_reviews_success_only",
        ),
        sa.CheckConstraint(
            "state IN ('PENDING_REVIEW','REVIEW_ACCEPTED','REVIEW_REJECTED')",
            name="ck_execution_experience_reviews_state",
        ),
        sa.CheckConstraint(
            "(state='PENDING_REVIEW' AND current_revision=1) OR "
            "(state IN ('REVIEW_ACCEPTED','REVIEW_REJECTED') AND current_revision=2)",
            name="ck_execution_experience_reviews_state_revision",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_review_fingerprint", name="uq_execution_experience_reviews_source_review"),
        sa.UniqueConstraint("record_fingerprint", name="uq_execution_experience_reviews_record_fingerprint"),
        sa.UniqueConstraint("workspace_id", "approval_id", name="uq_execution_experience_reviews_workspace_approval"),
    )
    op.create_index(
        "ix_execution_experience_reviews_workspace_state",
        "execution_experience_reviews",
        ["workspace_id", "state"],
        unique=False,
    )
    op.create_index(
        "ix_execution_experience_reviews_updated_at",
        "execution_experience_reviews",
        ["updated_at"],
        unique=False,
    )

    op.create_table(
        "execution_experience_review_events",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("execution_experience_review_id", sa.String(36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(24), nullable=False),
        sa.Column("from_state", sa.String(32), nullable=True),
        sa.Column("to_state", sa.String(32), nullable=False),
        sa.Column("actor", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("sequence IN (1,2)", name="ck_execution_experience_review_events_sequence"),
        sa.CheckConstraint(
            "event_type IN ('PROPOSED','OWNER_ACCEPTED','OWNER_REJECTED')",
            name="ck_execution_experience_review_events_type",
        ),
        sa.CheckConstraint(
            "from_state IS NULL OR from_state='PENDING_REVIEW'",
            name="ck_execution_experience_review_events_from_state",
        ),
        sa.CheckConstraint(
            "to_state IN ('PENDING_REVIEW','REVIEW_ACCEPTED','REVIEW_REJECTED')",
            name="ck_execution_experience_review_events_to_state",
        ),
        sa.CheckConstraint("actor IN ('SYSTEM','OWNER')", name="ck_execution_experience_review_events_actor"),
        sa.CheckConstraint(
            "(event_type='PROPOSED' AND sequence=1 "
            "AND from_state IS NULL AND to_state='PENDING_REVIEW' AND actor='SYSTEM') OR "
            "(event_type='OWNER_ACCEPTED' AND sequence=2 "
            "AND from_state='PENDING_REVIEW' AND to_state='REVIEW_ACCEPTED' AND actor='OWNER') OR "
            "(event_type='OWNER_REJECTED' AND sequence=2 "
            "AND from_state='PENDING_REVIEW' AND to_state='REVIEW_REJECTED' AND actor='OWNER')",
            name="ck_execution_experience_review_events_transition",
        ),
        sa.ForeignKeyConstraint(
            ["execution_experience_review_id"],
            ["execution_experience_reviews.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "execution_experience_review_id",
            "sequence",
            name="uq_execution_experience_review_event_sequence",
        ),
    )
    op.create_index(
        "ix_execution_experience_review_events_review_id",
        "execution_experience_review_events",
        ["execution_experience_review_id"],
        unique=False,
    )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.execute(sa.text("SELECT COUNT(*) FROM execution_experience_review_events")).scalar_one():
        raise RuntimeError("Refusing to downgrade D186 while execution review events exist.")
    if connection.execute(sa.text("SELECT COUNT(*) FROM execution_experience_reviews")).scalar_one():
        raise RuntimeError("Refusing to downgrade D186 while execution review records exist.")
    op.drop_index(
        "ix_execution_experience_review_events_review_id",
        table_name="execution_experience_review_events",
    )
    op.drop_table("execution_experience_review_events")
    op.drop_index(
        "ix_execution_experience_reviews_updated_at",
        table_name="execution_experience_reviews",
    )
    op.drop_index(
        "ix_execution_experience_reviews_workspace_state",
        table_name="execution_experience_reviews",
    )
    op.drop_table("execution_experience_reviews")
