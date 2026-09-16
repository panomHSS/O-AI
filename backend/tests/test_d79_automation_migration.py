import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings


class D79AutomationMigrationTests(unittest.TestCase):
    def test_upgrade_head_creates_exact_automation_foundation_and_downgrades(self):
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "d79.db"
            database_url = f"sqlite:///{db_path.as_posix()}"
            config = Config(str(root / "alembic.ini"))

            with patch.dict(
                os.environ,
                {"OAI_DATABASE_URL": database_url},
                clear=False,
            ):
                get_settings.cache_clear()
                try:
                    command.upgrade(config, "head")

                    engine = create_engine(database_url)
                    try:
                        inspector = inspect(engine)
                        self.assertIn(
                            "automation_definitions",
                            inspector.get_table_names(),
                        )
                        self.assertIn(
                            "automation_runs",
                            inspector.get_table_names(),
                        )

                        definition_columns = {
                            column["name"]
                            for column in inspector.get_columns(
                                "automation_definitions"
                            )
                        }
                        self.assertEqual(
                            definition_columns,
                            {
                                "id",
                                "contract_version",
                                "kind",
                                "message",
                                "schedule_kind",
                                "run_at_iso",
                                "daily_local_time",
                                "timezone",
                                "max_runs",
                                "definition_digest",
                                "status",
                                "approval_expires_at",
                                "approved_at",
                                "terminal_at",
                                "next_due_at_utc",
                                "created_at",
                                "updated_at",
                            },
                        )

                        run_columns = {
                            column["name"]
                            for column in inspector.get_columns(
                                "automation_runs"
                            )
                        }
                        self.assertNotIn("message", run_columns)
                        self.assertEqual(
                            run_columns,
                            {
                                "id",
                                "automation_id",
                                "definition_digest",
                                "due_at_utc",
                                "status",
                                "claimed_at",
                                "delivered_at",
                                "created_at",
                                "updated_at",
                            },
                        )

                        unique_names = {
                            item["name"]
                            for item in inspector.get_unique_constraints(
                                "automation_runs"
                            )
                        }
                        self.assertIn(
                            "uq_automation_runs_automation_due",
                            unique_names,
                        )
                    finally:
                        engine.dispose()

                    command.downgrade(
                        config,
                        "0010_oauth_credentials",
                    )
                    engine = create_engine(database_url)
                    try:
                        tables = inspect(engine).get_table_names()
                        self.assertNotIn(
                            "automation_definitions",
                            tables,
                        )
                        self.assertNotIn("automation_runs", tables)
                        self.assertIn("oauth_credentials", tables)
                    finally:
                        engine.dispose()
                finally:
                    get_settings.cache_clear()


if __name__ == "__main__":
    unittest.main()
