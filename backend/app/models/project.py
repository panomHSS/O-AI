from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class Project(Base):
    """Explicitly owner-managed durable project state; never provider context in Phase 2."""

    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'PAUSED', 'COMPLETED', 'ARCHIVED')", name="ck_projects_status"),
        CheckConstraint("length(trim(title)) > 0", name="ck_projects_title_nonempty"),
        CheckConstraint("length(title) <= 160", name="ck_projects_title_length"),
        CheckConstraint("length(trim(objective)) > 0", name="ck_projects_objective_nonempty"),
        CheckConstraint("length(objective) <= 4000", name="ck_projects_objective_length"),
        CheckConstraint("current_summary IS NULL OR length(current_summary) <= 4000", name="ck_projects_summary_length"),
        CheckConstraint("next_action IS NULL OR length(next_action) <= 512", name="ck_projects_next_action_length"),
        CheckConstraint("current_revision >= 1", name="ck_projects_current_revision"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE", index=True)
    current_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_action: Mapped[str | None] = mapped_column(String(512), nullable=True)
    current_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False, index=True)
