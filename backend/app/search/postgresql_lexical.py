from sqlalchemy import text
from sqlalchemy.orm import Session


class PostgreSQLLexicalSearch:
    """PostgreSQL workspace-scoped full-text lexical knowledge retrieval."""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def search(
        self,
        workspace_id: str,
        query: str,
        limit: int,
    ) -> list[dict[str, object]]:
        statement = text(
            "WITH search_query AS ("
            "SELECT websearch_to_tsquery("
            "'simple', :query"
            ") AS query"
            ") "
            "SELECT "
            "documents.id AS document_id, "
            "documents.file_name, "
            "documents.source_path, "
            "documents.file_extension, "
            "document_chunks.id AS chunk_id, "
            "document_chunks.content, "
            "document_chunks.source_locator, "
            "ts_rank_cd("
            "to_tsvector("
            "'simple', document_chunks.content"
            "), "
            "search_query.query"
            ") AS relevance_score "
            "FROM document_chunks "
            "JOIN documents "
            "ON documents.id = "
            "document_chunks.document_id "
            "CROSS JOIN search_query "
            "WHERE documents.status = 'indexed' "
            "AND documents.workspace_id = :workspace_id "
            "AND to_tsvector("
            "'simple', document_chunks.content"
            ") @@ search_query.query "
            "ORDER BY relevance_score DESC, "
            "document_chunks.id ASC "
            "LIMIT :limit"
        )

        rows = self._session.execute(
            statement,
            {
                "workspace_id": workspace_id,
                "query": query,
                "limit": limit,
            },
        ).mappings()

        return [
            dict(row)
            for row in rows
        ]
