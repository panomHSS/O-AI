"""Create owner-controlled personal memory storage.

Revision ID: 0003_personal_memory
Revises: 0002_message_citations
Create Date: 2026-08-01
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_personal_memory"
down_revision = "0002_message_citations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "memories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("value_type", sa.String(length=16), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("state IN ('PENDING', 'CONFIRMED', 'ARCHIVED')", name="ck_memories_state"),
        sa.CheckConstraint("value_type IN ('STRING', 'INTEGER', 'BOOLEAN', 'DATE', 'JSON')", name="ck_memories_value_type"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_memories_key", "memories", ["key"], unique=True)
    op.create_index("ix_memories_state", "memories", ["state"])
    op.create_index("ix_memories_updated_at", "memories", ["updated_at"])


def downgrade() -> None:
    op.drop_index("ix_memories_updated_at", table_name="memories")
    op.drop_index("ix_memories_state", table_name="memories")
    op.drop_index("ix_memories_key", table_name="memories")
    op.drop_table("memories")
