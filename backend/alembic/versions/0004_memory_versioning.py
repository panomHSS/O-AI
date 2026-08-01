"""Add immutable owner-controlled memory versions.

Revision ID: 0004_memory_versioning
Revises: 0003_personal_memory
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_memory_versioning"
down_revision = "0003_personal_memory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "memory_versions",
        sa.Column("id", sa.String(36), nullable=False), sa.Column("memory_id", sa.String(36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False), sa.Column("key", sa.String(128), nullable=False),
        sa.Column("value", sa.Text(), nullable=False), sa.Column("value_type", sa.String(16), nullable=False),
        sa.Column("state", sa.String(16), nullable=False), sa.Column("change_reason", sa.String(512), nullable=False),
        sa.Column("decision_comment", sa.Text(), nullable=True), sa.Column("evidence_snapshot", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(64), nullable=False), sa.Column("proposed_by", sa.String(64), nullable=False), sa.Column("proposed_at", sa.DateTime(timezone=True), nullable=False), sa.Column("decided_by", sa.String(64), nullable=True), sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["memory_id"], ["memories.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("memory_id", "version", name="uq_memory_version"), sa.CheckConstraint("state IN ('PENDING', 'CONFIRMED', 'REJECTED', 'ARCHIVED')", name="ck_memory_versions_state"), sa.CheckConstraint("value_type IN ('STRING', 'INTEGER', 'BOOLEAN', 'DATE', 'JSON')", name="ck_memory_versions_value_type"),
    )
    op.create_index("ix_memory_versions_memory_id", "memory_versions", ["memory_id"])
    op.execute(
        """
        CREATE TRIGGER trg_memory_versions_immutable
        BEFORE UPDATE ON memory_versions
        FOR EACH ROW WHEN
            NEW.memory_id IS NOT OLD.memory_id OR NEW.version IS NOT OLD.version
            OR NEW.key IS NOT OLD.key OR NEW.value IS NOT OLD.value
            OR NEW.value_type IS NOT OLD.value_type OR NEW.change_reason IS NOT OLD.change_reason
            OR NEW.evidence_snapshot IS NOT OLD.evidence_snapshot
            OR NEW.created_by IS NOT OLD.created_by OR NEW.proposed_by IS NOT OLD.proposed_by
            OR NEW.proposed_at IS NOT OLD.proposed_at OR NEW.created_at IS NOT OLD.created_at
            OR NOT (OLD.state = 'PENDING' AND NEW.state IN ('CONFIRMED', 'REJECTED'))
        BEGIN
            SELECT RAISE(ABORT, 'memory version snapshots are immutable');
        END
        """
    )
    with op.batch_alter_table("memories") as batch:
        batch.drop_constraint("ck_memories_state", type_="check")
        batch.create_check_constraint("ck_memories_state", "state IN ('PENDING', 'CONFIRMED', 'REJECTED', 'ARCHIVED')")
        batch.add_column(sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"))
        batch.add_column(sa.Column("active_version_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("pending_version_id", sa.String(36), nullable=True))
        batch.create_foreign_key("fk_memories_active_version", "memory_versions", ["active_version_id"], ["id"])
        batch.create_foreign_key("fk_memories_pending_version", "memory_versions", ["pending_version_id"], ["id"])
        batch.create_unique_constraint("uq_memories_pending_version", ["pending_version_id"])
    op.execute("INSERT INTO memory_versions (id, memory_id, version, key, value, value_type, state, change_reason, created_by, proposed_by, proposed_at, created_at) SELECT lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))), 2) || '-a' || substr(lower(hex(randomblob(2))), 2) || '-' || lower(hex(randomblob(6))), id, 1, key, value, value_type, state, 'Migrated existing memory.', 'owner', 'owner', created_at, created_at FROM memories")
    op.execute("UPDATE memories SET active_version_id = (SELECT id FROM memory_versions WHERE memory_versions.memory_id = memories.id AND state = 'CONFIRMED')")
    op.execute("UPDATE memories SET pending_version_id = (SELECT id FROM memory_versions WHERE memory_versions.memory_id = memories.id AND state = 'PENDING')")


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_memory_versions_immutable")
    with op.batch_alter_table("memories") as batch:
        batch.drop_constraint("uq_memories_pending_version", type_="unique")
        batch.drop_constraint("fk_memories_pending_version", type_="foreignkey")
        batch.drop_constraint("fk_memories_active_version", type_="foreignkey")
        batch.drop_column("pending_version_id")
        batch.drop_column("active_version_id")
        batch.drop_column("current_version")
        batch.drop_constraint("ck_memories_state", type_="check")
        batch.create_check_constraint("ck_memories_state", "state IN ('PENDING', 'CONFIRMED', 'ARCHIVED')")
    op.drop_index("ix_memory_versions_memory_id", table_name="memory_versions")
    op.drop_table("memory_versions")
