from sqlalchemy.orm import Session

from app.embeddings.base import EmbeddingPort
from app.search.base import KnowledgeSearchPort
from app.search.postgresql_vector import (
    PostgreSQLVectorSearchAdapter,
)
from app.search.sqlite_fts5 import SQLiteFTS5SearchAdapter


def create_knowledge_search(
    session: Session,
    *,
    embeddings: EmbeddingPort | None = None,
) -> KnowledgeSearchPort:
    """Create the derived-search adapter for the active database."""

    dialect_name = session.get_bind().dialect.name

    if dialect_name == "sqlite":
        return SQLiteFTS5SearchAdapter(
            session
        )

    if dialect_name == "postgresql":
        if embeddings is None:
            raise ValueError(
                "PostgreSQL knowledge search requires "
                "an embedding provider."
            )

        return PostgreSQLVectorSearchAdapter(
            session,
            embeddings,
        )

    raise ValueError(
        "Unsupported knowledge-search database dialect: "
        f"{dialect_name}"
    )