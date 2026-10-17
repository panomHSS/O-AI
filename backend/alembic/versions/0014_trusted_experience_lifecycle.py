"""Add D147 owner-controlled Trusted Experience lifecycle.

Revision ID: 0014_trusted_experience_lifecycle
Revises: 0013_context_snapshot_persistence
"""

from alembic import op
import sqlalchemy as sa


revision = "0014_trusted_experience_lifecycle"
down_revision = "0013_context_snapshot_persistence"
branch_labels = None
depends_on = None


def _dialect_name() -> str:
    return op.get_bind().dialect.name


def _create_immutability_triggers() -> None:
    dialect = _dialect_name()
    if dialect == "sqlite":
        op.execute(
            """
            CREATE TRIGGER trg_trusted_experiences_transition_guard
            BEFORE UPDATE ON trusted_experiences
            FOR EACH ROW WHEN
                NEW.id IS NOT OLD.id
                OR NEW.workspace_id IS NOT OLD.workspace_id
                OR NEW.contract_version IS NOT OLD.contract_version
                OR NEW.source_candidate_fingerprint IS NOT OLD.source_candidate_fingerprint
                OR NEW.source_feedback_fingerprint IS NOT OLD.source_feedback_fingerprint
                OR NEW.proposal_fingerprint IS NOT OLD.proposal_fingerprint
                OR NEW.quality_classification IS NOT OLD.quality_classification
                OR NEW.quality_reason_code IS NOT OLD.quality_reason_code
                OR NEW.lesson_code IS NOT OLD.lesson_code
                OR NEW.interaction_intent IS NOT OLD.interaction_intent
                OR NEW.cognitive_intent IS NOT OLD.cognitive_intent
                OR NEW.authoritative_ai_task_kind IS NOT OLD.authoritative_ai_task_kind
                OR NEW.observed_confidence_class IS NOT OLD.observed_confidence_class
                OR NEW.authorized_adapter_id IS NOT OLD.authorized_adapter_id
                OR NEW.authorized_model_id IS NOT OLD.authorized_model_id
                OR NEW.authorized_profile_id IS NOT OLD.authorized_profile_id
                OR NEW.source_revision_count IS NOT OLD.source_revision_count
                OR NEW.created_at IS NOT OLD.created_at
                OR NOT (
                    (OLD.state = 'PENDING_REVIEW'
                     AND NEW.state IN ('TRUSTED', 'REJECTED')
                     AND NEW.current_revision = OLD.current_revision + 1)
                    OR
                    (OLD.state = 'TRUSTED'
                     AND NEW.state = 'REVOKED'
                     AND NEW.current_revision = OLD.current_revision + 1)
                )
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'trusted experience source projection is immutable'
                );
            END
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_trusted_experience_events_immutable_update
            BEFORE UPDATE ON trusted_experience_events
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'trusted experience events are immutable'
                );
            END
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_trusted_experience_events_immutable_delete
            BEFORE DELETE ON trusted_experience_events
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'trusted experience events are immutable'
                );
            END
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_trusted_experiences_no_delete
            BEFORE DELETE ON trusted_experiences
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'trusted experience lifecycle roots are not deletable'
                );
            END
            """
        )
        return

    if dialect == "postgresql":
        op.execute(
            """
            CREATE FUNCTION enforce_trusted_experience_transition()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                IF
                    NEW.id IS DISTINCT FROM OLD.id
                    OR NEW.workspace_id IS DISTINCT FROM OLD.workspace_id
                    OR NEW.contract_version IS DISTINCT FROM OLD.contract_version
                    OR NEW.source_candidate_fingerprint IS DISTINCT FROM OLD.source_candidate_fingerprint
                    OR NEW.source_feedback_fingerprint IS DISTINCT FROM OLD.source_feedback_fingerprint
                    OR NEW.proposal_fingerprint IS DISTINCT FROM OLD.proposal_fingerprint
                    OR NEW.quality_classification IS DISTINCT FROM OLD.quality_classification
                    OR NEW.quality_reason_code IS DISTINCT FROM OLD.quality_reason_code
                    OR NEW.lesson_code IS DISTINCT FROM OLD.lesson_code
                    OR NEW.interaction_intent IS DISTINCT FROM OLD.interaction_intent
                    OR NEW.cognitive_intent IS DISTINCT FROM OLD.cognitive_intent
                    OR NEW.authoritative_ai_task_kind IS DISTINCT FROM OLD.authoritative_ai_task_kind
                    OR NEW.observed_confidence_class IS DISTINCT FROM OLD.observed_confidence_class
                    OR NEW.authorized_adapter_id IS DISTINCT FROM OLD.authorized_adapter_id
                    OR NEW.authorized_model_id IS DISTINCT FROM OLD.authorized_model_id
                    OR NEW.authorized_profile_id IS DISTINCT FROM OLD.authorized_profile_id
                    OR NEW.source_revision_count IS DISTINCT FROM OLD.source_revision_count
                    OR NEW.created_at IS DISTINCT FROM OLD.created_at
                    OR NOT (
                        (OLD.state = 'PENDING_REVIEW'
                         AND NEW.state IN ('TRUSTED', 'REJECTED')
                         AND NEW.current_revision = OLD.current_revision + 1)
                        OR
                        (OLD.state = 'TRUSTED'
                         AND NEW.state = 'REVOKED'
                         AND NEW.current_revision = OLD.current_revision + 1)
                    )
                THEN
                    RAISE EXCEPTION
                        'trusted experience source projection is immutable';
                END IF;
                RETURN NEW;
            END;
            $$;
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_trusted_experiences_transition_guard
            BEFORE UPDATE ON trusted_experiences
            FOR EACH ROW
            EXECUTE FUNCTION enforce_trusted_experience_transition()
            """
        )
        op.execute(
            """
            CREATE FUNCTION reject_trusted_experience_event_mutation()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                RAISE EXCEPTION 'trusted experience events are immutable';
            END;
            $$;
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_trusted_experience_events_immutable_update
            BEFORE UPDATE ON trusted_experience_events
            FOR EACH ROW
            EXECUTE FUNCTION reject_trusted_experience_event_mutation()
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_trusted_experience_events_immutable_delete
            BEFORE DELETE ON trusted_experience_events
            FOR EACH ROW
            EXECUTE FUNCTION reject_trusted_experience_event_mutation()
            """
        )
        op.execute(
            """
            CREATE FUNCTION reject_trusted_experience_root_delete()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                RAISE EXCEPTION 'trusted experience lifecycle roots are not deletable';
            END;
            $$;
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_trusted_experiences_no_delete
            BEFORE DELETE ON trusted_experiences
            FOR EACH ROW
            EXECUTE FUNCTION reject_trusted_experience_root_delete()
            """
        )


