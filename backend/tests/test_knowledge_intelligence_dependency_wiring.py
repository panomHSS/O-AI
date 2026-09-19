from tests.workspace_fixture import TEST_WORKSPACE_SCOPE

import unittest
from unittest.mock import MagicMock, patch

from app.api.dependencies import get_knowledge_answer_service


class KnowledgeIntelligenceDependencyWiringTests(unittest.TestCase):
    @patch("app.api.dependencies.get_settings")
    def test_runtime_wires_minimum_evidence_score_and_ai_authority(self, get_settings: MagicMock) -> None:
        settings = MagicMock()
        settings.oai_chat_context_message_limit = 20
        settings.oai_memory_context_max_items = 8
        settings.oai_memory_context_max_chars = 2000
        settings.oai_memory_context_max_item_chars = 500
        settings.oai_knowledge_answer_max_retrieval_queries = 3
        settings.oai_knowledge_answer_candidates_per_query = 12
        settings.oai_knowledge_answer_selected_evidence_count = 6
        settings.oai_knowledge_answer_max_evidence_per_document = 2
        settings.oai_knowledge_answer_minimum_evidence_score = 0.37
        settings.oai_knowledge_answer_context_char_budget = 8000
        get_settings.return_value = settings

        database_session = MagicMock()
        database_session.get_bind.return_value.dialect.name = "sqlite"
        chat_service = MagicMock()
        execution_planner = MagicMock()
        execution_guard = MagicMock()
        ai_runtime = MagicMock()
        error_normalizer = MagicMock()
        response_composer = MagicMock()

        service = get_knowledge_answer_service(
            database_session=database_session,
            workspace_scope=TEST_WORKSPACE_SCOPE,
            chat_service=chat_service,
            execution_planner=execution_planner,
            execution_guard=execution_guard,
            ai_runtime=ai_runtime,
            error_normalizer=error_normalizer,
            response_composer=response_composer,
        )

        self.assertEqual(service._ranker._minimum_score, 0.37)
        self.assertEqual(service._ranker._max_per_document, 2)
        self.assertIs(service._execution_planner, execution_planner)
        self.assertIs(service._execution_guard, execution_guard)
        self.assertIs(service._ai_runtime, ai_runtime)
        self.assertIs(service._error_normalizer, error_normalizer)
        self.assertIs(service._response_composer, response_composer)
        self.assertTrue(service._normalize_ai_execution_failures)


if __name__ == "__main__":
    unittest.main()
