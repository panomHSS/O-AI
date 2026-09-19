"""Persist D97 turn-linked Context snapshots.

Revision ID: 0013_context_snapshot_persistence
Revises: 0012_workspace_persistence
"""

from alembic import op
import sqlalchemy as sa


revision = "0013_context_snapshot_persistence"
down_revision = "0012_workspace_persistence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "context_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("message_id", sa.String(length=36), nullable=False),
        sa.Column(
            "contract_version",
            sa.String(length=16),
            nullable=False,
        ),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "snapshot_digest",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            "contract_version = '1'",
            name="ck_context_snapshots_contract_version",
        ),
        sa.CheckConstraint(
            "length(snapshot_digest) = 64",
            name="ck_context_snapshots_digest_length",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "message_id",
            name="uq_context_snapshots_message_id",
        ),
    )

    op.create_table(
        "context_snapshot_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "snapshot_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column("item_order", sa.Integer(), nullable=False),
        sa.Column("layer", sa.String(length=16), nullable=False),
        sa.Column("source_id", sa.String(length=512), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("label", sa.String(length=256), nullable=True),
        sa.Column(
            "content_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "parent_source_id",
            sa.String(length=512),
            nullable=True,
        ),
        sa.Column(
            "version_ref",
            sa.String(length=512),
            nullable=True,
        ),
        sa.Column(
            "source_locator",
            sa.String(length=1024),
            nullable=True,
        ),
        sa.Column(
            "source_timestamp",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "item_order >= 1",
            name="ck_context_snapshot_items_order",
        ),
        sa.CheckConstraint(
            "layer IN ('conversation','project','memory','knowledge')",
            name="ck_context_snapshot_items_layer",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_context_snapshot_items_digest_length",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["context_snapshots.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "snapshot_id",
            "item_order",
            name="uq_context_snapshot_items_order",
        ),
    )
    op.create_index(
        "ix_context_snapshot_items_snapshot_id",
        "context_snapshot_items",
        ["snapshot_id"],
    )


def _assert_downgrade_safe() -> None:
    bind = op.get_bind()
    snapshots = bind.execute(
        sa.text("SELECT COUNT(*) FROM context_snapshots")
    ).scalar_one()
    items = bind.execute(
        sa.text("SELECT COUNT(*) FROM context_snapshot_items")
    ).scalar_one()
    if snapshots or items:
        raise RuntimeError("d97_context_snapshot_downgrade_data")


def downgrade() -> None:
    _assert_downgrade_safe()
    op.drop_index(
        "ix_context_snapshot_items_snapshot_id",
        table_name="context_snapshot_items",
    )
    op.drop_table("context_snapshot_items")
    op.drop_table("context_snapshots")
