"""Durable Project action execution proposal persistence model."""

from uuid import uuid4

from sqlalchemy import Boolean, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProjectActionExecutionProposalRecord(Base):
    """Durable snapshot of an owner-reviewed execution proposal."""

    __tablename__ = "project_action_execution_proposals"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    project_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    conversation_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    project_revision: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    source_action: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    steps: Mapped[list[dict]] = mapped_column(
        JSON,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PENDING",
    )

    approved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    executed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )