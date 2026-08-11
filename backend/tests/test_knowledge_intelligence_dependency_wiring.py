import unittest
from unittest.mock import MagicMock, patch

from app.api.dependencies import (
    get_knowledge_answer_service,
)


class KnowledgeIntelligenceDependencyWiringTests(
    unittest.TestCase
):
    @patch(
        "app.api.dependencies.get_settings"
    )
    def test_runtime_wires_minimum_evidence_score(
        self,
        get_settings: MagicMock,
    ) -> None:
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
        database_session.get_bind.return_value.dialect.name = (
            "sqlite"
        )

        chat_service = MagicMock()
        service = get_knowledge_answer_service(
            database_session,
            chat_service,
        )

        self.assertEqual(
            service._ranker._minimum_score,
            0.37,
        )

        self.assertEqual(
            service._ranker._max_per_document,
            2,
        )

if __name__ == "__main__":
    unittest.main()