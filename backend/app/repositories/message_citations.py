from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.message import Message
from app.models.message_citation import MessageCitation


MAX_CITATIONS_PER_MESSAGE = 12


@dataclass(frozen=True)
class CitationSnapshot:
    citation_id: str
    document_id: str
    file_name: str
    source_path: str
    source_locator: str
    excerpt: str
    excerpt_hash: str
    confidence: float
    evidence_type: str = "document_chunk"


class MessageCitationRepository:
    """Persists immutable evidence snapshots within the caller's transaction."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add_snapshots(self, message: Message, snapshots: list[CitationSnapshot]) -> list[MessageCitation]:
        if len(snapshots) > MAX_CITATIONS_PER_MESSAGE:
            raise ValueError(f"At most {MAX_CITATIONS_PER_MESSAGE} citations can be stored for one message.")
        citations = [
            MessageCitation(
                message_id=message.id,
                citation_order=index,
                citation_id=snapshot.citation_id,
                document_id=snapshot.document_id,
                file_name=snapshot.file_name,
                source_path=snapshot.source_path,
                source_locator=snapshot.source_locator,
                excerpt=snapshot.excerpt,
                excerpt_hash=snapshot.excerpt_hash,
                confidence=snapshot.confidence,
                evidence_type=snapshot.evidence_type,
            )
            for index, snapshot in enumerate(snapshots, 1)
        ]
        self._session.add_all(citations)
        self._session.flush()
        return citations
