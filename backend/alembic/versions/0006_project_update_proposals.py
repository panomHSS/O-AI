"""Add durable owner-approved Project update proposals.

Revision ID: 0006_project_update_proposals
Revises: 0005_project_backbone
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_project_update_proposals"
down_revision = "0005_project_backbone"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_update_proposals",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("conversation_id", sa.String(36), nullable=False),
        sa.Column("base_revision", sa.Integer(), nullable=False),
        sa.Column("proposed_summary", sa.Text(), nullable=True),
        sa.Column("proposed_next_action", sa.String(512), nullable=True),
        sa.Column("reason", sa.String(512), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_revision", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "base_revision >= 1",
            name="ck_project_update_proposals_base_revision",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'APPLIED', 'REJECTED', 'STALE')",
            name="ck_project_update_proposals_status",
        ),
        sa.CheckConstraint(
            "proposed_summary IS NOT NULL OR proposed_next_action IS NOT NULL",
            name="ck_project_update_proposals_has_change",
        ),
        sa.CheckConstraint(
            "proposed_summary IS NULL OR length(proposed_summary) <= 4000",
            name="ck_project_update_proposals_summary_length",
        ),
        sa.CheckConstraint(
            "proposed_next_action IS NULL OR length(proposed_next_action) <= 512",
            name="ck_project_update_proposals_next_action_length",
        ),
        sa.CheckConstraint(
            "length(trim(reason)) > 0",
            name="ck_project_update_proposals_reason_nonempty",
        ),
        sa.CheckConstraint(
            "length(reason) <= 512",
            name="ck_project_update_proposals_reason_length",
        ),
        sa.CheckConstraint(
            """
            (status = 'PENDING' AND decided_at IS NULL AND applied_revision IS NULL)
            OR
            (status = 'APPLIED' AND decided_at IS NOT NULL AND applied_revision IS NOT NULL)
            OR
            (status IN ('REJECTED', 'STALE') AND decided_at IS NOT NULL AND applied_revision IS NULL)
            """,
            name="ck_project_update_proposals_lifecycle",
        ),
        sa.CheckConstraint(
            "applied_revision IS NULL OR applied_revision >= 1",
            name="ck_project_update_proposals_applied_revision",
        ),
    )

    op.create_index(
        "ix_project_update_proposals_project_id",
        "project_update_proposals",
        ["project_id"],
    )
    op.create_index(
        "ix_project_update_proposals_conversation_id",
        "project_update_proposals",
        ["conversation_id"],
    )
    op.create_index(
        "ix_project_update_proposals_status",
        "project_update_proposals",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_project_update_proposals_status",
        table_name="project_update_proposals",
    )
    op.drop_index(
        "ix_project_update_proposals_conversation_id",
        table_name="project_update_proposals",
    )
    op.drop_index(
        "ix_project_update_proposals_project_id",
        table_name="project_update_proposals",
    )
    op.drop_table("project_update_proposals")
