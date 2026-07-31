import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.db.verification import DatabaseVerificationError, DatabaseVerificationResult, TARGET_REVISION, verify_database
from app.main import app, lifespan


class StartupVerificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "verified-oai.db"
        self.database_url = f"sqlite:///{self.database_path.as_posix()}"
        self._upgrade_temporary_database()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _upgrade_temporary_database(self) -> None:
        previous = os.environ.get("OAI_DATABASE_URL")
        os.environ["OAI_DATABASE_URL"] = self.database_url
        from app.core.config import get_settings

        get_settings.cache_clear()
        try:
            command.upgrade(Config(str(Path(__file__).resolve().parents[2] / "alembic.ini")), "head")
        finally:
            if previous is None:
                os.environ.pop("OAI_DATABASE_URL", None)
            else:
                os.environ["OAI_DATABASE_URL"] = previous
            get_settings.cache_clear()

    def test_verifies_the_expected_schema_and_revision_read_only(self) -> None:
        original = self.database_path.read_bytes()
        result = verify_database(self.database_url)
        self.assertEqual(result.revision, TARGET_REVISION)
        self.assertEqual(self.database_path.read_bytes(), original)

    def test_rejects_missing_or_wrong_revision(self) -> None:
        engine = create_engine(self.database_url)
        with engine.begin() as connection:
            connection.execute(text("UPDATE alembic_version SET version_num = 'wrong_revision'"))
        engine.dispose()
        with self.assertRaises(DatabaseVerificationError):
            verify_database(self.database_url)

    def test_rejects_an_incompatible_schema(self) -> None:
        engine = create_engine(self.database_url)
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE document_chunks_fts"))
        engine.dispose()
        with self.assertRaises(DatabaseVerificationError):
            verify_database(self.database_url)

    def test_lifespan_runs_verification_without_initializing_database(self) -> None:
        async def run_lifespan() -> None:
            with patch("app.main.verify_database", return_value=DatabaseVerificationResult(TARGET_REVISION)) as verifier:
                async with lifespan(app):
                    self.assertEqual(app.state.database_revision, TARGET_REVISION)
                verifier.assert_called_once()

        asyncio.run(run_lifespan())
