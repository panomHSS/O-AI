from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base


def ensure_sqlite_directory(database_url: str) -> None:
    url = make_url(database_url)
    if (
        url.drivername.startswith("sqlite")
        and url.database
        and url.database != ":memory:"
    ):
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)


def create_database_engine(database_url: str) -> Engine:
    ensure_sqlite_directory(database_url)
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args)

    if database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection, _) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


settings = get_settings()
engine = create_database_engine(settings.oai_database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def initialize_test_database(database_engine: Engine) -> None:
    """Create the schema only for isolated temporary test databases."""
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=database_engine)
    initialize_knowledge_fts(database_engine)


def initialize_knowledge_fts(database_engine: Engine) -> None:
    """Create the SQLite FTS5 table separately from ORM-managed tables."""
    if database_engine.dialect.name != "sqlite":
        return

    with database_engine.begin() as connection:
        connection.execute(
            text(
                "CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts "
                "USING fts5(content, document_id UNINDEXED, chunk_id UNINDEXED, source_locator UNINDEXED)"
            )
        )


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
