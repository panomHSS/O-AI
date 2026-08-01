from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class ProjectUpdateProposal(Base):
    """Durable owner-reviewed proposal for bounded Project progress updates."""

    __tablename__ = "project_update_proposals"
    __table_args__ = (
        CheckConstraint(
            "base_revision >= 1",
            name="ck_project_update_proposals_base_revision",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'APPLIED', 'REJECTED', 'STALE')",
            name="ck_project_update_proposals_status",
        ),
        CheckConstraint(
            "proposed_summary IS NOT NULL OR proposed_next_action IS NOT NULL",
            name="ck_project_update_proposals_has_change",
        ),
        CheckConstraint(
            "proposed_summary IS NULL OR length(proposed_summary) <= 4000",
            name="ck_project_update_proposals_summary_length",
        ),
        CheckConstraint(
            "proposed_next_action IS NULL OR length(proposed_next_action) <= 512",
            name="ck_project_update_proposals_next_action_length",
        ),
        CheckConstraint(
            "length(trim(reason)) > 0",
            name="ck_project_update_proposals_reason_nonempty",
        ),
        CheckConstraint(
            "length(reason) <= 512",
            name="ck_project_update_proposals_reason_length",
        ),
        CheckConstraint(
            """
            (status = 'PENDING' AND decided_at IS NULL AND applied_revision IS NULL)
            OR
            (status = 'APPLIED' AND decided_at IS NOT NULL AND applied_revision IS NOT NULL)
            OR
            (status IN ('REJECTED', 'STALE') AND decided_at IS NOT NULL AND applied_revision IS NULL)
            """,
            name="ck_project_update_proposals_lifecycle",
        ),
        CheckConstraint(
            "applied_revision IS NULL OR applied_revision >= 1",
            name="ck_project_update_proposals_applied_revision",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id"),
        nullable=False,
        index=True,
    )
    base_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    proposed_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_next_action: Mapped[str | None] = mapped_column(String(512), nullable=True)
    reason: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    applied_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
