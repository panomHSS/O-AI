"""Create append-only D155 AI usage observability ledger.

Revision ID: 0015_ai_usage_observability
Revises: 0014_trusted_experience_lifecycle
"""

from alembic import op
import sqlalchemy as sa


revision = "0015_ai_usage_observability"
down_revision = "0014_trusted_experience_lifecycle"
branch_labels = None
depends_on = None


def _dialect_name() -> str:
    return op.get_bind().dialect.name


def _create_immutability_triggers() -> None:
    dialect = _dialect_name()
    if dialect == "sqlite":
        op.execute(
            "CREATE TRIGGER trg_ai_usage_events_immutable_update "
            "BEFORE UPDATE ON ai_usage_events BEGIN "
            "SELECT RAISE(ABORT, 'ai_usage_events are append-only'); END"
        )
        op.execute(
            "CREATE TRIGGER trg_ai_usage_events_immutable_delete "
            "BEFORE DELETE ON ai_usage_events BEGIN "
            "SELECT RAISE(ABORT, 'ai_usage_events are append-only'); END"
        )
        return

    if dialect == "postgresql":
        op.execute(
            """
            CREATE FUNCTION reject_ai_usage_event_mutation()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                RAISE EXCEPTION 'ai_usage_events are append-only';
            END;
            $$;
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_ai_usage_events_immutable_update
            BEFORE UPDATE ON ai_usage_events
            FOR EACH ROW
            EXECUTE FUNCTION reject_ai_usage_event_mutation()
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_ai_usage_events_immutable_delete
            BEFORE DELETE ON ai_usage_events
            FOR EACH ROW
            EXECUTE FUNCTION reject_ai_usage_event_mutation()
            """
        )


def _drop_immutability_triggers() -> None:
    dialect = _dialect_name()
    if dialect == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS trg_ai_usage_events_immutable_delete")
        op.execute("DROP TRIGGER IF EXISTS trg_ai_usage_events_immutable_update")
        return

    if dialect == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS trg_ai_usage_events_immutable_delete "
            "ON ai_usage_events"
        )
        op.execute(
            "DROP TRIGGER IF EXISTS trg_ai_usage_events_immutable_update "
            "ON ai_usage_events"
        )
        op.execute("DROP FUNCTION IF EXISTS reject_ai_usage_event_mutation()")


