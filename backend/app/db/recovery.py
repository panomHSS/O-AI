"""Isolated SQLite recovery primitives; never target the configured production database."""

from __future__ import annotations

import hashlib
import os
import sqlite3
import tempfile
from contextlib import closing
from dataclasses import dataclass, replace
from pathlib import Path
from uuid import uuid4

from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.db.verification import DatabaseVerificationError, verify_database


class RecoveryError(RuntimeError):
    """An isolated recovery operation could not be verified safely."""


@dataclass(frozen=True)
class RecoveryArtifact:
    """Non-sensitive metadata for a verified SQLite recovery artifact."""

    path: Path
    verified: bool
    integrity_check: str
    revision: str
    fingerprint: str


_BACKEND_OR_APPLICATION_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = (
    _BACKEND_OR_APPLICATION_ROOT.parent
    if (_BACKEND_OR_APPLICATION_ROOT.parent / "backend").is_dir()
    else _BACKEND_OR_APPLICATION_ROOT
)
PRODUCTION_DATABASE_PATH = REPOSITORY_ROOT / "data" / "oai.db"


def _resolved(path: Path, *, base: Path = REPOSITORY_ROOT) -> Path:
    """Resolve paths from the application root, never the caller's CWD."""
    return (path if path.is_absolute() else base / path).resolve()


def _production_path() -> Path | None:
    database_url = make_url(get_settings().oai_database_url)
    if (
        not database_url.drivername.startswith("sqlite")
        or not database_url.database
        or database_url.database == ":memory:"
    ):
        return None
    return _resolved(Path(database_url.database))


def _guard(path: Path) -> Path:
    resolved = _resolved(path)
    protected_paths = {_resolved(PRODUCTION_DATABASE_PATH)}
    configured_path = _production_path()
    if configured_path is not None:
        protected_paths.add(configured_path)
    if resolved in protected_paths:
        raise RecoveryError("Recovery operations cannot use the production database path.")
    return resolved


def _connect(path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    if readonly:
        return sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    return sqlite3.connect(path)


def _file_identity(path: Path) -> tuple[int, int] | None:
    try:
        stat = path.stat()
    except FileNotFoundError:
        return None
    return stat.st_dev, stat.st_ino


def _remove_owned_temporary(path: Path, identity: tuple[int, int]) -> None:
    """Remove a temporary artifact only when it is still the file we created."""
    if _file_identity(path) == identity:
        path.unlink()


def _new_temporary_destination(destination: Path) -> tuple[Path, tuple[int, int]]:
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".partial",
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    identity = _file_identity(temporary)
    if identity is None:  # pragma: no cover - defensive filesystem failure
        raise RecoveryError("Recovery temporary artifact could not be created.")
    return temporary, identity


def _finalize_owned_temporary(
    temporary: Path,
    temporary_identity: tuple[int, int],
    destination: Path,
) -> None:
    """Atomically publish a temporary artifact without overwriting a destination."""
    if _file_identity(temporary) != temporary_identity:
        raise RecoveryError("Recovery temporary artifact ownership was lost.")
    try:
        os.link(temporary, destination)
    except FileExistsError as error:
        raise RecoveryError("Backup destination already exists.") from error
    except OSError as error:
        raise RecoveryError("Recovery artifact could not be finalized safely.") from error
    _remove_owned_temporary(temporary, temporary_identity)


def _fingerprint_rows(connection: sqlite3.Connection) -> tuple[object, ...]:
    table_names = sorted(
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_schema "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
            "AND name NOT LIKE 'document_chunks_fts_%'"
        )
    )
    row_counts = [
        (table, connection.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0])
        for table in table_names
    ]
    relationships: list[tuple[object, ...]] = []
    for table, columns in (
        ("messages", "id, conversation_id"),
        (
            "message_citations",
            "id, message_id, citation_id, document_id, source_path, source_locator, citation_order",
        ),
        ("memory_versions", "id, memory_id, version, state"),
        ("memories", "id, active_version_id, pending_version_id, state"),
        ("projects", "id, current_revision, status"),
        ("project_revisions", "id, project_id, revision_number, status"),
        ("conversations", "id, project_id"),
        ("document_chunks", "id, document_id, chunk_index"),
    ):
        relationships.extend(
            (table, *row)
            for row in connection.execute(f"SELECT {columns} FROM {table} ORDER BY 1")
        )
    revisions = tuple(row[0] for row in connection.execute("SELECT version_num FROM alembic_version"))
    return (tuple(table_names), tuple(row_counts), tuple(relationships), revisions)


