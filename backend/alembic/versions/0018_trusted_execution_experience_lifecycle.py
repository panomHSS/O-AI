"""Create D187 trusted execution-experience lifecycle.

Revision ID: 0018_trusted_execution_experience_lifecycle
Revises: 0017_execution_experience_review_lifecycle
"""

from alembic import op
import sqlalchemy as sa


revision = "0018_trusted_execution_experience_lifecycle"
down_revision = "0017_execution_experience_review_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trusted_execution_experiences",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("workspace_id", sa.String(16), nullable=False),
        sa.Column("source_review_id", sa.String(36), nullable=False),
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
        sa.Column("source_d186_record_fingerprint", sa.String(64), nullable=False),
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
        sa.Column("promotion_fingerprint", sa.String(64), nullable=False),
        sa.Column("contract_version", sa.String(64), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("current_revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "workspace_id IN ('personal','company')",
            name="ck_trusted_execution_experiences_workspace",
        ),
        sa.CheckConstraint(
            "contract_version='o-ai.governed-execution-experience-trust.v1'",
            name="ck_trusted_execution_experiences_contract",
        ),
        sa.CheckConstraint(
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
        sa.CheckConstraint(
            "target_kind IN ('tool','module')",
            name="ck_trusted_execution_experiences_target",
        ),
        sa.CheckConstraint(
            "effect IN ('none','read')",
            name="ck_trusted_execution_experiences_effect",
        ),
        sa.CheckConstraint(
            "risk_class='R0'",
            name="ck_trusted_execution_experiences_risk",
        ),
        sa.CheckConstraint(
            "source_classification='execution_succeeded' "
            "AND experience_outcome_class='success' "
            "AND experience_lesson_code='authorized_execution_succeeded' "
            "AND review_reason_code='authorized_execution_succeeded'",
            name="ck_trusted_execution_experiences_success_only",
        ),
        sa.CheckConstraint(
            "state IN ('TRUSTED','REVOKED')",
            name="ck_trusted_execution_experiences_state",
        ),
        sa.CheckConstraint(
            "(state='TRUSTED' AND current_revision=1) OR "
            "(state='REVOKED' AND current_revision=2)",
            name="ck_trusted_execution_experiences_state_revision",
        ),
        sa.ForeignKeyConstraint(
            ["source_review_id"],
            ["execution_experience_reviews.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_review_id",
            name="uq_trusted_execution_experiences_source_review",
        ),
        sa.UniqueConstraint(
            "promotion_fingerprint",
            name="uq_trusted_execution_experiences_promotion",
        ),
    )
    op.create_index(
        "ix_trusted_execution_experiences_workspace_state",
        "trusted_execution_experiences",
        ["workspace_id", "state"],
        unique=False,
    )
    op.create_index(
        "ix_trusted_execution_experiences_updated_at",
        "trusted_execution_experiences",
        ["updated_at"],
        unique=False,
    )

    op.create_table(
        "trusted_execution_experience_events",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("trusted_execution_experience_id", sa.String(36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(24), nullable=False),
        sa.Column("from_state", sa.String(16), nullable=True),
        sa.Column("to_state", sa.String(16), nullable=False),
        sa.Column("actor", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "sequence IN (1,2)",
            name="ck_trusted_execution_experience_events_sequence",
        ),
        sa.CheckConstraint(
            "event_type IN ('OWNER_PROMOTED','OWNER_REVOKED')",
            name="ck_trusted_execution_experience_events_type",
        ),
        sa.CheckConstraint(
            "from_state IS NULL OR from_state='TRUSTED'",
            name="ck_trusted_execution_experience_events_from_state",
        ),
        sa.CheckConstraint(
            "to_state IN ('TRUSTED','REVOKED')",
            name="ck_trusted_execution_experience_events_to_state",
        ),
        sa.CheckConstraint(
            "actor='OWNER'",
            name="ck_trusted_execution_experience_events_actor",
        ),
        sa.CheckConstraint(
            "(event_type='OWNER_PROMOTED' AND sequence=1 "
            "AND from_state IS NULL AND to_state='TRUSTED' AND actor='OWNER') OR "
            "(event_type='OWNER_REVOKED' AND sequence=2 "
            "AND from_state='TRUSTED' AND to_state='REVOKED' AND actor='OWNER')",
            name="ck_trusted_execution_experience_events_transition",
        ),
        sa.ForeignKeyConstraint(
            ["trusted_execution_experience_id"],
            ["trusted_execution_experiences.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trusted_execution_experience_id",
            "sequence",
            name="uq_trusted_execution_experience_event_sequence",
        ),
    )
    op.create_index(
        "ix_trusted_execution_experience_events_experience_id",
        "trusted_execution_experience_events",
        ["trusted_execution_experience_id"],
        unique=False,
    )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.execute(
        sa.text("SELECT COUNT(*) FROM trusted_execution_experience_events")
    ).scalar_one():
        raise RuntimeError(
            "Refusing to downgrade D187 while trusted execution experience events exist."
        )
    if connection.execute(
        sa.text("SELECT COUNT(*) FROM trusted_execution_experiences")
    ).scalar_one():
        raise RuntimeError(
            "Refusing to downgrade D187 while trusted execution experiences exist."
        )
    op.drop_index(
        "ix_trusted_execution_experience_events_experience_id",
        table_name="trusted_execution_experience_events",
    )
    op.drop_table("trusted_execution_experience_events")
    op.drop_index(
        "ix_trusted_execution_experiences_updated_at",
        table_name="trusted_execution_experiences",
    )
    op.drop_index(
        "ix_trusted_execution_experiences_workspace_state",
        table_name="trusted_execution_experiences",
    )
    op.drop_table("trusted_execution_experiences")
