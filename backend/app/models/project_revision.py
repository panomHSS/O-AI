from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class ProjectRevision(Base):
    """Immutable, append-only snapshot of owner-visible project state."""

    __tablename__ = "project_revisions"
    __table_args__ = (
        UniqueConstraint("project_id", "revision_number", name="uq_project_revision_number"),
        CheckConstraint("revision_number >= 1", name="ck_project_revisions_positive_number"),
        CheckConstraint("status IN ('ACTIVE', 'PAUSED', 'COMPLETED', 'ARCHIVED')", name="ck_project_revisions_status"),
        CheckConstraint("length(trim(title)) > 0", name="ck_project_revisions_title_nonempty"),
        CheckConstraint("length(title) <= 160", name="ck_project_revisions_title_length"),
        CheckConstraint("length(trim(objective)) > 0", name="ck_project_revisions_objective_nonempty"),
        CheckConstraint("length(objective) <= 4000", name="ck_project_revisions_objective_length"),
        CheckConstraint("current_summary IS NULL OR length(current_summary) <= 4000", name="ck_project_revisions_summary_length"),
        CheckConstraint("next_action IS NULL OR length(next_action) <= 512", name="ck_project_revisions_next_action_length"),
        CheckConstraint("length(trim(change_note)) > 0", name="ck_project_revisions_note_nonempty"),
        CheckConstraint("length(change_note) <= 512", name="ck_project_revisions_note_length"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    current_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_action: Mapped[str | None] = mapped_column(String(512), nullable=True)
    change_note: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