def fingerprint(path: Path) -> str:
    """Return a deterministic, non-content structural fingerprint."""
    path = _guard(path)
    if not path.is_file():
        raise RecoveryError("Recovery database does not exist.")
    try:
        with closing(_connect(path, readonly=True)) as connection:
            material = _fingerprint_rows(connection)
    except sqlite3.Error as error:
        raise RecoveryError("Recovery fingerprint generation failed.") from error
    return hashlib.sha256(repr(material).encode("utf-8")).hexdigest()


def validate_memory_invariants(path: Path) -> None:
    """Validate active/pending memory pointers without reading memory values."""
    path = _guard(path)
    try:
        with closing(_connect(path, readonly=True)) as connection:
            invalid_pointer = connection.execute(
                "SELECT m.id FROM memories AS m "
                "LEFT JOIN memory_versions AS active ON active.id = m.active_version_id "
                "LEFT JOIN memory_versions AS pending ON pending.id = m.pending_version_id "
                "WHERE (m.active_version_id IS NOT NULL "
                "AND (active.id IS NULL OR active.memory_id != m.id OR active.state != 'CONFIRMED')) "
                "OR (m.pending_version_id IS NOT NULL "
                "AND (pending.id IS NULL OR pending.memory_id != m.id OR pending.state != 'PENDING'))"
            ).fetchone()
            invalid_versions = connection.execute(
                "SELECT m.id FROM memories AS m "
                "LEFT JOIN memory_versions AS v ON v.memory_id = m.id "
                "GROUP BY m.id, m.current_version "
                "HAVING count(v.id) = 0 OR min(v.version) != 1 "
                "OR max(v.version) != m.current_version "
                "OR count(*) != count(DISTINCT version)"
            ).fetchone()
            invalid_state = connection.execute(
                """
                SELECT m.id
                FROM memories AS m
                LEFT JOIN memory_versions AS active ON active.id = m.active_version_id
                LEFT JOIN memory_versions AS pending ON pending.id = m.pending_version_id
                WHERE m.state NOT IN ('PENDING', 'CONFIRMED', 'REJECTED', 'ARCHIVED')
                   OR (
                        m.state = 'PENDING'
                        AND (
                            m.active_version_id IS NOT NULL
                            OR pending.id IS NULL
                            OR pending.memory_id != m.id
                            OR pending.state != 'PENDING'
                        )
                    )
                   OR (
                        m.state = 'CONFIRMED'
                        AND (
                            active.id IS NULL
                            OR active.memory_id != m.id
                            OR active.state != 'CONFIRMED'
                            OR (
                                m.pending_version_id IS NOT NULL
                                AND (pending.memory_id != m.id OR pending.state != 'PENDING')
                            )
                        )
                    )
                   OR (
                        m.state = 'REJECTED'
                        AND (
                            m.active_version_id IS NOT NULL
                            OR m.pending_version_id IS NOT NULL
                            OR NOT EXISTS (
                                SELECT 1 FROM memory_versions AS rejected
                                WHERE rejected.memory_id = m.id AND rejected.state = 'REJECTED'
                            )
                        )
                    )
                   OR (
                        m.state = 'ARCHIVED'
                        AND (
                            m.pending_version_id IS NOT NULL
                            OR NOT EXISTS (
                                SELECT 1 FROM memory_versions AS archived
                                WHERE archived.memory_id = m.id AND archived.state = 'ARCHIVED'
                            )
                            OR (
                                m.active_version_id IS NULL
                                AND EXISTS (
                                    SELECT 1 FROM memory_versions AS non_archived
                                    WHERE non_archived.memory_id = m.id
                                      AND non_archived.state != 'ARCHIVED'
                                )
                            )
                            OR (
                                m.active_version_id IS NOT NULL
                                AND (
                                    active.memory_id != m.id
                                    OR active.state != 'CONFIRMED'
                                )
                            )
                        )
                    )
                """
            ).fetchone()
            invalid_version_state = connection.execute(
                "SELECT id FROM memory_versions "
                "WHERE state NOT IN ('PENDING', 'CONFIRMED', 'REJECTED', 'ARCHIVED')"
            ).fetchone()
    except sqlite3.Error as error:
        raise RecoveryError("Memory recovery invariant validation failed.") from error
    if any((invalid_pointer, invalid_versions, invalid_state, invalid_version_state)):
        raise RecoveryError("Memory recovery invariants are invalid.")
    _verify_memory_immutability_behavior(path)