def upgrade() -> None:
    op.create_table(
        "ai_usage_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("contract_version", sa.String(length=16), nullable=False),
        sa.Column("invocation_digest", sa.String(length=64), nullable=False),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.Column("plan_digest", sa.String(length=64), nullable=False),
        sa.Column("adapter_id", sa.Text(), nullable=False),
        sa.Column("authorized_model_id", sa.Text(), nullable=False),
        sa.Column("provider_id", sa.String(length=32), nullable=False),
        sa.Column("model_id", sa.Text(), nullable=False),
        sa.Column("pricing_mode", sa.String(length=32), nullable=False),
        sa.Column("usage_status", sa.String(length=32), nullable=False),
        sa.Column("billing_status", sa.String(length=32), nullable=False),
        sa.Column("input_tokens", sa.BigInteger(), nullable=True),
        sa.Column("cached_input_tokens", sa.BigInteger(), nullable=True),
        sa.Column("cache_write_tokens", sa.BigInteger(), nullable=True),
        sa.Column("output_tokens", sa.BigInteger(), nullable=True),
        sa.Column("reasoning_tokens", sa.BigInteger(), nullable=True),
        sa.Column("total_tokens", sa.BigInteger(), nullable=True),
        sa.Column("pricing_version", sa.String(length=64), nullable=True),
        sa.Column("estimated_cost_nano_usd", sa.BigInteger(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "contract_version = '1'",
            name="ck_ai_usage_events_contract_version",
        ),
        sa.CheckConstraint(
            "length(invocation_digest) = 64 AND "
            "length(request_digest) = 64 AND length(plan_digest) = 64",
            name="ck_ai_usage_events_digest_lengths",
        ),
        sa.CheckConstraint(
            "usage_status IN ('measured', 'unavailable', 'not_applicable')",
            name="ck_ai_usage_events_usage_status",
        ),
        sa.CheckConstraint(
            "billing_status IN ('priced', 'unknown', 'not_applicable')",
            name="ck_ai_usage_events_billing_status",
        ),
        sa.CheckConstraint(
            "(input_tokens IS NULL OR input_tokens >= 0) AND "
            "(cached_input_tokens IS NULL OR cached_input_tokens >= 0) AND "
            "(cache_write_tokens IS NULL OR cache_write_tokens >= 0) AND "
            "(output_tokens IS NULL OR output_tokens >= 0) AND "
            "(reasoning_tokens IS NULL OR reasoning_tokens >= 0) AND "
            "(total_tokens IS NULL OR total_tokens >= 0) AND "
            "(estimated_cost_nano_usd IS NULL OR estimated_cost_nano_usd >= 0)",
            name="ck_ai_usage_events_non_negative",
        ),
        sa.CheckConstraint(
            "(usage_status = 'measured' AND "
            "input_tokens IS NOT NULL AND cached_input_tokens IS NOT NULL AND "
            "cache_write_tokens IS NOT NULL AND output_tokens IS NOT NULL AND "
            "reasoning_tokens IS NOT NULL AND total_tokens IS NOT NULL) OR "
            "(usage_status IN ('unavailable', 'not_applicable') AND "
            "input_tokens IS NULL AND cached_input_tokens IS NULL AND "
            "cache_write_tokens IS NULL AND output_tokens IS NULL AND "
            "reasoning_tokens IS NULL AND total_tokens IS NULL)",
            name="ck_ai_usage_events_measurement_shape",
        ),
        sa.CheckConstraint(
            "usage_status != 'measured' OR "
            "(cached_input_tokens + cache_write_tokens <= input_tokens AND "
            "reasoning_tokens <= output_tokens AND "
            "total_tokens = input_tokens + output_tokens)",
            name="ck_ai_usage_events_token_invariants",
        ),
        sa.CheckConstraint(
            "(billing_status = 'priced' AND usage_status = 'measured' AND "
            "pricing_version IS NOT NULL AND estimated_cost_nano_usd IS NOT NULL) OR "
            "(billing_status = 'unknown' AND "
            "usage_status IN ('measured', 'unavailable') AND "
            "estimated_cost_nano_usd IS NULL) OR "
            "(billing_status = 'not_applicable' AND "
            "usage_status = 'not_applicable' AND pricing_version IS NULL AND "
            "estimated_cost_nano_usd IS NULL)",
            name="ck_ai_usage_events_billing_shape",
        ),
        sa.CheckConstraint(
            "provider_id != 'local' OR "
            "(usage_status = 'not_applicable' AND "
            "billing_status = 'not_applicable' AND pricing_mode = 'not_applicable')",
            name="ck_ai_usage_events_local_not_billable",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_ai_usage_events_invocation_digest",
        "ai_usage_events",
        ["invocation_digest"],
        unique=True,
    )
    op.create_index(
        "ix_ai_usage_events_request_digest",
        "ai_usage_events",
        ["request_digest"],
        unique=False,
    )
    op.create_index(
        "ix_ai_usage_events_occurred_at",
        "ai_usage_events",
        ["occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_ai_usage_events_model_occurred_at",
        "ai_usage_events",
        ["model_id", "occurred_at"],
        unique=False,
    )
    _create_immutability_triggers()


def downgrade() -> None:
    _drop_immutability_triggers()
    op.drop_index(
        "ix_ai_usage_events_model_occurred_at",
        table_name="ai_usage_events",
    )
    op.drop_index(
        "ix_ai_usage_events_occurred_at",
        table_name="ai_usage_events",
    )
    op.drop_index(
        "ix_ai_usage_events_request_digest",
        table_name="ai_usage_events",
    )
    op.drop_index(
        "uq_ai_usage_events_invocation_digest",
        table_name="ai_usage_events",
    )
    op.drop_table("ai_usage_events")