def _drop_immutability_triggers() -> None:
    dialect = _dialect_name()
    if dialect == "sqlite":
        for name in (
            "trg_trusted_experiences_no_delete",
            "trg_trusted_experience_events_immutable_delete",
            "trg_trusted_experience_events_immutable_update",
            "trg_trusted_experiences_transition_guard",
        ):
            op.execute(f"DROP TRIGGER IF EXISTS {name}")
        return

    if dialect == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS trg_trusted_experiences_no_delete "
            "ON trusted_experiences"
        )
        op.execute(
            "DROP TRIGGER IF EXISTS trg_trusted_experience_events_immutable_delete "
            "ON trusted_experience_events"
        )
        op.execute(
            "DROP TRIGGER IF EXISTS trg_trusted_experience_events_immutable_update "
            "ON trusted_experience_events"
        )
        op.execute(
            "DROP TRIGGER IF EXISTS trg_trusted_experiences_transition_guard "
            "ON trusted_experiences"
        )
        op.execute(
            "DROP FUNCTION IF EXISTS reject_trusted_experience_root_delete()"
        )
        op.execute(
            "DROP FUNCTION IF EXISTS reject_trusted_experience_event_mutation()"
        )
        op.execute(
            "DROP FUNCTION IF EXISTS enforce_trusted_experience_transition()"
        )


