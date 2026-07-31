"""Safely stamp a verified O-AI 0.6.1 SQLite database with the Alembic baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sqlite3
import sys
import tempfile
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from alembic import __version__ as ALEMBIC_VERSION
from alembic import command
from alembic.config import Config


BACKUP_MANIFEST = "manifest.json"
MANIFEST_VERSION = 1
OAI_VERSION = "0.6.2A"
BACKUP_REASON = "baseline_adoption"
TARGET_REVISION = "0001_v061_baseline"
EXPECTED_TABLES = {"conversations", "messages", "documents", "document_chunks", "document_chunks_fts"}
EXPECTED_COLUMNS = {
    "conversations": [("id", "VARCHAR(36)", 1), ("title", "VARCHAR(120)", 0), ("created_at", "DATETIME", 0), ("updated_at", "DATETIME", 0)],
    "messages": [("id", "VARCHAR(36)", 1), ("conversation_id", "VARCHAR(36)", 0), ("role", "VARCHAR(16)", 0), ("content", "VARCHAR", 0), ("created_at", "DATETIME", 0)],
    "documents": [("id", "VARCHAR(36)", 1), ("source_path", "VARCHAR(1024)", 0), ("file_name", "VARCHAR(512)", 0), ("file_extension", "VARCHAR(32)", 0), ("mime_type", "VARCHAR(255)", 0), ("file_size", "INTEGER", 0), ("content_hash", "VARCHAR(64)", 0), ("status", "VARCHAR(32)", 0), ("error_message", "TEXT", 0), ("created_at", "DATETIME", 0), ("updated_at", "DATETIME", 0), ("indexed_at", "DATETIME", 0)],
    "document_chunks": [("id", "VARCHAR(36)", 1), ("document_id", "VARCHAR(36)", 0), ("chunk_index", "INTEGER", 0), ("content", "TEXT", 0), ("source_locator", "VARCHAR(512)", 0), ("created_at", "DATETIME", 0)],
}
EXPECTED_INDEXES = {
    "conversations": {"ix_conversations_updated_at": (["updated_at"], False)},
    "messages": {"ix_messages_conversation_id": (["conversation_id"], False), "ix_messages_created_at": (["created_at"], False)},
    "documents": {"ix_documents_source_path": (["source_path"], True), "ix_documents_content_hash": (["content_hash"], False), "ix_documents_status": (["status"], False), "ix_documents_updated_at": (["updated_at"], False)},
    "document_chunks": {"ix_document_chunks_document_id": (["document_id"], False)},
}
EXPECTED_FOREIGN_KEYS = {
    "messages": ("conversation_id", "conversations", "id"),
    "document_chunks": ("document_id", "documents", "id"),
}
NULLABLE_COLUMNS = {"documents": {"error_message", "indexed_at"}}


class AdoptionError(RuntimeError):
    """The candidate database cannot safely be adopted."""


def _readonly_connection(database_path: Path) -> sqlite3.Connection:
    if not database_path.is_file():
        raise AdoptionError(f"Database file does not exist: {database_path}")
    return sqlite3.connect(f"{database_path.resolve().as_uri()}?mode=ro", uri=True)


def _user_tables(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute("SELECT name FROM sqlite_schema WHERE type = 'table'").fetchall()
    return {name for (name,) in rows if not name.startswith("sqlite_") and not name.startswith("document_chunks_fts_")}


def _validate_columns(connection: sqlite3.Connection, table_name: str) -> None:
    actual = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    expected = EXPECTED_COLUMNS[table_name]
    observed = [(row[1], row[2].upper(), row[5]) for row in actual]
    if observed != expected:
        raise AdoptionError(f"Unexpected columns or primary key for {table_name}: {observed}")
    nullable_columns = NULLABLE_COLUMNS.get(table_name, set())
    for row in actual:
        expected_not_null = 0 if row[1] in nullable_columns else 1
        if row[3] != expected_not_null:
            raise AdoptionError(f"Unexpected nullability for {table_name}.{row[1]}")


def _validate_indexes(connection: sqlite3.Connection, table_name: str) -> None:
    indexes = {row[1]: row for row in connection.execute(f"PRAGMA index_list({table_name})")}
    for index_name, (columns, unique) in EXPECTED_INDEXES[table_name].items():
        index = indexes.get(index_name)
        if index is None or bool(index[2]) is not unique:
            raise AdoptionError(f"Missing or invalid index {index_name}")
        actual_columns = [row[2] for row in connection.execute(f"PRAGMA index_info({index_name})")]
        if actual_columns != columns:
            raise AdoptionError(f"Unexpected columns for index {index_name}: {actual_columns}")


def _validate_foreign_key(connection: sqlite3.Connection, table_name: str) -> None:
    column_name, referred_table, referred_column = EXPECTED_FOREIGN_KEYS[table_name]
    foreign_keys = connection.execute(f"PRAGMA foreign_key_list({table_name})").fetchall()
    matching = [row for row in foreign_keys if row[3:5] == (column_name, referred_column) and row[2] == referred_table]
    if len(matching) != 1 or matching[0][6].upper() != "CASCADE":
        raise AdoptionError(f"Missing CASCADE foreign key from {table_name}.{column_name}")


def _validate_constraints(connection: sqlite3.Connection) -> None:
    message_sql = connection.execute("SELECT sql FROM sqlite_schema WHERE type = 'table' AND name = 'messages'").fetchone()[0]
    if "CHECK (ROLE IN ('USER', 'ASSISTANT'))" not in message_sql.upper():
        raise AdoptionError("Missing messages role check constraint")
    indexes = connection.execute("PRAGMA index_list(document_chunks)").fetchall()
    unique_indexes = [row[1] for row in indexes if row[2]]
    if not any([row[2] for row in connection.execute(f"PRAGMA index_info({index_name})")] == ["document_id", "chunk_index"] for index_name in unique_indexes):
        raise AdoptionError("Missing document_chunks(document_id, chunk_index) unique constraint")


def _validate_fts(connection: sqlite3.Connection) -> None:
    row = connection.execute("SELECT sql FROM sqlite_schema WHERE type = 'table' AND name = 'document_chunks_fts'").fetchone()
    if row is None:
        raise AdoptionError("Missing document_chunks_fts")
    normalized = " ".join(row[0].upper().split())
    expected = "CREATE VIRTUAL TABLE DOCUMENT_CHUNKS_FTS USING FTS5(CONTENT, DOCUMENT_ID UNINDEXED, CHUNK_ID UNINDEXED, SOURCE_LOCATOR UNINDEXED)"
    if normalized != expected:
        raise AdoptionError("document_chunks_fts is not the required FTS5 definition")


def validate_database(database_path: Path) -> None:
    """Validate the complete 0.6.1 schema using a read-only SQLite connection."""
    with closing(_readonly_connection(database_path)) as connection:
        tables = _user_tables(connection)
        allowed_tables = EXPECTED_TABLES | {"alembic_version"}
        if tables - allowed_tables or not EXPECTED_TABLES.issubset(tables):
            raise AdoptionError(f"Unsupported table set: {sorted(tables)}")
        for table_name in EXPECTED_COLUMNS:
            _validate_columns(connection, table_name)
            _validate_indexes(connection, table_name)
        for table_name in EXPECTED_FOREIGN_KEYS:
            _validate_foreign_key(connection, table_name)
        _validate_constraints(connection)
        _validate_fts(connection)


def managed_revision(database_path: Path) -> str | None:
    """Return the already stamped revision, rejecting malformed version tracking."""
    with closing(_readonly_connection(database_path)) as connection:
        if "alembic_version" not in _user_tables(connection):
            return None
        versions = [row[0] for row in connection.execute("SELECT version_num FROM alembic_version")]
    if versions != [TARGET_REVISION]:
        raise AdoptionError(f"Database is already managed at an unsupported revision: {versions}")
    return TARGET_REVISION


def _integrity_check(database_path: Path) -> None:
    with closing(_readonly_connection(database_path)) as connection:
        results = [row[0] for row in connection.execute("PRAGMA integrity_check")]
    if results != ["ok"]:
        raise AdoptionError(f"Backup integrity check failed: {results}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def create_backup(database_path: Path, backup_directory: Path) -> tuple[Path, dict[str, object]]:
    """Copy a database with SQLite's backup API and record verified metadata."""
    backup_directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc)
    backup_name = f"{database_path.stem}-{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex[:12]}.db"
    backup_path = backup_directory / backup_name
    try:
        with closing(_readonly_connection(database_path)) as source, closing(sqlite3.connect(backup_path)) as destination:
            source.backup(destination)
            destination.commit()
        _integrity_check(backup_path)
        metadata = {
            "manifest_version": MANIFEST_VERSION,
            "alembic_version": ALEMBIC_VERSION,
            "sqlite_version": sqlite3.sqlite_version,
            "oai_version": OAI_VERSION,
            "backup_reason": BACKUP_REASON,
            "platform": {
                "operating_system": platform.system(),
                "python_version": platform.python_version(),
            },
            "database_name": database_path.name,
            "backup_filename": backup_name,
            "sha256": _sha256(backup_path),
            "timestamp": timestamp.isoformat(),
            "target_alembic_revision": TARGET_REVISION,
        }
        _append_manifest(backup_directory / BACKUP_MANIFEST, metadata)
        return backup_path, metadata
    except Exception:
        backup_path.unlink(missing_ok=True)
        raise


