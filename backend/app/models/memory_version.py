from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class MemoryVersion(Base):
    """Immutable owner-authored memory state and evidence snapshot."""

    __tablename__ = "memory_versions"
    __table_args__ = (
        UniqueConstraint("memory_id", "version", name="uq_memory_version"),
        CheckConstraint("state IN ('PENDING', 'CONFIRMED', 'REJECTED', 'ARCHIVED')", name="ck_memory_versions_state"),
        CheckConstraint("value_type IN ('STRING', 'INTEGER', 'BOOLEAN', 'DATE', 'JSON')", name="ck_memory_versions_value_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    memory_id: Mapped[str] = mapped_column(ForeignKey("memories.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[str] = mapped_column(String(16), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    change_reason: Mapped[str] = mapped_column(String(512), nullable=False)
    decision_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(64), nullable=False, default="owner")
    proposed_by: Mapped[str] = mapped_column(String(64), nullable=False, default="owner")
    proposed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    decided_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
