from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class Memory(Base):
    """Owner-managed memory root with D92 workspace persistence metadata."""

    __tablename__ = "memories"
    __table_args__ = (
        CheckConstraint("state IN ('PENDING', 'CONFIRMED', 'REJECTED', 'ARCHIVED')", name="ck_memories_state"),
        CheckConstraint("value_type IN ('STRING', 'INTEGER', 'BOOLEAN', 'DATE', 'JSON')", name="ck_memories_value_type"),
        CheckConstraint(
            "workspace_id IS NULL OR workspace_id IN ('personal', 'company')",
            name="ck_memories_workspace_id",
        ),
        Index(
            "uq_memories_legacy_key",
            "key",
            unique=True,
            sqlite_where=text("workspace_id IS NULL"),
            postgresql_where=text("workspace_id IS NULL"),
        ),
        Index(
            "uq_memories_workspace_key",
            "workspace_id",
            "key",
            unique=True,
            sqlite_where=text("workspace_id IS NOT NULL"),
            postgresql_where=text("workspace_id IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[str] = mapped_column(String(16), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING", index=True)
    current_version: Mapped[int] = mapped_column(nullable=False, default=1)
    active_version_id: Mapped[str | None] = mapped_column(ForeignKey("memory_versions.id"), nullable=True)
    pending_version_id: Mapped[str | None] = mapped_column(ForeignKey("memory_versions.id"), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False, index=True)
    workspace_id: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
