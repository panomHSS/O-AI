from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


EMBEDDING_DIMENSIONS = 1536


class DocumentChunkEmbedding(Base):
    """Derived pgvector search state for an authoritative document chunk."""

    __tablename__ = "document_chunk_embeddings"

    chunk_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "document_chunks.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "documents.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS),
        nullable=False,
    )