def _append_manifest(manifest_path: Path, metadata: dict[str, object]) -> None:
    entries: list[dict[str, object]] = []
    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            entries = existing["backups"]
        except (json.JSONDecodeError, KeyError, TypeError) as error:
            raise AdoptionError(f"Invalid backup manifest: {manifest_path}") from error
    entries.append(metadata)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=manifest_path.parent, delete=False) as temporary:
        json.dump({"backups": entries}, temporary, indent=2)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(manifest_path)


@contextmanager
def _database_environment(database_path: Path) -> Iterator[None]:
    previous = os.environ.get("OAI_DATABASE_URL")
    os.environ["OAI_DATABASE_URL"] = f"sqlite:///{database_path.resolve().as_posix()}"
    from app.core.config import get_settings

    get_settings.cache_clear()
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("OAI_DATABASE_URL", None)
        else:
            os.environ["OAI_DATABASE_URL"] = previous
        get_settings.cache_clear()


def _alembic_config() -> Config:
    repository_root = Path(__file__).resolve().parents[2]
    return Config(str(repository_root / "alembic.ini"))


def stamp_and_verify(database_path: Path) -> None:
    """Stamp the target revision without running an Alembic upgrade."""
    with _database_environment(database_path):
        configuration = _alembic_config()
        command.stamp(configuration, TARGET_REVISION)
        command.current(configuration)
    with closing(_readonly_connection(database_path)) as connection:
        current_revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    if current_revision != TARGET_REVISION:
        raise AdoptionError(f"Alembic current is {current_revision!r}, expected {TARGET_REVISION!r}")


