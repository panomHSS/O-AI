import tempfile
import unittest
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.db.session import create_database_engine, initialize_test_database
from app.models.message import Message
from app.models.message_citation import MessageCitation
from app.repositories.conversations import ConversationRepository
from app.repositories.message_citations import CitationSnapshot, MAX_CITATIONS_PER_MESSAGE, MessageCitationRepository
from app.services.chat import ChatService
from app.services.conversations import ConversationService
from app.services.knowledge_answer import KnowledgeAnswerService
from app.services.knowledge_intelligence import CitationEngine, ConfidenceEvaluator, ConflictDetector, ContextBuilder, EvidenceRanker, GroundedPromptBuilder, IntentAnalyzer, RetrievalPlanner


class MessageCitationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.engine = create_database_engine(f"sqlite:///{(Path(self.temporary_directory.name) / 'citations.db').as_posix()}")
        initialize_test_database(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.sessions = []

    def tearDown(self) -> None:
        for session in self.sessions:
            session.close()
        self.engine.dispose()
        self.temporary_directory.cleanup()

    def _service(self, citations: MessageCitationRepository | None = None) -> ConversationService:
        session = self.Session()
        self.sessions.append(session)
        return ConversationService(ConversationRepository(session), ChatService(None), 2, citations or MessageCitationRepository(session))

    @staticmethod
    def _snapshot(index: int) -> CitationSnapshot:
        excerpt = f"Evidence excerpt {index}"
        return CitationSnapshot(f"S{index}", f"00000000-0000-0000-0000-{index:012d}", f"file-{index}.txt", f"notes/file-{index}.txt", f"line {index}", excerpt, f"{index:064x}", 0.5)

    def test_snapshots_are_ordered_and_exposed_with_metadata(self) -> None:
        service = self._service()
        conversation, _ = service.begin_turn("Question")
        service.complete_turn(conversation.id, "Answer S1 S2", [self._snapshot(2), self._snapshot(1)])

        detail = service.get_conversation(conversation.id)
        citations = detail.messages[-1].citations
        self.assertEqual([citation.citation_id for citation in citations], ["S2", "S1"])
        self.assertEqual([citation.order for citation in citations], [1, 2])
        self.assertEqual(citations[0].excerpt, "Evidence excerpt 2")
        self.assertEqual(citations[0].excerpt_hash, f"{2:064x}")
        self.assertEqual(citations[0].evidence_type, "document_chunk")
        self.assertEqual(citations[0].confidence, 0.5)

    def test_message_and_citations_roll_back_together_on_failure(self) -> None:
        session = self.Session()
        self.sessions.append(session)

        class FailingCitationRepository(MessageCitationRepository):
            def add_snapshots(self, message, snapshots):
                super().add_snapshots(message, snapshots)
                raise RuntimeError("citation write failed")

        service = ConversationService(ConversationRepository(session), ChatService(None), 2, FailingCitationRepository(session))
        conversation, _ = service.begin_turn("Question")
        with self.assertRaisesRegex(RuntimeError, "citation write failed"):
            service.complete_turn(conversation.id, "Answer", [self._snapshot(1)])
        self.assertEqual(session.scalar(select(func.count(Message.id)).where(Message.role == "assistant")), 0)
        self.assertEqual(session.scalar(select(func.count(MessageCitation.id))), 0)

    def test_citation_limit_and_message_cascade_are_enforced(self) -> None:
        service = self._service()
        conversation, _ = service.begin_turn("Question")
        with self.assertRaises(ValueError):
            service.complete_turn(conversation.id, "Answer", [self._snapshot(index) for index in range(MAX_CITATIONS_PER_MESSAGE + 1)])
        service.complete_turn(conversation.id, "Answer", [self._snapshot(1)])
        service.delete_conversation(conversation.id)
        with self.Session() as session:
            self.assertEqual(session.scalar(select(func.count(MessageCitation.id))), 0)

    def test_knowledge_answer_persists_its_validated_evidence(self) -> None:
        class Provider:
            def generate_reply(self, message: str) -> str:
                return "The answer is supported by S1."

        class KnowledgeRepository:
            def search(self, query: str, limit: int):
                return [{
                    "document_id": "00000000-0000-0000-0000-000000000001", "chunk_id": "chunk-1", "file_name": "manual.txt",
                    "source_path": "manual.txt", "source_locator": "line 1", "content": "Verified evidence for the answer.",
                    "relevance_score": 1.0, "file_extension": ".txt",
                }]

        conversation_service = self._service()
        answer_service = KnowledgeAnswerService(
            KnowledgeRepository(), conversation_service, ChatService(Provider()), IntentAnalyzer(), RetrievalPlanner(1), EvidenceRanker(1),
            ConflictDetector(), ContextBuilder(1000), GroundedPromptBuilder(), CitationEngine(), ConfidenceEvaluator(), 1, 1,
        )
        response = answer_service.answer("What is verified?", None)
        detail = conversation_service.get_conversation(response.conversation_id)
        citations = detail.messages[-1].citations
        self.assertEqual([citation.citation_id for citation in citations], ["S1"])
        self.assertEqual(citations[0].excerpt, "Verified evidence for the answer.")
