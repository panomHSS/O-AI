"""Read-only verification of the Alembic-managed O-AI SQLite schema."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import make_url


TARGET_REVISION = "0008_pgvector_foundation"
EXPECTED_TABLES = {
    "alembic_version",
    "conversations",
    "messages",
    "message_citations",
    "documents",
    "document_chunks",
    "document_chunks_fts",
    "memories",
    "memory_versions",
    "projects",
    "project_revisions",
    "project_update_proposals",
    "project_action_execution_proposals",
}
EXPECTED_COLUMNS = {
    "conversations": [("id", "VARCHAR(36)", 1), ("title", "VARCHAR(120)", 0), ("created_at", "DATETIME", 0), ("updated_at", "DATETIME", 0), ("project_id", "VARCHAR(36)", 0)],
    "messages": [("id", "VARCHAR(36)", 1), ("conversation_id", "VARCHAR(36)", 0), ("role", "VARCHAR(16)", 0), ("content", "VARCHAR", 0), ("created_at", "DATETIME", 0)],
    "documents": [("id", "VARCHAR(36)", 1), ("source_path", "VARCHAR(1024)", 0), ("file_name", "VARCHAR(512)", 0), ("file_extension", "VARCHAR(32)", 0), ("mime_type", "VARCHAR(255)", 0), ("file_size", "INTEGER", 0), ("content_hash", "VARCHAR(64)", 0), ("status", "VARCHAR(32)", 0), ("error_message", "TEXT", 0), ("created_at", "DATETIME", 0), ("updated_at", "DATETIME", 0), ("indexed_at", "DATETIME", 0)],
    "document_chunks": [("id", "VARCHAR(36)", 1), ("document_id", "VARCHAR(36)", 0), ("chunk_index", "INTEGER", 0), ("content", "TEXT", 0), ("source_locator", "VARCHAR(512)", 0), ("created_at", "DATETIME", 0)],
    "message_citations": [("id", "VARCHAR(36)", 1), ("message_id", "VARCHAR(36)", 0), ("citation_order", "INTEGER", 0), ("citation_id", "VARCHAR(16)", 0), ("document_id", "VARCHAR(36)", 0), ("file_name", "VARCHAR(512)", 0), ("source_path", "VARCHAR(1024)", 0), ("source_locator", "VARCHAR(512)", 0), ("excerpt", "TEXT", 0), ("excerpt_hash", "VARCHAR(64)", 0), ("confidence", "FLOAT", 0), ("evidence_type", "VARCHAR(32)", 0), ("created_at", "DATETIME", 0)],
    "memories": [("id", "VARCHAR(36)", 1), ("key", "VARCHAR(128)", 0), ("value", "TEXT", 0), ("value_type", "VARCHAR(16)", 0), ("state", "VARCHAR(16)", 0), ("created_at", "DATETIME", 0), ("updated_at", "DATETIME", 0), ("current_version", "INTEGER", 0), ("active_version_id", "VARCHAR(36)", 0), ("pending_version_id", "VARCHAR(36)", 0)],
    "memory_versions": [("id", "VARCHAR(36)", 1), ("memory_id", "VARCHAR(36)", 0), ("version", "INTEGER", 0), ("key", "VARCHAR(128)", 0), ("value", "TEXT", 0), ("value_type", "VARCHAR(16)", 0), ("state", "VARCHAR(16)", 0), ("change_reason", "VARCHAR(512)", 0), ("decision_comment", "TEXT", 0), ("evidence_snapshot", "TEXT", 0), ("created_by", "VARCHAR(64)", 0), ("proposed_by", "VARCHAR(64)", 0), ("proposed_at", "DATETIME", 0), ("decided_by", "VARCHAR(64)", 0), ("decided_at", "DATETIME", 0), ("created_at", "DATETIME", 0)],
    "projects": [("id", "VARCHAR(36)", 1), ("title", "VARCHAR(160)", 0), ("objective", "TEXT", 0), ("status", "VARCHAR(16)", 0), ("current_summary", "TEXT", 0), ("next_action", "VARCHAR(512)", 0), ("current_revision", "INTEGER", 0), ("created_at", "DATETIME", 0), ("updated_at", "DATETIME", 0)],
    "project_revisions": [("id", "VARCHAR(36)", 1), ("project_id", "VARCHAR(36)", 0), ("revision_number", "INTEGER", 0), ("title", "VARCHAR(160)", 0), ("objective", "TEXT", 0), ("status", "VARCHAR(16)", 0), ("current_summary", "TEXT", 0), ("next_action", "VARCHAR(512)", 0), ("change_note", "VARCHAR(512)", 0), ("created_at", "DATETIME", 0)],
    "project_update_proposals": [
    ("id", "VARCHAR(36)", 1),
    ("project_id", "VARCHAR(36)", 0),
    ("conversation_id", "VARCHAR(36)", 0),
    ("base_revision", "INTEGER", 0),
    ("proposed_summary", "TEXT", 0),
    ("proposed_next_action", "VARCHAR(512)", 0),
    ("reason", "VARCHAR(512)", 0),
    ("status", "VARCHAR(16)", 0),
    ("created_at", "DATETIME", 0),
    ("decided_at", "DATETIME", 0),
    ("applied_revision", "INTEGER", 0),
],
"project_action_execution_proposals": [
    ("id", "VARCHAR(36)", 1),
    ("project_id", "VARCHAR(36)", 0),
    ("conversation_id", "VARCHAR(36)", 0),
    ("project_revision", "INTEGER", 0),
    ("source_action", "VARCHAR(512)", 0),
    ("steps", "JSON", 0),
    ("status", "VARCHAR(32)", 0),
    ("approved", "BOOLEAN", 0),
    ("executed", "BOOLEAN", 0),
],
}
EXPECTED_INDEXES = {
    "conversations": {"ix_conversations_updated_at": (["updated_at"], False), "ix_conversations_project_id": (["project_id"], False)},
    "messages": {"ix_messages_conversation_id": (["conversation_id"], False), "ix_messages_created_at": (["created_at"], False)},
    "documents": {"ix_documents_source_path": (["source_path"], True), "ix_documents_content_hash": (["content_hash"], False), "ix_documents_status": (["status"], False), "ix_documents_updated_at": (["updated_at"], False)},
    "document_chunks": {"ix_document_chunks_document_id": (["document_id"], False)},
    "message_citations": {"ix_message_citations_message_id": (["message_id"], False)},
    "memories": {"ix_memories_key": (["key"], True), "ix_memories_state": (["state"], False), "ix_memories_updated_at": (["updated_at"], False)},
    "memory_versions": {"ix_memory_versions_memory_id": (["memory_id"], False)},
    "projects": {"ix_projects_status": (["status"], False), "ix_projects_updated_at": (["updated_at"], False)},
    "project_revisions": {"ix_project_revisions_project_id": (["project_id"], False)},
    "project_update_proposals": {
        "ix_project_update_proposals_project_id": (
            ["project_id"],
            False,
        ),
        "ix_project_update_proposals_conversation_id": (
            ["conversation_id"],
            False,
        ),
        "ix_project_update_proposals_status": (
            ["status"],
            False,
        ),
    },
    "project_action_execution_proposals": {
        "ix_project_action_execution_proposals_project_id": (
            ["project_id"],
            False,
        ),
        "ix_project_action_execution_proposals_conversation_id": (
            ["conversation_id"],
            False,
        ),
    },
}
EXPECTED_FOREIGN_KEYS = {
    "messages": {("conversation_id", "conversations", "id", "CASCADE")},
    "document_chunks": {("document_id", "documents", "id", "CASCADE")},
    "message_citations": {("message_id", "messages", "id", "CASCADE")},
    "memory_versions": {("memory_id", "memories", "id", "CASCADE")},
    "project_revisions": {("project_id", "projects", "id", "NO ACTION")},
    "conversations": {("project_id", "projects", "id", "NO ACTION")},
    "project_update_proposals": {
        ("project_id", "projects", "id", "NO ACTION"),
        ("conversation_id", "conversations", "id", "NO ACTION"),
    },
}
NULLABLE_COLUMNS = {"documents": {"error_message", "indexed_at"}, "memories": {"active_version_id", "pending_version_id"}, "memory_versions": {"decision_comment", "evidence_snapshot", "decided_by", "decided_at"}, "conversations": {"project_id"}, "projects": {"current_summary", "next_action"}, "project_revisions": {"current_summary", "next_action"}, "project_update_proposals": {
    "proposed_summary",
    "proposed_next_action",
    "decided_at",
    "applied_revision",
},}


class DatabaseVerificationError(RuntimeError):
    """The configured database is not safe for the current application version."""


@dataclass(frozen=True)
class DatabaseVerificationResult:
    revision: str


def _database_path(database_url: str) -> Path:
    url = make_url(database_url)
    if not url.drivername.startswith("sqlite") or not url.database or url.database == ":memory:":
        raise DatabaseVerificationError("Startup verification requires a file-backed SQLite database.")
    path = Path(url.database).resolve()
    if not path.is_file():
        raise DatabaseVerificationError("Configured database file does not exist.")
    return path


def _readonly_connection(database_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"{database_path.as_uri()}?mode=ro", uri=True)


def _table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute("SELECT name FROM sqlite_schema WHERE type = 'table'").fetchall()
    return {name for (name,) in rows if not name.startswith("sqlite_") and not name.startswith("document_chunks_fts_")}


def _verify_schema(connection: sqlite3.Connection) -> None:
    tables = _table_names(connection)
    if tables != EXPECTED_TABLES:
        raise DatabaseVerificationError("Configured database has an unsupported table set.")
    for table_name, expected_columns in EXPECTED_COLUMNS.items():
        columns = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        if [(row[1], row[2].upper(), row[5]) for row in columns] != expected_columns:
            raise DatabaseVerificationError(f"Configured database has incompatible columns in {table_name}.")
        nullable_columns = NULLABLE_COLUMNS.get(table_name, set())
        if any(row[3] != (0 if row[1] in nullable_columns else 1) for row in columns):
            raise DatabaseVerificationError(f"Configured database has incompatible nullability in {table_name}.")
        indexes = {row[1]: row for row in connection.execute(f"PRAGMA index_list({table_name})")}
        for index_name, (expected_index_columns, unique) in EXPECTED_INDEXES[table_name].items():
            index = indexes.get(index_name)
            columns_for_index = [] if index is None else [row[2] for row in connection.execute(f"PRAGMA index_info({index_name})")]
            if index is None or bool(index[2]) is not unique or columns_for_index != expected_index_columns:
                raise DatabaseVerificationError(f"Configured database has incompatible index {index_name}.")
    for table_name, expected_foreign_keys in EXPECTED_FOREIGN_KEYS.items():
        foreign_keys = connection.execute(
            f"PRAGMA foreign_key_list({table_name})"
        ).fetchall()

        actual_foreign_keys = {
            (row[3], row[2], row[4], row[6].upper())
            for row in foreign_keys
        }

        if actual_foreign_keys != expected_foreign_keys:
            raise DatabaseVerificationError(
                f"Configured database has incompatible foreign keys in {table_name}."
            )

    message_sql = connection.execute(
        "SELECT sql FROM sqlite_schema WHERE type = 'table' AND name = 'messages'"
    ).fetchone()[0]
    message_sql = connection.execute("SELECT sql FROM sqlite_schema WHERE type = 'table' AND name = 'messages'").fetchone()[0]
    if "CHECK (ROLE IN ('USER', 'ASSISTANT'))" not in message_sql.upper():
        raise DatabaseVerificationError("Configured database is missing the messages role constraint.")
    unique_indexes = [row[1] for row in connection.execute("PRAGMA index_list(document_chunks)") if row[2]]
    if not any([row[2] for row in connection.execute(f"PRAGMA index_info({index_name})")] == ["document_id", "chunk_index"] for index_name in unique_indexes):
        raise DatabaseVerificationError("Configured database is missing the document chunk unique constraint.")
    citation_sql = connection.execute("SELECT sql FROM sqlite_schema WHERE type = 'table' AND name = 'message_citations'").fetchone()[0].upper()
    if "CITATION_ORDER >= 1" not in citation_sql or "CONFIDENCE >= 0 AND CONFIDENCE <= 1" not in citation_sql:
        raise DatabaseVerificationError("Configured database is missing citation constraints.")
    citation_unique_indexes = [row[1] for row in connection.execute("PRAGMA index_list(message_citations)") if row[2]]
    if not any([row[2] for row in connection.execute(f"PRAGMA index_info({index_name})")] == ["message_id", "citation_order"] for index_name in citation_unique_indexes):
        raise DatabaseVerificationError("Configured database is missing citation ordering uniqueness.")
    memory_sql = connection.execute("SELECT sql FROM sqlite_schema WHERE type = 'table' AND name = 'memories'").fetchone()[0].upper()
    if "STATE IN ('PENDING', 'CONFIRMED', 'REJECTED', 'ARCHIVED')" not in memory_sql or "VALUE_TYPE IN ('STRING', 'INTEGER', 'BOOLEAN', 'DATE', 'JSON')" not in memory_sql:
        raise DatabaseVerificationError("Configured database is missing memory constraints.")
    version_sql = connection.execute("SELECT sql FROM sqlite_schema WHERE type = 'table' AND name = 'memory_versions'").fetchone()[0].upper()
    if "STATE IN ('PENDING', 'CONFIRMED', 'REJECTED', 'ARCHIVED')" not in version_sql or "VALUE_TYPE IN ('STRING', 'INTEGER', 'BOOLEAN', 'DATE', 'JSON')" not in version_sql:
        raise DatabaseVerificationError("Configured database is missing memory version constraints.")
    version_trigger = connection.execute("SELECT sql FROM sqlite_schema WHERE type = 'trigger' AND name = 'trg_memory_versions_immutable'").fetchone()
    if version_trigger is None:
        raise DatabaseVerificationError("Configured database is missing memory version immutability protection.")
    project_sql = connection.execute("SELECT sql FROM sqlite_schema WHERE type = 'table' AND name = 'projects'").fetchone()[0].upper()
    revision_sql = connection.execute("SELECT sql FROM sqlite_schema WHERE type = 'table' AND name = 'project_revisions'").fetchone()[0].upper()
    if (
        "STATUS IN ('ACTIVE', 'PAUSED', 'COMPLETED', 'ARCHIVED')" not in project_sql
        or "CURRENT_REVISION >= 1" not in project_sql
        or "LENGTH(TITLE) <= 160" not in project_sql
        or "LENGTH(OBJECTIVE) <= 4000" not in project_sql
        or "REVISION_NUMBER >= 1" not in revision_sql
        or "LENGTH(TRIM(CHANGE_NOTE)) > 0" not in revision_sql
    ):
        raise DatabaseVerificationError("Configured database is missing project constraints.")
    if not all(connection.execute("SELECT sql FROM sqlite_schema WHERE type = 'trigger' AND name = ?", (name,)).fetchone() for name in ("trg_project_revisions_immutable_update", "trg_project_revisions_immutable_delete")):
        raise DatabaseVerificationError("Configured database is missing project revision immutability protection.")
    proposal_sql = connection.execute(
        "SELECT sql FROM sqlite_schema "
        "WHERE type = 'table' AND name = 'project_update_proposals'"
    ).fetchone()[0].upper()

    required_proposal_constraints = (
        "BASE_REVISION >= 1",
        "STATUS IN ('PENDING', 'APPLIED', 'REJECTED', 'STALE')",
        "PROPOSED_SUMMARY IS NOT NULL OR PROPOSED_NEXT_ACTION IS NOT NULL",
        "LENGTH(PROPOSED_SUMMARY) <= 4000",
        "LENGTH(PROPOSED_NEXT_ACTION) <= 512",
        "LENGTH(TRIM(REASON)) > 0",
        "LENGTH(REASON) <= 512",
        "APPLIED_REVISION IS NULL OR APPLIED_REVISION >= 1",
    )

    if not all(
        constraint in proposal_sql
        for constraint in required_proposal_constraints
    ):
        raise DatabaseVerificationError(
            "Configured database is missing Project update proposal constraints."
        )
    memory_foreign_keys = connection.execute("PRAGMA foreign_key_list(memories)").fetchall()
    if {(row[3], row[2], row[4]) for row in memory_foreign_keys} != {("active_version_id", "memory_versions", "id"), ("pending_version_id", "memory_versions", "id")}:
        raise DatabaseVerificationError("Configured database is missing memory version pointers.")
    fts_definition = connection.execute("SELECT sql FROM sqlite_schema WHERE type = 'table' AND name = 'document_chunks_fts'").fetchone()
    expected_fts = "CREATE VIRTUAL TABLE DOCUMENT_CHUNKS_FTS USING FTS5(CONTENT, DOCUMENT_ID UNINDEXED, CHUNK_ID UNINDEXED, SOURCE_LOCATOR UNINDEXED)"
    if fts_definition is None or " ".join(fts_definition[0].upper().split()) != expected_fts:
        raise DatabaseVerificationError("Configured database is missing the required FTS5 table.")


def verify_database(database_url: str) -> DatabaseVerificationResult:
    """Verify the configured database without opening it for write access."""
    database_path = _database_path(database_url)
    with closing(_readonly_connection(database_path)) as connection:
        _verify_schema(connection)
        revisions = [row[0] for row in connection.execute("SELECT version_num FROM alembic_version")]
    if revisions != [TARGET_REVISION]:
        raise DatabaseVerificationError("Configured database is not stamped at the required Alembic revision.")
    return DatabaseVerificationResult(revision=TARGET_REVISION)
