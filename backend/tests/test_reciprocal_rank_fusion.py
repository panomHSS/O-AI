import unittest

from app.search.fusion import reciprocal_rank_fusion


class ReciprocalRankFusionTests(unittest.TestCase):
    def test_document_found_by_both_rankings_wins(
        self,
    ) -> None:
        semantic = [
            {"chunk_id": "semantic-only"},
            {"chunk_id": "both"},
            {"chunk_id": "semantic-third"},
        ]

        lexical = [
            {"chunk_id": "both"},
            {"chunk_id": "lexical-only"},
            {"chunk_id": "lexical-third"},
        ]

        results = reciprocal_rank_fusion(
            semantic,
            lexical,
            limit=4,
        )

        self.assertEqual(
            results[0]["chunk_id"],
            "both",
        )

    def test_result_preserves_original_record(
        self,
    ) -> None:
        semantic = [
            {
                "chunk_id": "chunk-1",
                "document_id": "document-1",
                "content": "pump pressure",
                "relevance_score": 0.91,
            }
        ]

        results = reciprocal_rank_fusion(
            semantic,
            [],
            limit=1,
        )

        self.assertEqual(
            results[0]["document_id"],
            "document-1",
        )
        self.assertEqual(
            results[0]["content"],
            "pump pressure",
        )

    def test_relevance_score_becomes_fused_score(
        self,
    ) -> None:
        semantic = [
            {
                "chunk_id": "chunk-1",
                "relevance_score": 0.99,
            }
        ]

        lexical = [
            {
                "chunk_id": "chunk-1",
                "relevance_score": 0.25,
            }
        ]

        results = reciprocal_rank_fusion(
            semantic,
            lexical,
            limit=1,
        )

        expected = (
            1.0 / 61.0
            + 1.0 / 61.0
        )

        self.assertAlmostEqual(
            results[0]["relevance_score"],
            expected,
        )

    def test_limit_is_applied_after_fusion(
        self,
    ) -> None:
        semantic = [
            {"chunk_id": "a"},
            {"chunk_id": "b"},
            {"chunk_id": "c"},
        ]

        results = reciprocal_rank_fusion(
            semantic,
            [],
            limit=2,
        )

        self.assertEqual(
            len(results),
            2,
        )

    def test_empty_rankings_return_empty_results(
        self,
    ) -> None:
        self.assertEqual(
            reciprocal_rank_fusion(
                [],
                [],
                limit=5,
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()