"""Add nullable workspace persistence metadata without classifying legacy rows.

Revision ID: 0012_workspace_persistence
Revises: 0011_automation_foundation
"""

from alembic import op
import sqlalchemy as sa


revision = "0012_workspace_persistence"
down_revision = "0011_automation_foundation"
branch_labels = None
depends_on = None


_ROOT_TABLES = (
    "conversations",
    "projects",
    "memories",
    "documents",
)


def _workspace_column(constraint_name: str) -> sa.Column:
    return sa.Column(
        "workspace_id",
        sa.String(length=16),
        sa.CheckConstraint(
            "workspace_id IS NULL OR workspace_id IN ('personal', 'company')",
            name=constraint_name,
        ),
        nullable=True,
    )


def _partial_unique_kwargs(predicate: str) -> dict[str, object]:
    clause = sa.text(predicate)
    return {
        "sqlite_where": clause,
        "postgresql_where": clause,
    }


def upgrade() -> None:
    op.add_column(
        "conversations",
        _workspace_column("ck_conversations_workspace_id"),
    )
    op.add_column(
        "projects",
        _workspace_column("ck_projects_workspace_id"),
    )
    op.add_column(
        "memories",
        _workspace_column("ck_memories_workspace_id"),
    )
    op.add_column(
        "documents",
        _workspace_column("ck_documents_workspace_id"),
    )

    for table_name in _ROOT_TABLES:
        op.create_index(
            f"ix_{table_name}_workspace_id",
            table_name,
            ["workspace_id"],
        )

    op.drop_index("ix_memories_key", table_name="memories")
    op.create_index("ix_memories_key", "memories", ["key"])
    op.create_index(
        "uq_memories_legacy_key",
        "memories",
        ["key"],
        unique=True,
        **_partial_unique_kwargs("workspace_id IS NULL"),
    )
    op.create_index(
        "uq_memories_workspace_key",
        "memories",
        ["workspace_id", "key"],
        unique=True,
        **_partial_unique_kwargs("workspace_id IS NOT NULL"),
    )

    op.drop_index("ix_documents_source_path", table_name="documents")
    op.create_index(
        "ix_documents_source_path",
        "documents",
        ["source_path"],
    )
    op.create_index(
        "uq_documents_legacy_source_path",
        "documents",
        ["source_path"],
        unique=True,
        **_partial_unique_kwargs("workspace_id IS NULL"),
    )
    op.create_index(
        "uq_documents_workspace_source_path",
        "documents",
        ["workspace_id", "source_path"],
        unique=True,
        **_partial_unique_kwargs("workspace_id IS NOT NULL"),
    )


def _assert_downgrade_safe() -> None:
    bind = op.get_bind()
    for table_name in _ROOT_TABLES:
        scoped_count = bind.execute(
            sa.text(
                f"SELECT COUNT(*) FROM {table_name} "
                "WHERE workspace_id IS NOT NULL"
            )
        ).scalar_one()
        if scoped_count:
            raise RuntimeError("d92_workspace_downgrade_scoped_data")


def downgrade() -> None:
    _assert_downgrade_safe()

    op.drop_index(
        "uq_documents_workspace_source_path",
        table_name="documents",
    )
    op.drop_index(
        "uq_documents_legacy_source_path",
        table_name="documents",
    )
    op.drop_index("ix_documents_source_path", table_name="documents")
    op.create_index(
        "ix_documents_source_path",
        "documents",
        ["source_path"],
        unique=True,
    )

    op.drop_index("uq_memories_workspace_key", table_name="memories")
    op.drop_index("uq_memories_legacy_key", table_name="memories")
    op.drop_index("ix_memories_key", table_name="memories")
    op.create_index(
        "ix_memories_key",
        "memories",
        ["key"],
        unique=True,
    )

    for table_name in reversed(_ROOT_TABLES):
        op.drop_index(
            f"ix_{table_name}_workspace_id",
            table_name=table_name,
        )

    for table_name in reversed(_ROOT_TABLES):
        with op.batch_alter_table(table_name) as batch:
            batch.drop_constraint(
                f"ck_{table_name}_workspace_id",
                type_="check",
            )
            batch.drop_column("workspace_id")
