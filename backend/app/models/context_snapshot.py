"""D97 durable Context snapshot persistence records."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class ContextSnapshotRecord(Base):
    """One immutable D96 snapshot attached to one assistant Message."""

    __tablename__ = "context_snapshots"
    __table_args__ = (
        CheckConstraint(
            "contract_version = '1'",
            name="ck_context_snapshots_contract_version",
        ),
        CheckConstraint(
            "length(snapshot_digest) = 64",
            name="ck_context_snapshots_digest_length",
        ),
        UniqueConstraint(
            "message_id",
            name="uq_context_snapshots_message_id",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    message_id: Mapped[str] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    contract_version: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    snapshot_digest: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    items: Mapped[list["ContextSnapshotItemRecord"]] = relationship(
        back_populates="snapshot",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ContextSnapshotItemRecord.item_order",
    )


class ContextSnapshotItemRecord(Base):
    """One ordered immutable item inside a durable Context snapshot."""

    __tablename__ = "context_snapshot_items"
    __table_args__ = (
        CheckConstraint(
            "item_order >= 1",
            name="ck_context_snapshot_items_order",
        ),
        CheckConstraint(
            "layer IN ('conversation','project','memory','knowledge')",
            name="ck_context_snapshot_items_layer",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_context_snapshot_items_digest_length",
        ),
        UniqueConstraint(
            "snapshot_id",
            "item_order",
            name="uq_context_snapshot_items_order",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("context_snapshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    layer: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    source_id: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    label: Mapped[str | None] = mapped_column(
        String(256),
        nullable=True,
    )
    content_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    parent_source_id: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )
    version_ref: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )
    source_locator: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )
    source_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    snapshot: Mapped[ContextSnapshotRecord] = relationship(
        back_populates="items",
    )


__all__ = [
    "ContextSnapshotItemRecord",
    "ContextSnapshotRecord",
]
