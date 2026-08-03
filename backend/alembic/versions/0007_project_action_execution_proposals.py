"""Create durable Project action execution proposals.

Revision ID: 0007_project_action_execution_proposals
Revises: 0006_project_update_proposals
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_project_action_execution_proposals"
down_revision = "0006_project_update_proposals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_action_execution_proposals",
        sa.Column(
            "id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "conversation_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "project_revision",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "source_action",
            sa.String(length=512),
            nullable=False,
        ),
        sa.Column(
            "steps",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "approved",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "executed",
            sa.Boolean(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_project_action_execution_proposals_project_id",
        "project_action_execution_proposals",
        ["project_id"],
        unique=False,
    )

    op.create_index(
        "ix_project_action_execution_proposals_conversation_id",
        "project_action_execution_proposals",
        ["conversation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_project_action_execution_proposals_conversation_id",
        table_name="project_action_execution_proposals",
    )

    op.drop_index(
        "ix_project_action_execution_proposals_project_id",
        table_name="project_action_execution_proposals",
    )

    op.drop_table(
        "project_action_execution_proposals"
    )
    