"""Create durable owner-controlled project snapshots and conversation links.

Revision ID: 0005_project_backbone
Revises: 0004_memory_versioning
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_project_backbone"
down_revision = "0004_memory_versioning"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("current_summary", sa.Text(), nullable=True),
        sa.Column("next_action", sa.String(512), nullable=True),
        sa.Column("current_revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('ACTIVE', 'PAUSED', 'COMPLETED', 'ARCHIVED')", name="ck_projects_status"),
        sa.CheckConstraint("length(trim(title)) > 0", name="ck_projects_title_nonempty"),
        sa.CheckConstraint("length(title) <= 160", name="ck_projects_title_length"),
        sa.CheckConstraint("length(trim(objective)) > 0", name="ck_projects_objective_nonempty"),
        sa.CheckConstraint("length(objective) <= 4000", name="ck_projects_objective_length"),
        sa.CheckConstraint("current_summary IS NULL OR length(current_summary) <= 4000", name="ck_projects_summary_length"),
        sa.CheckConstraint("next_action IS NULL OR length(next_action) <= 512", name="ck_projects_next_action_length"),
        sa.CheckConstraint("current_revision >= 1", name="ck_projects_current_revision"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_status", "projects", ["status"])
    op.create_index("ix_projects_updated_at", "projects", ["updated_at"])
    op.create_table(
        "project_revisions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("current_summary", sa.Text(), nullable=True),
        sa.Column("next_action", sa.String(512), nullable=True),
        sa.Column("change_note", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "revision_number", name="uq_project_revision_number"),
        sa.CheckConstraint("revision_number >= 1", name="ck_project_revisions_positive_number"),
        sa.CheckConstraint("status IN ('ACTIVE', 'PAUSED', 'COMPLETED', 'ARCHIVED')", name="ck_project_revisions_status"),
        sa.CheckConstraint("length(trim(title)) > 0", name="ck_project_revisions_title_nonempty"),
        sa.CheckConstraint("length(title) <= 160", name="ck_project_revisions_title_length"),
        sa.CheckConstraint("length(trim(objective)) > 0", name="ck_project_revisions_objective_nonempty"),
        sa.CheckConstraint("length(objective) <= 4000", name="ck_project_revisions_objective_length"),
        sa.CheckConstraint("current_summary IS NULL OR length(current_summary) <= 4000", name="ck_project_revisions_summary_length"),
        sa.CheckConstraint("next_action IS NULL OR length(next_action) <= 512", name="ck_project_revisions_next_action_length"),
        sa.CheckConstraint("length(trim(change_note)) > 0", name="ck_project_revisions_note_nonempty"),
        sa.CheckConstraint("length(change_note) <= 512", name="ck_project_revisions_note_length"),
    )
    op.create_index("ix_project_revisions_project_id", "project_revisions", ["project_id"])
    op.execute("CREATE TRIGGER trg_project_revisions_immutable_update BEFORE UPDATE ON project_revisions BEGIN SELECT RAISE(ABORT, 'project revision snapshots are immutable'); END")
    op.execute("CREATE TRIGGER trg_project_revisions_immutable_delete BEFORE DELETE ON project_revisions BEGIN SELECT RAISE(ABORT, 'project revision snapshots are immutable'); END")
    with op.batch_alter_table("conversations") as batch:
        batch.add_column(sa.Column("project_id", sa.String(36), nullable=True))
        batch.create_foreign_key("fk_conversations_project", "projects", ["project_id"], ["id"])
        batch.create_index("ix_conversations_project_id", ["project_id"])


def downgrade() -> None:
    with op.batch_alter_table("conversations") as batch:
        batch.drop_index("ix_conversations_project_id")
        batch.drop_constraint("fk_conversations_project", type_="foreignkey")
        batch.drop_column("project_id")
    op.execute("DROP TRIGGER trg_project_revisions_immutable_delete")
    op.execute("DROP TRIGGER trg_project_revisions_immutable_update")
    op.drop_index("ix_project_revisions_project_id", table_name="project_revisions")
    op.drop_table("project_revisions")
    op.drop_index("ix_projects_updated_at", table_name="projects")
    op.drop_index("ix_projects_status", table_name="projects")
    op.drop_table("projects")
