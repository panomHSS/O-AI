# Database migrations and existing-database adoption

O-AI 0.6.2A introduces Alembic revision `0001_v061_baseline` for the verified O-AI 0.6.1 SQLite schema. Application startup opens the configured SQLite database in read-only mode and verifies the baseline schema and revision; it never runs Alembic migrations, creates tables, stamps revisions, or writes backups.

Startup refuses missing, unmanaged, incompatible, or differently stamped databases. The health endpoint reports the verified `database_revision`.

To run the same read-only check without starting the API:

```powershell
python backend/scripts/verify_database.py --database <path-to-oai.db>
```

## Fresh databases

Set `OAI_DATABASE_URL` to the intended empty SQLite database, then run from the repository root:

```powershell
python -m alembic -c alembic.ini upgrade head
```

## Adopt a verified 0.6.1 database

Adoption is only for an existing database that already has the exact 0.6.1 schema. It validates the schema in SQLite read-only mode, including relational tables, columns, types, primary and foreign keys, indexes, unique constraints, and the FTS5 definition. It never runs a schema upgrade.

First run a read-only readiness check:

```powershell
python backend/scripts/adopt_alembic_baseline.py --database <path-to-oai.db> --dry-run
```

After reviewing the result, run adoption with a deliberate backup location:

```powershell
python backend/scripts/adopt_alembic_baseline.py --database <path-to-oai.db> --backup-dir backups
```

The utility creates a collision-resistant backup filename with `sqlite3.Connection.backup()`, verifies the copy with `PRAGMA integrity_check`, writes backup metadata to `backups/manifest.json`, then stamps `0001_v061_baseline`. A database already stamped with that exact revision exits successfully without a backup or any changes. Any other existing Alembic revision is refused and is never overwritten.

Each item in the manifest's `backups` list contains:

- `manifest_version`: manifest record format version; currently integer `1`.
- `alembic_version`: installed Alembic package version used for adoption.
- `sqlite_version`: SQLite library version used to create and verify the backup.
- `oai_version`: O-AI release version of the adoption tool.
- `backup_reason`: operation reason; baseline adoption uses `baseline_adoption`.
- `platform.operating_system`: operating system reported by Python.
- `platform.python_version`: Python runtime version reported by Python.
- `database_name`: source database filename only.
- `backup_filename`: generated backup filename in the backup directory.
- `sha256`: SHA-256 checksum of the completed backup file.
- `timestamp`: UTC ISO-8601 backup creation timestamp.
- `target_alembic_revision`: Alembic revision stamped after successful backup and validation.

The `backups/` directory contains recoverable database copies and should be retained outside source control or backed up according to the deployment policy.