def adopt_database(database_path: Path, backup_directory: Path, dry_run: bool = False) -> dict[str, object]:
    """Validate, back up, and stamp an unmanaged verified database."""
    database_path = database_path.resolve()
    validate_database(database_path)
    revision = managed_revision(database_path)
    if revision is not None:
        return {"status": "already_managed", "revision": revision, "database": database_path.name}
    if dry_run:
        return {"status": "ready", "revision": TARGET_REVISION, "database": database_path.name, "dry_run": True}
    backup_path, metadata = create_backup(database_path, backup_directory.resolve())
    validate_database(database_path)
    if managed_revision(database_path) is not None:
        raise AdoptionError("Database became managed before it could be stamped")
    stamp_and_verify(database_path)
    return {"status": "adopted", "revision": TARGET_REVISION, "backup": str(backup_path), "manifest": metadata}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safely adopt an O-AI 0.6.1 SQLite database into Alembic.")
    parser.add_argument("--database", type=Path, required=True, help="Path to the verified existing SQLite database.")
    parser.add_argument("--backup-dir", type=Path, default=Path("backups"), help="Directory for verified backups and manifest.json.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and report readiness without creating a backup or stamping.")
    return parser.parse_args()


def main() -> int:
    script_backend = Path(__file__).resolve().parents[1]
    if str(script_backend) not in sys.path:
        sys.path.insert(0, str(script_backend))
    arguments = parse_arguments()
    try:
        result = adopt_database(arguments.database, arguments.backup_dir, arguments.dry_run)
    except AdoptionError as error:
        print(f"Adoption refused: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
