"""Durable D79 automation due-slot/run history."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AutomationRunRecord(Base):
    """One immutable due-slot identity with bounded lifecycle status."""

    __tablename__ = "automation_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('claimed', 'delivered', 'missed', 'indeterminate')",
            name="ck_automation_runs_status",
        ),
        UniqueConstraint(
            "automation_id",
            "due_at_utc",
            name="uq_automation_runs_automation_due",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    automation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "automation_definitions.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    definition_digest: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    due_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
