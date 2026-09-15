import unittest
from types import SimpleNamespace

from app.services.knowledge_answer import KnowledgeAnswerService


class RecordingRepository:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def search(
        self,
        query: str,
        limit: int,
    ) -> list[dict[str, object]]:
        self.queries.append(query)
        return []


class FakeConversations:

    def begin_turn(
        self,
        question,
        conversation_id,
        project_id,
    ):
        return (
            SimpleNamespace(
                id="11111111-1111-1111-1111-111111111111",
                project_id=None,
            ),
            [],
        )
    
    def resolve_project_context(
        self,
        conversation,
    ):
        return None

    def complete_turn(
        self,
        conversation_id,
        answer,
        snapshots,
    ) -> None:
        pass


class FakeAnalyzer:
    def analyze(self, question):
        return SimpleNamespace(
            question=question,
            important_terms=(),
        )


class FakePlanner:
    def plan(self, intent):
        return [
            "pump pressure problem",
            "centrifugal pump troubleshooting",
        ]


class EmptyRanker:
    def rank(
        self,
        question,
        important_terms,
        records,
    ):
        return [], 0, 0


class EmptyConflicts:
    def detect(
        self,
        selected,
        important_terms,
    ):
        return []


class EmptyContext:
    def build(self, selected):
        return []


class FakeConfidence:
    def evaluate(
        self,
        context,
        citations,
        conflicts,
    ):
        return "insufficient"


class NeverAIExecution:
    def plan(self, request):
        _ = request
        raise AssertionError("No-evidence path must not plan AI execution.")

    def authorize(self, request, planning):
        _ = (request, planning)
        raise AssertionError("No-evidence path must not authorize AI execution.")

    def bind(self, request, authorization):
        _ = (request, authorization)
        raise AssertionError("No-evidence path must not bind AI execution.")


class KnowledgeAnswerQuerySemanticsTests(
    unittest.TestCase
):
    def test_retrieval_planner_queries_remain_natural_language(
        self,
    ) -> None:
        repository = RecordingRepository()

        service = KnowledgeAnswerService(
            repository=repository,
            conversations=FakeConversations(),
            chat=SimpleNamespace(),
            analyzer=FakeAnalyzer(),
            planner=FakePlanner(),
            ranker=EmptyRanker(),
            conflict_detector=EmptyConflicts(),
            context_builder=EmptyContext(),
            prompt_builder=SimpleNamespace(),
            citations=SimpleNamespace(),
            confidence=FakeConfidence(),
            candidates_per_query=10,
            selected_limit=5,
        )

        service.answer(
            "How do I solve a pump pressure problem?",
            None,
        )

        self.assertEqual(
            repository.queries,
            [
                "pump pressure problem",
                "centrifugal pump troubleshooting",
            ],
        )

    def test_answer_without_grounded_citations_returns_insufficient_message(
        self,
    ) -> None:
        repository = RecordingRepository()

        service = KnowledgeAnswerService(
            repository=repository,
            conversations=FakeConversations(),
            chat=SimpleNamespace(),
            analyzer=FakeAnalyzer(),
            planner=FakePlanner(),
            ranker=EmptyRanker(),
            conflict_detector=EmptyConflicts(),
            context_builder=EmptyContext(),
            prompt_builder=SimpleNamespace(),
            citations=SimpleNamespace(),
            confidence=FakeConfidence(),
            candidates_per_query=10,
            selected_limit=5,
        )

        response = service.answer(
            "How do I solve a pump pressure problem?",
            None,
        )

        self.assertEqual(
            response.answer,
            "Sufficient supporting evidence was not found in local documents.",
        )

        self.assertEqual(
            response.evidence_quality,
            "insufficient",
        )

        self.assertEqual(
            response.citations,
            [],
        )

    def test_no_evidence_never_enters_ai_authority_chain(self) -> None:
        repository = RecordingRepository()
        never = NeverAIExecution()
        service = KnowledgeAnswerService(
            repository=repository,
            conversations=FakeConversations(),
            chat=SimpleNamespace(),
            analyzer=FakeAnalyzer(),
            planner=FakePlanner(),
            ranker=EmptyRanker(),
            conflict_detector=EmptyConflicts(),
            context_builder=EmptyContext(),
            prompt_builder=SimpleNamespace(),
            citations=SimpleNamespace(),
            confidence=FakeConfidence(),
            candidates_per_query=10,
            selected_limit=5,
            execution_planner=never,  # type: ignore[arg-type]
            execution_guard=never,  # type: ignore[arg-type]
            ai_runtime=never,  # type: ignore[arg-type]
        )
        response = service.answer(
            "How do I solve a pump pressure problem?",
            None,
            request_id="no-evidence-1",
        )
        self.assertEqual(
            response.answer,
            "Sufficient supporting evidence was not found in local documents.",
        )
        self.assertEqual(response.evidence_quality, "insufficient")


if __name__ == "__main__":
    unittest.main()