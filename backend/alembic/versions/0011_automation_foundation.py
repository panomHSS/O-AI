"""Create durable D79 automation authority foundation.

Revision ID: 0011_automation_foundation
Revises: 0010_oauth_credentials
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_automation_foundation"
down_revision = "0010_oauth_credentials"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "automation_definitions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "contract_version",
            sa.String(length=16),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "schedule_kind",
            sa.String(length=16),
            nullable=False,
        ),
        sa.Column("run_at_iso", sa.Text(), nullable=True),
        sa.Column(
            "daily_local_time",
            sa.String(length=5),
            nullable=True,
        ),
        sa.Column(
            "timezone",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column("max_runs", sa.Integer(), nullable=False),
        sa.Column(
            "definition_digest",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "approval_expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "approved_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "terminal_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "next_due_at_utc",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            "kind = 'local_reminder'",
            name="ck_automation_definitions_kind",
        ),
        sa.CheckConstraint(
            "schedule_kind IN ('once', 'daily')",
            name="ck_automation_definitions_schedule_kind",
        ),
        sa.CheckConstraint(
            "status IN "
            "('pending', 'approved', 'denied', 'cancelled', 'completed')",
            name="ck_automation_definitions_status",
        ),
        sa.CheckConstraint(
            "max_runs >= 1 AND max_runs <= 31",
            name="ck_automation_definitions_max_runs",
        ),
        sa.CheckConstraint(
            "(schedule_kind = 'once' "
            "AND run_at_iso IS NOT NULL "
            "AND daily_local_time IS NULL "
            "AND max_runs = 1) "
            "OR "
            "(schedule_kind = 'daily' "
            "AND run_at_iso IS NULL "
            "AND daily_local_time IS NOT NULL)",
            name="ck_automation_definitions_schedule_shape",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_automation_definitions_status_due",
        "automation_definitions",
        ["status", "next_due_at_utc"],
    )

    op.create_table(
        "automation_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "automation_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "definition_digest",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "due_at_utc",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "claimed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "delivered_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('claimed', 'delivered', 'missed', 'indeterminate')",
            name="ck_automation_runs_status",
        ),
        sa.ForeignKeyConstraint(
            ["automation_id"],
            ["automation_definitions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "automation_id",
            "due_at_utc",
            name="uq_automation_runs_automation_due",
        ),
    )
    op.create_index(
        "ix_automation_runs_automation_due",
        "automation_runs",
        ["automation_id", "due_at_utc"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_automation_runs_automation_due",
        table_name="automation_runs",
    )
    op.drop_table("automation_runs")
    op.drop_index(
        "ix_automation_definitions_status_due",
        table_name="automation_definitions",
    )
    op.drop_table("automation_definitions")
