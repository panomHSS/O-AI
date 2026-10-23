from __future__ import annotations

import os
import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.core.config import get_settings
from app.db.session import create_database_engine

REVISION = "0018_trusted_execution_experience_lifecycle"


def config() -> Config:
    root = Path(__file__).resolve().parents[2]
    return Config(str(root / "alembic.ini"))


def test_d186_fresh_database_has_exact_review_tables_and_head():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "d186-fresh.db"
        previous = os.environ.get("OAI_DATABASE_URL")
        os.environ["OAI_DATABASE_URL"] = f"sqlite:///{path.as_posix()}"
        get_settings.cache_clear()
        engine = None
        try:
            command.upgrade(config(), "head")
            engine = create_database_engine(os.environ["OAI_DATABASE_URL"])
            inspector = inspect(engine)
            tables = set(inspector.get_table_names())
            assert "execution_experience_reviews" in tables
            assert "execution_experience_review_events" in tables
            assert {
                item["name"]
                for item in inspector.get_indexes("execution_experience_reviews")
            } == {
                "ix_execution_experience_reviews_workspace_state",
                "ix_execution_experience_reviews_updated_at",
            }
            assert {
                item["name"]
                for item in inspector.get_indexes("execution_experience_review_events")
            } == {"ix_execution_experience_review_events_review_id"}
            with engine.connect() as connection:
                assert connection.scalar(
                    text("SELECT version_num FROM alembic_version")
                ) == REVISION
        finally:
            if engine is not None:
                engine.dispose()
            if previous is None:
                os.environ.pop("OAI_DATABASE_URL", None)
            else:
                os.environ["OAI_DATABASE_URL"] = previous
            get_settings.cache_clear()


def test_d186_upgrade_from_0016_preserves_existing_data():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "d186-upgrade.db"
        previous = os.environ.get("OAI_DATABASE_URL")
        os.environ["OAI_DATABASE_URL"] = f"sqlite:///{path.as_posix()}"
        get_settings.cache_clear()
        engine = None
        try:
            command.upgrade(config(), "0016_cognitive_quality_observability")
            engine = create_database_engine(os.environ["OAI_DATABASE_URL"])
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO conversations "
                        "(id,title,workspace_id,created_at,updated_at) "
                        "VALUES ('pre-d186','Existing','personal',"
                        "CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"
                    )
                )
            engine.dispose()
            engine = None
            command.upgrade(config(), "head")
            engine = create_database_engine(os.environ["OAI_DATABASE_URL"])
            with engine.connect() as connection:
                assert connection.scalar(
                    text("SELECT count(*) FROM conversations WHERE id='pre-d186'")
                ) == 1
                assert connection.scalar(
                    text("SELECT count(*) FROM execution_experience_reviews")
                ) == 0
                assert connection.scalar(
                    text("SELECT version_num FROM alembic_version")
                ) == REVISION
        finally:
            if engine is not None:
                engine.dispose()
            if previous is None:
                os.environ.pop("OAI_DATABASE_URL", None)
            else:
                os.environ["OAI_DATABASE_URL"] = previous
            get_settings.cache_clear()