def upgrade() -> None:
    op.create_table(
        "trusted_experiences",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("workspace_id", sa.String(16), nullable=False),
        sa.Column("contract_version", sa.String(16), nullable=False),
        sa.Column("source_candidate_fingerprint", sa.String(64), nullable=False),
        sa.Column("source_feedback_fingerprint", sa.String(64), nullable=False),
        sa.Column("proposal_fingerprint", sa.String(64), nullable=False),
        sa.Column("quality_classification", sa.String(32), nullable=False),
        sa.Column("quality_reason_code", sa.String(32), nullable=False),
        sa.Column("lesson_code", sa.String(32), nullable=False),
        sa.Column("interaction_intent", sa.String(64), nullable=False),
        sa.Column("cognitive_intent", sa.String(64), nullable=False),
        sa.Column("authoritative_ai_task_kind", sa.String(64), nullable=False),
        sa.Column("observed_confidence_class", sa.String(32), nullable=False),
        sa.Column("authorized_adapter_id", sa.String(512), nullable=True),
        sa.Column("authorized_model_id", sa.String(512), nullable=True),
        sa.Column("authorized_profile_id", sa.String(512), nullable=True),
        sa.Column("source_revision_count", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("current_revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "workspace_id IN ('personal', 'company')",
            name="ck_trusted_experiences_workspace",
        ),
        sa.CheckConstraint(
            "contract_version = '1'",
            name="ck_trusted_experiences_contract_version",
        ),
        sa.CheckConstraint(
            "length(source_candidate_fingerprint) = 64 "
            "AND length(source_feedback_fingerprint) = 64 "
            "AND length(proposal_fingerprint) = 64",
            name="ck_trusted_experiences_fingerprints",
        ),
        sa.CheckConstraint(
            "quality_classification = 'verified_success' "
            "AND quality_reason_code = 'verified_success' "
            "AND lesson_code = 'verified_success'",
            name="ck_trusted_experiences_verified_success_only",
        ),
        sa.CheckConstraint(
            "source_revision_count >= 0 AND source_revision_count <= 1",
            name="ck_trusted_experiences_source_revision",
        ),
        sa.CheckConstraint(
            "state IN ('PENDING_REVIEW', 'TRUSTED', 'REJECTED', 'REVOKED')",
            name="ck_trusted_experiences_state",
        ),
        sa.CheckConstraint(
            "(state = 'PENDING_REVIEW' AND current_revision = 1) OR "
            "(state IN ('TRUSTED', 'REJECTED') AND current_revision = 2) OR "
            "(state = 'REVOKED' AND current_revision = 3)",
            name="ck_trusted_experiences_state_revision",
        ),
    )
    op.create_index(
        "ix_trusted_experiences_workspace_state",
        "trusted_experiences",
        ["workspace_id", "state"],
    )
    op.create_index(
        "ix_trusted_experiences_updated_at",
        "trusted_experiences",
        ["updated_at"],
    )

    op.create_table(
        "trusted_experience_events",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("trusted_experience_id", sa.String(36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(16), nullable=False),
        sa.Column("from_state", sa.String(32), nullable=True),
        sa.Column("to_state", sa.String(32), nullable=False),
        sa.Column("actor", sa.String(16), nullable=False),
        sa.Column("decision_comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["trusted_experience_id"],
            ["trusted_experiences.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trusted_experience_id",
            "sequence",
            name="uq_trusted_experience_event_sequence",
        ),
        sa.CheckConstraint(
            "sequence >= 1",
            name="ck_trusted_experience_events_sequence",
        ),
        sa.CheckConstraint(
            "event_type IN ('PROPOSED', 'APPROVED', 'REJECTED', 'REVOKED')",
            name="ck_trusted_experience_events_type",
        ),
        sa.CheckConstraint(
            "from_state IS NULL OR from_state IN "
            "('PENDING_REVIEW', 'TRUSTED', 'REJECTED', 'REVOKED')",
            name="ck_trusted_experience_events_from_state",
        ),
        sa.CheckConstraint(
            "to_state IN ('PENDING_REVIEW', 'TRUSTED', 'REJECTED', 'REVOKED')",
            name="ck_trusted_experience_events_to_state",
        ),
        sa.CheckConstraint(
            "actor IN ('SYSTEM', 'OWNER')",
            name="ck_trusted_experience_events_actor",
        ),
        sa.CheckConstraint(
            "decision_comment IS NULL OR "
            "(length(trim(decision_comment)) > 0 AND length(decision_comment) <= 2000)",
            name="ck_trusted_experience_events_comment",
        ),
        sa.CheckConstraint(
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
    )
    op.create_index(
        "ix_trusted_experience_events_experience_id",
        "trusted_experience_events",
        ["trusted_experience_id"],
    )

    _create_immutability_triggers()


def _assert_downgrade_safe() -> None:
    bind = op.get_bind()
    roots = bind.execute(
        sa.text("SELECT COUNT(*) FROM trusted_experiences")
    ).scalar_one()
    events = bind.execute(
        sa.text("SELECT COUNT(*) FROM trusted_experience_events")
    ).scalar_one()
    if roots or events:
        raise RuntimeError("d147_trusted_experience_downgrade_data")


def downgrade() -> None:
    _assert_downgrade_safe()
    _drop_immutability_triggers()
    op.drop_index(
        "ix_trusted_experience_events_experience_id",
        table_name="trusted_experience_events",
    )
    op.drop_table("trusted_experience_events")
    op.drop_index(
        "ix_trusted_experiences_updated_at",
        table_name="trusted_experiences",
    )
    op.drop_index(
        "ix_trusted_experiences_workspace_state",
        table_name="trusted_experiences",
    )
    op.drop_table("trusted_experiences")
