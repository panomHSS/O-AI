"""Durable D79 owner-approved automation definition record."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AutomationDefinitionRecord(Base):
    """One durable exact automation proposal/grant."""

    __tablename__ = "automation_definitions"
    __table_args__ = (
        CheckConstraint(
            "kind = 'local_reminder'",
            name="ck_automation_definitions_kind",
        ),
        CheckConstraint(
            "schedule_kind IN ('once', 'daily')",
            name="ck_automation_definitions_schedule_kind",
        ),
        CheckConstraint(
            "status IN "
            "('pending', 'approved', 'denied', 'cancelled', 'completed')",
            name="ck_automation_definitions_status",
        ),
        CheckConstraint(
            "max_runs >= 1 AND max_runs <= 31",
            name="ck_automation_definitions_max_runs",
        ),
        CheckConstraint(
            "(schedule_kind = 'once' "
            "AND run_at_iso IS NOT NULL "
            "AND daily_local_time IS NULL "
            "AND max_runs = 1) "
            "OR "
            "(schedule_kind = 'daily' "
            "AND run_at_iso IS NULL "
            "AND daily_local_time IS NOT NULL)",
            name="ck_automation_definitions_schedule_shape",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    contract_version: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    schedule_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    run_at_iso: Mapped[str | None] = mapped_column(Text, nullable=True)
    daily_local_time: Mapped[str | None] = mapped_column(
        String(5),
        nullable=True,
    )
    timezone: Mapped[str] = mapped_column(String(128), nullable=False)
    max_runs: Mapped[int] = mapped_column(Integer, nullable=False)
    definition_digest: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    approval_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    terminal_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_due_at_utc: Mapped[datetime | None] = mapped_column(
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
