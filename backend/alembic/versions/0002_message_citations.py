"""Persist immutable citations for assistant messages.

Revision ID: 0002_message_citations
Revises: 0001_v061_baseline
Create Date: 2026-08-01
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_message_citations"
down_revision = "0001_v061_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "message_citations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("message_id", sa.String(length=36), nullable=False),
        sa.Column("citation_order", sa.Integer(), nullable=False),
        sa.Column("citation_id", sa.String(length=16), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("file_name", sa.String(length=512), nullable=False),
        sa.Column("source_path", sa.String(length=1024), nullable=False),
        sa.Column("source_locator", sa.String(length=512), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("excerpt_hash", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence_type", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("citation_order >= 1", name="ck_message_citations_order"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_message_citations_confidence"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id", "citation_order", name="uq_message_citation_order"),
    )
    op.create_index("ix_message_citations_message_id", "message_citations", ["message_id"])


def downgrade() -> None:
    op.drop_index("ix_message_citations_message_id", table_name="message_citations")
    op.drop_table("message_citations")
