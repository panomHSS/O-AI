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
                id="11111111-1111-1111-1111-111111111111"
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


if __name__ == "__main__":
    unittest.main()