from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class Memory(Base):
    """Owner-managed personal memory with no provider or learning dependency."""

    __tablename__ = "memories"
    __table_args__ = (
        CheckConstraint("state IN ('PENDING', 'CONFIRMED', 'ARCHIVED')", name="ck_memories_state"),
        CheckConstraint("value_type IN ('STRING', 'INTEGER', 'BOOLEAN', 'DATE', 'JSON')", name="ck_memories_value_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[str] = mapped_column(String(16), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False, index=True)
