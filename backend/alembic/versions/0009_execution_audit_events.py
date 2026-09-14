"""Create durable execution audit event storage.

Revision ID: 0009_execution_audit_events
Revises: 0008_pgvector_foundation
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_execution_audit_events"
down_revision = "0008_pgvector_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "execution_audit_events",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "contract_version",
            sa.String(length=16),
            nullable=False,
        ),
        sa.Column(
            "request_id",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "stage",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "action",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "target_kind",
            sa.String(length=16),
            nullable=True,
        ),
        sa.Column(
            "adapter_id",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "reason_code",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "plan_digest",
            sa.String(length=64),
            nullable=True,
        ),
        sa.CheckConstraint(
            "contract_version = '1'",
            name="ck_execution_audit_events_contract_version",
        ),
        sa.CheckConstraint(
            "stage IN ('planning', 'authorization', 'execution')",
            name="ck_execution_audit_events_stage",
        ),
        sa.CheckConstraint(
            "action IN ('started', 'completed')",
            name="ck_execution_audit_events_action",
        ),
        sa.CheckConstraint(
            "status IN ('planned', 'rejected', 'unavailable', "
            "'authorized', 'blocked', 'started', 'succeeded', 'failed')",
            name="ck_execution_audit_events_status",
        ),
        sa.CheckConstraint(
            "target_kind IS NULL OR target_kind IN ('ai', 'tool', 'module')",
            name="ck_execution_audit_events_target_kind",
        ),
        sa.CheckConstraint(
            "plan_digest IS NULL OR length(plan_digest) = 64",
            name="ck_execution_audit_events_plan_digest_length",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_execution_audit_events_request_id",
        "execution_audit_events",
        ["request_id"],
        unique=False,
    )
    op.create_index(
        "ix_execution_audit_events_occurred_at",
        "execution_audit_events",
        ["occurred_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_execution_audit_events_occurred_at",
        table_name="execution_audit_events",
    )
    op.drop_index(
        "ix_execution_audit_events_request_id",
        table_name="execution_audit_events",
    )
    op.drop_table("execution_audit_events")
