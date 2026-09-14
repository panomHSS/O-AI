"""Durable persistence model for allowlisted D39 execution audit events."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExecutionAuditEventRecord(Base):
    """Append-only application record of one safe execution observation."""

    __tablename__ = "execution_audit_events"
    __table_args__ = (
        CheckConstraint(
            "contract_version = '1'",
            name="ck_execution_audit_events_contract_version",
        ),
        CheckConstraint(
            "stage IN ('planning', 'authorization', 'execution')",
            name="ck_execution_audit_events_stage",
        ),
        CheckConstraint(
            "action IN ('started', 'completed')",
            name="ck_execution_audit_events_action",
        ),
        CheckConstraint(
            "status IN ('planned', 'rejected', 'unavailable', "
            "'authorized', 'blocked', 'started', 'succeeded', 'failed')",
            name="ck_execution_audit_events_status",
        ),
        CheckConstraint(
            "target_kind IS NULL OR target_kind IN ('ai', 'tool', 'module')",
            name="ck_execution_audit_events_target_kind",
        ),
        CheckConstraint(
            "plan_digest IS NULL OR length(plan_digest) = 64",
            name="ck_execution_audit_events_plan_digest_length",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    contract_version: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    request_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True,
    )
    stage: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    target_kind: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
    )
    adapter_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    reason_code: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    plan_digest: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
