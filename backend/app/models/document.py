from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class Document(Base):
    """One locally discovered source file with D92 workspace persistence metadata."""

    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "workspace_id IS NULL OR workspace_id IN ('personal', 'company')",
            name="ck_documents_workspace_id",
        ),
        Index(
            "uq_documents_legacy_source_path",
            "source_path",
            unique=True,
            sqlite_where=text("workspace_id IS NULL"),
            postgresql_where=text("workspace_id IS NULL"),
        ),
        Index(
            "uq_documents_workspace_source_path",
            "workspace_id",
            "source_path",
            unique=True,
            sqlite_where=text("workspace_id IS NOT NULL"),
            postgresql_where=text("workspace_id IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    source_path: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(32), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False, index=True)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    workspace_id: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan", passive_deletes=True)


from app.models.document_chunk import DocumentChunk  # noqa: E402
