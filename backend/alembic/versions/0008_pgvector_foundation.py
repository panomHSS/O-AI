"""Establish PostgreSQL pgvector knowledge-search foundation.

Revision ID: 0008_pgvector_foundation
Revises: 0007_project_action_execution_proposals
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision = "0008_pgvector_foundation"
down_revision = "0007_project_action_execution_proposals"
branch_labels = None
depends_on = None


EMBEDDING_DIMENSIONS = 1536


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name != "postgresql":
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "document_chunk_embeddings",
        sa.Column(
            "chunk_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "embedding",
            Vector(EMBEDDING_DIMENSIONS),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["document_chunks.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("chunk_id"),
    )

    op.create_index(
        "ix_document_chunk_embeddings_document_id",
        "document_chunk_embeddings",
        ["document_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name != "postgresql":
        return

    op.drop_index(
        "ix_document_chunk_embeddings_document_id",
        table_name="document_chunk_embeddings",
    )

    op.drop_table(
        "document_chunk_embeddings",
    )
