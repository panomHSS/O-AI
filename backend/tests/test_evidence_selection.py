import unittest

from app.services.knowledge_intelligence import (
    ContextBuilder,
    Evidence,
    EvidenceRanker,
)

def record(
    *,
    document_id: str,
    chunk_id: str,
    content: str,
    relevance_score: float = 1.0,
    file_name: str = "manual.pdf",
) -> dict[str, object]:
    return {
        "document_id": document_id,
        "chunk_id": chunk_id,
        "file_name": file_name,
        "source_path": file_name,
        "source_locator": "page 1",
        "content": content,
        "relevance_score": relevance_score,
        "file_extension": ".pdf",
    }


class EvidenceSelectionTests(
    unittest.TestCase
):
    def test_exact_duplicate_content_is_removed(
        self,
    ) -> None:
        ranker = EvidenceRanker(
            max_per_document=5
        )

        selected, duplicates, filtered = ranker.rank(
            "pump pressure",
            ("pump", "pressure"),
            [
                record(
                    document_id="doc-1",
                    chunk_id="chunk-1",
                    content="Pump pressure is 10 bar.",
                ),
                record(
                    document_id="doc-2",
                    chunk_id="chunk-2",
                    content="  pump   pressure is 10 BAR.  ",
                ),
            ],
        )

        self.assertEqual(
            len(selected),
            1,
        )
        self.assertEqual(
            duplicates,
            1,
        )
        self.assertEqual(
            filtered,
            0,
        )

    def test_document_limit_prevents_source_domination(
        self,
    ) -> None:
        ranker = EvidenceRanker(
            max_per_document=2
        )

        selected, duplicates, filtered = ranker.rank(
            "pump pressure",
            ("pump", "pressure"),
            [
                record(
                    document_id="doc-1",
                    chunk_id="chunk-1",
                    content="Pump pressure information A.",
                    relevance_score=1.0,
                ),
                record(
                    document_id="doc-1",
                    chunk_id="chunk-2",
                    content="Pump pressure information B.",
                    relevance_score=0.9,
                ),
                record(
                    document_id="doc-1",
                    chunk_id="chunk-3",
                    content="Pump pressure information C.",
                    relevance_score=0.8,
                ),
                record(
                    document_id="doc-2",
                    chunk_id="chunk-4",
                    content="Pump pressure information D.",
                    relevance_score=0.7,
                ),
            ],
        )

        document_ids = [
            item.document_id
            for item in selected
        ]

        self.assertEqual(
            document_ids.count("doc-1"),
            2,
        )
        self.assertIn(
            "doc-2",
            document_ids,
        )
        self.assertEqual(
            duplicates,
            0,
        )
        self.assertEqual(
            filtered,
            1,
        )

    def test_ranking_is_deterministic(
        self,
    ) -> None:
        ranker = EvidenceRanker(
            max_per_document=5
        )

        records = [
            record(
                document_id="doc-b",
                chunk_id="chunk-2",
                content="Pump pressure B.",
            ),
            record(
                document_id="doc-a",
                chunk_id="chunk-1",
                content="Pump pressure A.",
            ),
        ]

        first, _, _ = ranker.rank(
            "pump pressure",
            ("pump", "pressure"),
            records,
        )

        second, _, _ = ranker.rank(
            "pump pressure",
            ("pump", "pressure"),
            list(reversed(records)),
        )

        self.assertEqual(
            [
                item.chunk_id
                for item in first
            ],
            [
                item.chunk_id
                for item in second
            ],
        )

    def test_punctuation_only_duplicate_is_removed(
        self,
    ) -> None:
        ranker = EvidenceRanker(
            max_per_document=5
        )

        selected, duplicates, filtered = ranker.rank(
            "pump discharge pressure",
            ("pump", "discharge", "pressure"),
            [
                record(
                    document_id="doc-1",
                    chunk_id="chunk-1",
                    content=(
                        "Pump discharge pressure "
                        "is 10 bar."
                    ),
                ),
                record(
                    document_id="doc-2",
                    chunk_id="chunk-2",
                    content=(
                        "Pump discharge pressure "
                        "is 10 bar!"
                    ),
                ),
            ],
        )

        self.assertEqual(
            len(selected),
            1,
        )
        self.assertEqual(
            duplicates,
            1,
        )
        self.assertEqual(
            filtered,
            0,
        )

    def test_different_engineering_values_are_preserved(
        self,
    ) -> None:
        ranker = EvidenceRanker(
            max_per_document=5
        )

        selected, duplicates, filtered = ranker.rank(
            "pump discharge pressure",
            ("pump", "discharge", "pressure"),
            [
                record(
                    document_id="doc-1",
                    chunk_id="chunk-1",
                    content=(
                        "Pump discharge pressure "
                        "is 10 bar."
                    ),
                ),
                record(
                    document_id="doc-2",
                    chunk_id="chunk-2",
                    content=(
                        "Pump discharge pressure "
                        "is 16 bar."
                    ),
                ),
            ],
        )

        self.assertEqual(
            len(selected),
            2,
        )
        self.assertEqual(
            duplicates,
            0,
        )
        self.assertEqual(
            filtered,
            0,
        )

    def test_different_engineering_units_are_preserved(
        self,
    ) -> None:
        ranker = EvidenceRanker(
            max_per_document=5
        )

        selected, duplicates, filtered = ranker.rank(
            "pump discharge pressure",
            ("pump", "discharge", "pressure"),
            [
                record(
                    document_id="doc-1",
                    chunk_id="chunk-1",
                    content=(
                        "Pump discharge pressure "
                        "is 10 bar."
                    ),
                ),
                record(
                    document_id="doc-2",
                    chunk_id="chunk-2",
                    content=(
                        "Pump discharge pressure "
                        "is 10 psi."
                    ),
                ),
            ],
        )

        self.assertEqual(
            len(selected),
            2,
        )
        self.assertEqual(
            duplicates,
            0,
        )
        self.assertEqual(
            filtered,
            0,
        )


    def test_different_material_designations_are_preserved(
        self,
    ) -> None:
        ranker = EvidenceRanker(
            max_per_document=5
        )

        selected, duplicates, filtered = ranker.rank(
            "boiler tube material",
            ("boiler", "tube", "material"),
            [
                record(
                    document_id="doc-1",
                    chunk_id="chunk-1",
                    content=(
                        "Boiler tube material "
                        "is SA-192."
                    ),
                ),
                record(
                    document_id="doc-2",
                    chunk_id="chunk-2",
                    content=(
                        "Boiler tube material "
                        "is SA-210."
                    ),
                ),
            ],
        )

        self.assertEqual(
            len(selected),
            2,
        )
        self.assertEqual(
            duplicates,
            0,
        )
        self.assertEqual(
            filtered,
            0,
        )

    def test_minimum_score_filters_weak_evidence(
        self,
    ) -> None:
        ranker = EvidenceRanker(
            max_per_document=5,
            minimum_score=0.50,
        )

        selected, duplicates, filtered = ranker.rank(
            "pump pressure",
            ("pump", "pressure"),
            [
                record(
                    document_id="doc-1",
                    chunk_id="chunk-1",
                    content=(
                        "Pump pressure troubleshooting "
                        "requires checking discharge pressure."
                    ),
                    relevance_score=1.0,
                ),
                record(
                    document_id="doc-2",
                    chunk_id="chunk-2",
                    content=(
                        "General maintenance information."
                    ),
                    relevance_score=0.01,
                    file_name="notes.txt",
                ),
            ],
        )

        self.assertEqual(
            [
                item.chunk_id
                for item in selected
            ],
            ["chunk-1"],
        )
        self.assertEqual(
            duplicates,
            0,
        )
        self.assertEqual(
            filtered,
            1,
        )

    def test_evidence_at_minimum_score_is_preserved(
        self,
    ) -> None:
        ranker = EvidenceRanker(
            max_per_document=5,
            minimum_score=0.0,
        )

        selected, duplicates, filtered = ranker.rank(
            "",
            (),
            [
                record(
                    document_id="doc-1",
                    chunk_id="chunk-1",
                    content="Unrelated evidence.",
                    relevance_score=0.0,
                    file_name="notes.txt",
                ),
            ],
        )

        self.assertEqual(
            len(selected),
            1,
        )
        self.assertEqual(
            selected[0].chunk_id,
            "chunk-1",
        )
        self.assertEqual(
            duplicates,
            0,
        )
        self.assertEqual(
            filtered,
            0,
        )

    def test_score_calibration_preserves_relative_quality(
        self,
    ) -> None:
        ranker = EvidenceRanker(
            max_per_document=5,
        )

        selected, _, _ = ranker.rank(
            "pump pressure",
            ("pump", "pressure"),
            [
                record(
                    document_id="doc-1",
                    chunk_id="strong",
                    content=(
                        "Pump pressure troubleshooting "
                        "requires checking pump pressure."
                    ),
                    relevance_score=1.0,
                    file_name="pump_manual.pdf",
                ),
                record(
                    document_id="doc-2",
                    chunk_id="partial",
                    content=(
                        "Pump maintenance requires "
                        "regular inspection."
                    ),
                    relevance_score=0.5,
                    file_name="maintenance.pdf",
                ),
                record(
                    document_id="doc-3",
                    chunk_id="weak",
                    content=(
                        "General maintenance information."
                    ),
                    relevance_score=0.01,
                    file_name="notes.txt",
                ),
            ],
        )

        scores = {
            item.chunk_id: item.score
            for item in selected
        }

        self.assertGreater(
            scores["strong"],
            scores["partial"],
        )
        self.assertGreater(
            scores["partial"],
            scores["weak"],
        )

        self.assertGreaterEqual(
            scores["strong"],
            0.50,
        )
        self.assertLess(
            scores["weak"],
            0.25,
        )

    def test_context_builder_respects_budget_and_skips_oversized_evidence(
        self,
    ) -> None:
        evidence = [
            Evidence(
                document_id="doc-1",
                chunk_id="chunk-1",
                file_name="first.pdf",
                source_path="first.pdf",
                source_locator="page 1",
                content="A" * 60,
                fts_score=1.0,
                file_extension=".pdf",
                score=0.90,
                citation_id="S1",
            ),
            Evidence(
                document_id="doc-2",
                chunk_id="chunk-2",
                file_name="oversized.pdf",
                source_path="oversized.pdf",
                source_locator="page 2",
                content="B" * 50,
                fts_score=1.0,
                file_extension=".pdf",
                score=0.80,
                citation_id="S2",
            ),
            Evidence(
                document_id="doc-3",
                chunk_id="chunk-3",
                file_name="third.pdf",
                source_path="third.pdf",
                source_locator="page 3",
                content="C" * 40,
                fts_score=1.0,
                file_extension=".pdf",
                score=0.70,
                citation_id="S3",
            ),
        ]

        selected = ContextBuilder(
            budget=100,
        ).build(evidence)

        self.assertEqual(
            [item.citation_id for item in selected],
            ["S1", "S3"],
        )

        self.assertLessEqual(
            sum(len(item.content) for item in selected),
            100,
        )

    def test_context_builder_accepts_exact_budget_fit(
        self,
    ) -> None:
        evidence = [
            Evidence(
                document_id="doc-1",
                chunk_id="chunk-1",
                file_name="first.pdf",
                source_path="first.pdf",
                source_locator="page 1",
                content="A" * 60,
                fts_score=1.0,
                file_extension=".pdf",
                score=0.90,
                citation_id="S1",
            ),
            Evidence(
                document_id="doc-2",
                chunk_id="chunk-2",
                file_name="second.pdf",
                source_path="second.pdf",
                source_locator="page 2",
                content="B" * 40,
                fts_score=1.0,
                file_extension=".pdf",
                score=0.80,
                citation_id="S2",
            ),
        ]

        selected = ContextBuilder(
            budget=100,
        ).build(evidence)

        self.assertEqual(
            [item.citation_id for item in selected],
            ["S1", "S2"],
        )

        self.assertEqual(
            sum(len(item.content) for item in selected),
            100,
        )


    def test_context_builder_handles_empty_evidence(
        self,
    ) -> None:
        selected = ContextBuilder(
            budget=100,
        ).build([])

        self.assertEqual(
            selected,
            [],
        )

    def test_context_builder_preserves_evidence_ranking_order(
        self,
    ) -> None:
        evidence = [
            Evidence(
                document_id="doc-1",
                chunk_id="chunk-1",
                file_name="highest.pdf",
                source_path="highest.pdf",
                source_locator="page 1",
                content="A" * 30,
                fts_score=1.0,
                file_extension=".pdf",
                score=0.95,
                citation_id="S1",
            ),
            Evidence(
                document_id="doc-2",
                chunk_id="chunk-2",
                file_name="middle.pdf",
                source_path="middle.pdf",
                source_locator="page 2",
                content="B" * 30,
                fts_score=1.0,
                file_extension=".pdf",
                score=0.75,
                citation_id="S2",
            ),
            Evidence(
                document_id="doc-3",
                chunk_id="chunk-3",
                file_name="lowest.pdf",
                source_path="lowest.pdf",
                source_locator="page 3",
                content="C" * 30,
                fts_score=1.0,
                file_extension=".pdf",
                score=0.55,
                citation_id="S3",
            ),
        ]

        selected = ContextBuilder(
            budget=100,
        ).build(evidence)

        self.assertEqual(
            [item.citation_id for item in selected],
            ["S1", "S2", "S3"],
        )

if __name__ == "__main__":
    unittest.main()