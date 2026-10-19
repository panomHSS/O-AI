"""Create append-only D156 longitudinal cognitive quality ledger.

Revision ID: 0016_cognitive_quality_observability
Revises: 0015_ai_usage_observability
"""
from alembic import op
import sqlalchemy as sa

revision="0016_cognitive_quality_observability"
down_revision="0015_ai_usage_observability"
branch_labels=None
depends_on=None


def _dialect(): return op.get_bind().dialect.name

def _create_triggers():
    if _dialect()=="sqlite":
        op.execute("CREATE TRIGGER trg_cognitive_quality_observations_immutable_update BEFORE UPDATE ON cognitive_quality_observations BEGIN SELECT RAISE(ABORT, 'cognitive quality observations are append-only'); END")
        op.execute("CREATE TRIGGER trg_cognitive_quality_observations_immutable_delete BEFORE DELETE ON cognitive_quality_observations BEGIN SELECT RAISE(ABORT, 'cognitive quality observations are append-only'); END")
    elif _dialect()=="postgresql":
        op.execute("""CREATE FUNCTION reject_cognitive_quality_observation_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'cognitive quality observations are append-only'; END; $$;""")
        op.execute("CREATE TRIGGER trg_cognitive_quality_observations_immutable_update BEFORE UPDATE ON cognitive_quality_observations FOR EACH ROW EXECUTE FUNCTION reject_cognitive_quality_observation_mutation()")
        op.execute("CREATE TRIGGER trg_cognitive_quality_observations_immutable_delete BEFORE DELETE ON cognitive_quality_observations FOR EACH ROW EXECUTE FUNCTION reject_cognitive_quality_observation_mutation()")


def _drop_triggers():
    if _dialect()=="sqlite":
        op.execute("DROP TRIGGER IF EXISTS trg_cognitive_quality_observations_immutable_delete")
        op.execute("DROP TRIGGER IF EXISTS trg_cognitive_quality_observations_immutable_update")
    elif _dialect()=="postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_cognitive_quality_observations_immutable_delete ON cognitive_quality_observations")
        op.execute("DROP TRIGGER IF EXISTS trg_cognitive_quality_observations_immutable_update ON cognitive_quality_observations")
        op.execute("DROP FUNCTION IF EXISTS reject_cognitive_quality_observation_mutation()")


def upgrade():
    op.create_table("cognitive_quality_observations",
        sa.Column("id",sa.Integer(),autoincrement=True,nullable=False),
        sa.Column("contract_version",sa.String(16),nullable=False), sa.Column("turn_digest",sa.String(64),nullable=False),
        sa.Column("workspace_id",sa.String(16),nullable=False), sa.Column("terminal_state",sa.String(32),nullable=False),
        sa.Column("interaction_intent",sa.String(64),nullable=True), sa.Column("cognitive_intent",sa.String(64),nullable=True),
        sa.Column("task_kind",sa.String(64),nullable=True), sa.Column("quality_classification",sa.String(32),nullable=False),
        sa.Column("quality_reason_code",sa.String(64),nullable=False), sa.Column("verification_result",sa.String(32),nullable=True),
        sa.Column("publication_disposition",sa.String(32),nullable=True), sa.Column("critic_exhausted",sa.Boolean(),nullable=True),
        sa.Column("revision_count",sa.Integer(),nullable=False), sa.Column("confidence_class",sa.String(32),nullable=True),
        sa.Column("experience_cohort",sa.String(32),nullable=False), sa.Column("adapter_id",sa.Text(),nullable=True),
        sa.Column("model_id",sa.Text(),nullable=True), sa.Column("profile_id",sa.Text(),nullable=True),
        sa.Column("source_candidate_fingerprint",sa.String(64),nullable=True), sa.Column("source_feedback_fingerprint",sa.String(64),nullable=True),
        sa.Column("projection_fingerprint",sa.String(64),nullable=False), sa.Column("occurred_at",sa.DateTime(timezone=True),nullable=False),
        sa.CheckConstraint("contract_version = '1'",name="ck_cognitive_quality_contract_version"),
        sa.CheckConstraint("length(turn_digest)=64 AND length(projection_fingerprint)=64",name="ck_cognitive_quality_digest_lengths"),
        sa.CheckConstraint("workspace_id IN ('personal','company')",name="ck_cognitive_quality_workspace"),
        sa.CheckConstraint("terminal_state IN ('completed','insufficient','failed')",name="ck_cognitive_quality_terminal_state"),
        sa.CheckConstraint("quality_classification IN ('verified_success','bounded_insufficiency','adverse_outcome','invalid_evidence')",name="ck_cognitive_quality_classification"),
        sa.CheckConstraint("quality_reason_code IN ('verified_success','bounded_insufficiency','critic_exhausted','invalid_cognition','terminal_failure','invalid_experience_candidate')",name="ck_cognitive_quality_reason"),
        sa.CheckConstraint("verification_result IS NULL OR verification_result IN ('pass','revise','insufficient_evidence','invalid_cognition')",name="ck_cognitive_quality_verification"),
        sa.CheckConstraint("publication_disposition IS NULL OR publication_disposition IN ('eligible','bounded_insufficiency_only','revision_required','blocked')",name="ck_cognitive_quality_publication"),
        sa.CheckConstraint("revision_count >= 0",name="ck_cognitive_quality_revision"),
        sa.CheckConstraint("confidence_class IS NULL OR confidence_class IN ('sufficient','limited','insufficient','unknown')",name="ck_cognitive_quality_confidence"),
        sa.CheckConstraint("experience_cohort IN ('verification_active','reasoning_active','projected','restricted','no_evidence','unavailable','absent','not_evaluated')",name="ck_cognitive_quality_cohort"),
        sa.CheckConstraint("(source_candidate_fingerprint IS NULL OR length(source_candidate_fingerprint)=64) AND (source_feedback_fingerprint IS NULL OR length(source_feedback_fingerprint)=64)",name="ck_cognitive_quality_source_digests"),
        sa.PrimaryKeyConstraint("id"))
    op.create_index("uq_cognitive_quality_turn_digest","cognitive_quality_observations",["turn_digest"],unique=True)
    op.create_index("ix_cognitive_quality_workspace_occurred_at","cognitive_quality_observations",["workspace_id","occurred_at"],unique=False)
    op.create_index("ix_cognitive_quality_workspace_cohort_occurred_at","cognitive_quality_observations",["workspace_id","experience_cohort","occurred_at"],unique=False)
    op.create_index("ix_cognitive_quality_workspace_task_occurred_at","cognitive_quality_observations",["workspace_id","task_kind","occurred_at"],unique=False)
    _create_triggers()


def downgrade():
    if op.get_bind().execute(sa.text("SELECT COUNT(*) FROM cognitive_quality_observations")).scalar_one():
        raise RuntimeError("Refusing to downgrade D156 while cognitive quality evidence exists.")
    _drop_triggers()
    for name in ("ix_cognitive_quality_workspace_task_occurred_at","ix_cognitive_quality_workspace_cohort_occurred_at","ix_cognitive_quality_workspace_occurred_at","uq_cognitive_quality_turn_digest"):
        op.drop_index(name,table_name="cognitive_quality_observations")
    op.drop_table("cognitive_quality_observations")
