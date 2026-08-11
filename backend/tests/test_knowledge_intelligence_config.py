import unittest

from pydantic import ValidationError

from app.core.config import Settings


class KnowledgeIntelligenceConfigTests(
    unittest.TestCase
):
    def test_minimum_evidence_score_has_safe_default(
        self,
    ) -> None:
        settings = Settings()

        self.assertEqual(
            settings.oai_knowledge_answer_minimum_evidence_score,
            0.20,
        )

    def test_minimum_evidence_score_accepts_valid_value(
        self,
    ) -> None:
        settings = Settings(
            oai_knowledge_answer_minimum_evidence_score=0.35
        )

        self.assertEqual(
            settings.oai_knowledge_answer_minimum_evidence_score,
            0.35,
        )

    def test_minimum_evidence_score_rejects_negative_value(
        self,
    ) -> None:
        with self.assertRaises(ValidationError):
            Settings(
                oai_knowledge_answer_minimum_evidence_score=-0.01
            )

    def test_minimum_evidence_score_rejects_value_above_one(
        self,
    ) -> None:
        with self.assertRaises(ValidationError):
            Settings(
                oai_knowledge_answer_minimum_evidence_score=1.01
            )


if __name__ == "__main__":
    unittest.main()