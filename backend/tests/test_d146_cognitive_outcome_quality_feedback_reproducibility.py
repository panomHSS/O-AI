from __future__ import annotations

import hashlib
import json
from datetime import timedelta

import pytest

from app.services.cognitive_outcome_quality_feedback import (
    CognitiveOutcomeQualityFeedbackEvaluator,
    CognitiveOutcomeQualityFeedbackMonitor,
)
from tests.test_d134_cognitive_experience import NOW, completed_candidate
from tests.test_d146_cognitive_outcome_quality_feedback import (
    LESSON_CASES,
    candidate_for_lesson,
)


@pytest.mark.parametrize("case", range(12), ids=[f"R{i:02d}" for i in range(1, 13)])
def test_r01_repeated_evaluation_is_identical(case: int):
    lesson = LESSON_CASES[case % len(LESSON_CASES)][0]
    candidate = candidate_for_lesson(lesson)
    first = CognitiveOutcomeQualityFeedbackEvaluator.evaluate(candidate)
    second = CognitiveOutcomeQualityFeedbackEvaluator.evaluate(candidate)
    assert first == second


@pytest.mark.parametrize("case", range(12), ids=[f"R{i:02d}" for i in range(13, 25)])
def test_r02_turn_identity_and_created_at_do_not_change_feedback(case: int):
    reference, *_ = completed_candidate(
        turn_id="turn-reference",
        created_at=NOW,
    )
    candidate, *_ = completed_candidate(
        turn_id=f"turn-{case}",
        created_at=NOW + timedelta(seconds=case + 1),
    )
    assert candidate.candidate_fingerprint == reference.candidate_fingerprint
    assert (
        CognitiveOutcomeQualityFeedbackEvaluator.evaluate(candidate)
        == CognitiveOutcomeQualityFeedbackEvaluator.evaluate(reference)
    )


@pytest.mark.parametrize("case", range(12), ids=[f"R{i:02d}" for i in range(25, 37)])
def test_r03_feedback_fingerprint_matches_frozen_canonical_json(case: int):
    lesson, _ = LESSON_CASES[case % len(LESSON_CASES)]
    candidate = candidate_for_lesson(lesson)
    assessment = CognitiveOutcomeQualityFeedbackEvaluator.evaluate(candidate)

    payload = {
        "candidate_fingerprint": candidate.candidate_fingerprint,
        "classification": assessment.classification,
        "contract_version": "1",
        "reason_code": assessment.reason_code,
    }
    expected = hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    assert assessment.feedback_fingerprint == expected


@pytest.mark.parametrize("rotation", range(12), ids=[f"R{i:02d}" for i in range(37, 49)])
def test_r04_aggregate_snapshot_is_order_independent(rotation: int):
    candidates = [
        candidate_for_lesson("verified_success"),
        candidate_for_lesson("bounded_insufficiency"),
        candidate_for_lesson("critic_exhausted"),
        candidate_for_lesson("invalid_cognition"),
        candidate_for_lesson("terminal_failure"),
        object(),
    ]

    reference = CognitiveOutcomeQualityFeedbackMonitor()
    for item in candidates:
        assert reference.try_record(item)

    shifted = CognitiveOutcomeQualityFeedbackMonitor()
    offset = rotation % len(candidates)
    for item in candidates[offset:] + candidates[:offset]:
        assert shifted.try_record(item)

    assert shifted.snapshot() == reference.snapshot()
