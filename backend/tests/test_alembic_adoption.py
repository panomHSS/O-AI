import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


def _load_adoption_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "adopt_alembic_baseline.py"
    specification = importlib.util.spec_from_file_location("adopt_alembic_baseline", script_path)
    module = importlib.util.module_from_spec(specification)
    assert specification.loader is not None
    specification.loader.exec_module(module)
    return module


adoption = _load_adoption_module()


class AlembicAdoptionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.database_path = self.root / "existing-oai.db"
        self.backup_directory = self.root / "backups"
        self._create_baseline_database()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _create_baseline_database(self) -> None:
        config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        import os
        from app.core.config import get_settings

        previous = os.environ.get("OAI_DATABASE_URL")
        os.environ["OAI_DATABASE_URL"] = f"sqlite:///{self.database_path.as_posix()}"
        get_settings.cache_clear()
        try:
            command.upgrade(config, "head")
        finally:
            if previous is None:
                os.environ.pop("OAI_DATABASE_URL", None)
            else:
                os.environ["OAI_DATABASE_URL"] = previous
            get_settings.cache_clear()
        engine = create_engine(f"sqlite:///{self.database_path.as_posix()}")
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE alembic_version"))
        engine.dispose()

    def test_validator_accepts_complete_unmanaged_baseline(self) -> None:
        adoption.validate_database(self.database_path)
        self.assertIsNone(adoption.managed_revision(self.database_path))

    def test_dry_run_only_reports_readiness(self) -> None:
        original_hash = adoption._sha256(self.database_path)
        result = adoption.adopt_database(self.database_path, self.backup_directory, dry_run=True)
        self.assertEqual(result["status"], "ready")
        self.assertFalse(self.backup_directory.exists())
        self.assertIsNone(adoption.managed_revision(self.database_path))
        self.assertEqual(adoption._sha256(self.database_path), original_hash)

    def test_backup_is_verified_and_recorded_in_manifest(self) -> None:
        backup_path, metadata = adoption.create_backup(self.database_path, self.backup_directory)
        self.assertTrue(backup_path.is_file())
        adoption._integrity_check(backup_path)
        manifest = json.loads((self.backup_directory / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["backups"], [metadata])
        self.assertEqual(metadata["manifest_version"], 1)
        self.assertTrue(metadata["alembic_version"])
        self.assertTrue(metadata["sqlite_version"])
        self.assertEqual(metadata["oai_version"], adoption.OAI_VERSION)
        self.assertEqual(metadata["backup_reason"], "baseline_adoption")
        self.assertTrue(metadata["platform"]["operating_system"])
        self.assertTrue(metadata["platform"]["python_version"])
        self.assertEqual(metadata["target_alembic_revision"], adoption.TARGET_REVISION)
        self.assertEqual(metadata["sha256"], adoption._sha256(backup_path))

    def test_adoption_stamps_once_and_repeated_adoption_is_a_no_op(self) -> None:
        result = adoption.adopt_database(self.database_path, self.backup_directory)
        self.assertEqual(result["status"], "adopted")
        self.assertEqual(adoption.managed_revision(self.database_path), adoption.TARGET_REVISION)
        repeated = adoption.adopt_database(self.database_path, self.backup_directory)
        self.assertEqual(repeated["status"], "already_managed")
        self.assertEqual(len(list(self.backup_directory.glob("*.db"))), 1)

    def test_validator_rejects_incomplete_or_unsupported_schemas(self) -> None:
        engine = create_engine(f"sqlite:///{self.database_path.as_posix()}")
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE document_chunks"))
        engine.dispose()
        with self.assertRaises(adoption.AdoptionError):
            adoption.validate_database(self.database_path)

    def test_validator_rejects_an_unknown_alembic_revision(self) -> None:
        engine = create_engine(f"sqlite:///{self.database_path.as_posix()}")
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
            connection.execute(text("INSERT INTO alembic_version VALUES ('other_revision')"))
        engine.dispose()
        with self.assertRaises(adoption.AdoptionError):
            adoption.adopt_database(self.database_path, self.backup_directory)
        self.assertFalse(self.backup_directory.exists())