def _verify_memory_immutability_behavior(path: Path) -> None:
    """Probe immutable snapshots inside a rolled-back isolated transaction."""
    probe_memory_id = f"recovery-probe-{uuid4()}"
    probe_version_id = f"recovery-probe-version-{uuid4()}"
    with closing(_connect(path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("SAVEPOINT recovery_immutability_probe")
        try:
            connection.execute(
                "INSERT INTO memories "
                "(id, key, value, value_type, state, current_version, active_version_id, "
                "pending_version_id, created_at, updated_at) "
                "VALUES (?, ?, ?, 'STRING', 'PENDING', 1, NULL, NULL, "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                (probe_memory_id, probe_memory_id, '"probe"'),
            )
            connection.execute(
                "INSERT INTO memory_versions "
                "(id, memory_id, version, key, value, value_type, state, change_reason, "
                "decision_comment, evidence_snapshot, created_by, proposed_by, proposed_at, "
                "decided_by, decided_at, created_at) "
                "VALUES (?, ?, 1, ?, ?, 'STRING', 'PENDING', 'recovery probe', "
                "NULL, NULL, 'owner', 'owner', CURRENT_TIMESTAMP, NULL, NULL, CURRENT_TIMESTAMP)",
                (probe_version_id, probe_memory_id, probe_memory_id, '"probe"'),
            )
            try:
                connection.execute(
                    "UPDATE memory_versions SET value = ? WHERE id = ?",
                    ('"changed"', probe_version_id),
                )
            except sqlite3.DatabaseError:
                mutation_rejected = True
            else:
                mutation_rejected = False
        except sqlite3.Error as error:
            raise RecoveryError("Memory immutability verification failed.") from error
        finally:
            connection.execute("ROLLBACK TO recovery_immutability_probe")
            connection.execute("RELEASE recovery_immutability_probe")
    if not mutation_rejected:
        raise RecoveryError("Memory immutability protection is ineffective.")


def validate_fts(path: Path) -> None:
    """Confirm the required FTS5 virtual table can execute a harmless query."""
    path = _guard(path)
    try:
        with closing(_connect(path, readonly=True)) as connection:
            connection.execute(
                "SELECT count(*) FROM document_chunks_fts "
                "WHERE document_chunks_fts MATCH 'recoveryftsprobe'"
            ).fetchone()
    except sqlite3.Error as error:
        raise RecoveryError("FTS recovery validation failed.") from error


def validate_citation_invariants(path: Path) -> None:
    """Validate citation/message relationships and ordering without excerpts."""
    path = _guard(path)
    try:
        with closing(_connect(path, readonly=True)) as connection:
            invalid_reference = connection.execute(
                "SELECT c.id FROM message_citations AS c "
                "LEFT JOIN messages AS m ON m.id = c.message_id "
                "LEFT JOIN conversations AS x ON x.id = m.conversation_id "
                "WHERE m.id IS NULL OR x.id IS NULL OR m.role != 'assistant'"
            ).fetchone()
            invalid_order = connection.execute(
                "SELECT message_id FROM message_citations GROUP BY message_id "
                "HAVING min(citation_order) < 1 "
                "OR count(*) != count(DISTINCT citation_order)"
            ).fetchone()
    except sqlite3.Error as error:
        raise RecoveryError("Citation recovery invariant validation failed.") from error
    if invalid_reference is not None or invalid_order is not None:
        raise RecoveryError("Citation recovery invariants are invalid.")


def validate_project_invariants(path: Path) -> None:
    """Validate Project state and append-only snapshots without reading content fields."""
    path = _guard(path)
    try:
        with closing(_connect(path, readonly=True)) as connection:
            invalid = connection.execute(
                "SELECT p.id FROM projects p LEFT JOIN project_revisions r ON r.project_id = p.id "
                "GROUP BY p.id, p.current_revision, p.status HAVING p.status NOT IN ('ACTIVE','PAUSED','COMPLETED','ARCHIVED') "
                "OR count(r.id) = 0 OR min(r.revision_number) != 1 OR max(r.revision_number) != p.current_revision "
                "OR count(r.id) != count(DISTINCT r.revision_number)"
            ).fetchone()
            mismatch = connection.execute(
                "SELECT p.id FROM projects p JOIN project_revisions r ON r.project_id=p.id AND r.revision_number=p.current_revision "
                "WHERE p.status != r.status OR p.title != r.title OR p.objective != r.objective "
                "OR NOT (p.current_summary IS r.current_summary) OR NOT (p.next_action IS r.next_action)"
            ).fetchone()
    except sqlite3.Error as error:
        raise RecoveryError("Project recovery invariant validation failed.") from error
    if invalid is not None or mismatch is not None:
        raise RecoveryError("Project recovery invariants are invalid.")
    _verify_project_immutability_behavior(path)


def _verify_project_immutability_behavior(path: Path) -> None:
    with closing(_connect(path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("SAVEPOINT project_immutability_probe")
        try:
            connection.execute("INSERT INTO projects (id,title,objective,status,current_revision,created_at,updated_at) VALUES ('recovery-project-probe','probe','probe','ACTIVE',1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)")
            connection.execute("INSERT INTO project_revisions (id,project_id,revision_number,title,objective,status,change_note,created_at) VALUES ('recovery-project-revision-probe','recovery-project-probe',1,'probe','probe','ACTIVE','probe',CURRENT_TIMESTAMP)")
            try:
                connection.execute("UPDATE project_revisions SET title='changed' WHERE id='recovery-project-revision-probe'")
            except sqlite3.DatabaseError:
                update_rejected = True
            else:
                update_rejected = False
            try:
                connection.execute("DELETE FROM project_revisions WHERE id='recovery-project-revision-probe'")
            except sqlite3.DatabaseError:
                delete_rejected = True
            else:
                delete_rejected = False
        except sqlite3.Error as error:
            raise RecoveryError("Project immutability verification failed.") from error
        finally:
            connection.execute("ROLLBACK TO project_immutability_probe")
            connection.execute("RELEASE project_immutability_probe")
    if not update_rejected or not delete_rejected:
        raise RecoveryError("Project immutability protection is ineffective.")


def verify(path: Path) -> RecoveryArtifact:
    """Verify an isolated database and return only non-sensitive metadata."""
    path = _guard(path)
    try:
        with closing(_connect(path, readonly=True)) as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            foreign_key_violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        if integrity != "ok" or foreign_key_violations:
            raise RecoveryError("Recovery database integrity validation failed.")
        result = verify_database(f"sqlite:///{path.as_posix()}")
        validate_fts(path)
        validate_memory_invariants(path)
        validate_citation_invariants(path)
        validate_project_invariants(path)
    except (sqlite3.Error, DatabaseVerificationError) as error:
        raise RecoveryError("Recovery database verification failed.") from error
    return RecoveryArtifact(path, True, integrity, result.revision, fingerprint(path))


def backup(source: Path, destination: Path) -> RecoveryArtifact:
    """Create and independently verify a new isolated SQLite backup."""
    source, destination = _guard(source), _guard(destination)
    if source == destination:
        raise RecoveryError("Backup source and destination must differ.")
    if not source.is_file() or destination.exists():
        raise RecoveryError("Backup paths are unsafe.")
    if not destination.parent.is_dir():
        raise RecoveryError("Backup destination parent must exist.")
    temporary, temporary_identity = _new_temporary_destination(destination)
    try:
        with closing(_connect(source, readonly=True)) as origin:
            with closing(_connect(temporary)) as target:
                origin.backup(target)
        artifact = verify(temporary)
        _finalize_owned_temporary(temporary, temporary_identity, destination)
        return replace(artifact, path=destination)
    except sqlite3.Error as error:
        _remove_owned_temporary(temporary, temporary_identity)
        raise RecoveryError("SQLite backup failed.") from error
    except Exception:
        _remove_owned_temporary(temporary, temporary_identity)
        raise


def restore(artifact: Path, destination: Path) -> RecoveryArtifact:
    """Restore a verified artifact to a new isolated SQLite database path."""
    verify(artifact)
    return backup(artifact, destination)
