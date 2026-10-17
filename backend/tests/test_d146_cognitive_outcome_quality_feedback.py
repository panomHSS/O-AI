from __future__ import annotations

import inspect
from dataclasses import fields
from pathlib import Path
from typing import get_args

import pytest

from app.contracts.cognitive_brain import (
    CognitiveFailureCode,
    CognitiveTurnState,
)
from app.contracts.cognitive_outcome_quality_feedback import (
    D146_CONTRACT_VERSION,
    D146_COUNTER_MAX,
    D146_REFERENCE_BASELINE,
    D146_SAMPLE_SCOPE,
    CognitiveOutcomeQualityClassification,
    CognitiveOutcomeQualityFeedbackAssessment,
    CognitiveOutcomeQualityFeedbackSnapshot,
    CognitiveOutcomeQualityReasonCode,
)
from app.schemas.diagnostics import CognitiveOutcomeQualityFeedbackDiagnostics
from app.services.cognitive_outcome_quality_feedback import (
    CognitiveOutcomeQualityFeedbackEvaluator,
    CognitiveOutcomeQualityFeedbackMonitor,
)
from tests.test_d134_cognitive_experience import (
    completed_candidate,
    form,
    make_gate,
    make_manifest,
    make_meta,
    make_task,
    make_verification,
)

ROOT = Path(__file__).resolve().parents[2]


def candidate_for_lesson(lesson: str):
    if lesson == "verified_success":
        return completed_candidate()[0]
    if lesson == "bounded_insufficiency":
        manifest = make_manifest(
            CognitiveTurnState.INSUFFICIENT,
            failure_code=None,
        )
        task = make_task(manifest)
        meta = make_meta(manifest, task, confidence="unknown")
        return form(
            manifest,
            task=task,
            meta=meta,
            verification=None,
            gate=None,
        )
    if lesson == "critic_exhausted":
        manifest = make_manifest(
            CognitiveTurnState.FAILED,
            revision=1,
            failure_code=CognitiveFailureCode.CRITIC_UNAVAILABLE,
        )
        task = make_task(manifest)
        meta = make_meta(manifest, task, confidence="limited")
        verification = make_verification(manifest, result="revise")
        gate = make_gate(manifest, verification)
        return form(
            manifest,
            task=task,
            meta=meta,
            verification=verification,
            gate=gate,
        )
    if lesson == "invalid_cognition":
        manifest = make_manifest(
            CognitiveTurnState.FAILED,
            failure_code=CognitiveFailureCode.INVALID_COGNITION,
        )
        task = make_task(manifest)
        meta = make_meta(manifest, task)
        verification = make_verification(manifest, result="invalid_cognition")
        return form(
            manifest,
            task=task,
            meta=meta,
            verification=verification,
            gate=None,
        )
    if lesson == "terminal_failure":
        manifest = make_manifest(
            CognitiveTurnState.FAILED,
            context_digest=None,
            task_kind=None,
            failure_code=CognitiveFailureCode.TURN_DEADLINE_EXCEEDED,
        )
        return form(
            manifest,
            task=None,
            meta=None,
            verification=None,
            gate=None,
        )
    raise AssertionError(lesson)


LESSON_CASES = (
    ("verified_success", "verified_success"),
    ("bounded_insufficiency", "bounded_insufficiency"),
    ("critic_exhausted", "adverse_outcome"),
    ("invalid_cognition", "adverse_outcome"),
    ("terminal_failure", "adverse_outcome"),
)

AUTHORITY_FLAGS = (
    "learning_authority",
    "retention_authority",
    "experience_promotion_authority",
    "memory_write_authority",
    "routing_authority",
    "model_selection_authority",
    "execution_authority",
    "configuration_authority",
    "rollout_authority",
    "automatic_learning",
    "automatic_promotion",
)


@pytest.mark.parametrize(("lesson", "classification"), LESSON_CASES)
def test_f01_exact_lesson_classification_mapping(lesson: str, classification: str):
    assessment = CognitiveOutcomeQualityFeedbackEvaluator.evaluate(
        candidate_for_lesson(lesson)
    )
    assert assessment.classification == classification


@pytest.mark.parametrize(("lesson", "_classification"), LESSON_CASES)
def test_f02_valid_reason_code_is_exact_d134_lesson(
    lesson: str,
    _classification: str,
):
    assessment = CognitiveOutcomeQualityFeedbackEvaluator.evaluate(
        candidate_for_lesson(lesson)
    )
    assert assessment.reason_code == lesson


@pytest.mark.parametrize(("lesson", "_classification"), LESSON_CASES)
def test_f03_valid_feedback_fingerprint_is_sha256_hex(
    lesson: str,
    _classification: str,
):
    assessment = CognitiveOutcomeQualityFeedbackEvaluator.evaluate(
        candidate_for_lesson(lesson)
    )
    assert assessment.feedback_fingerprint is not None
    assert len(assessment.feedback_fingerprint) == 64
    int(assessment.feedback_fingerprint, 16)


@pytest.mark.parametrize(("lesson", "_classification"), LESSON_CASES)
def test_f04_valid_assessment_carries_exact_candidate_fingerprint(
    lesson: str,
    _classification: str,
):
    candidate = candidate_for_lesson(lesson)
    assessment = CognitiveOutcomeQualityFeedbackEvaluator.evaluate(candidate)
    assert assessment.source_candidate_fingerprint == candidate.candidate_fingerprint


@pytest.mark.parametrize("field_name", AUTHORITY_FLAGS)
def test_f05_assessment_authority_firewall_is_false(field_name: str):
    assessment = CognitiveOutcomeQualityFeedbackEvaluator.evaluate(
        candidate_for_lesson("verified_success")
    )
    assert getattr(assessment, field_name) is False


@pytest.mark.parametrize("field_name", AUTHORITY_FLAGS)
def test_f06_diagnostics_authority_firewall_is_false(field_name: str):
    diagnostics = CognitiveOutcomeQualityFeedbackDiagnostics(status="idle")
    assert getattr(diagnostics, field_name) is False


CONTRACT_CHECKS = (
    ("baseline", D146_REFERENCE_BASELINE, "bd773c16b154b23bdd57381ca8f6b25def29adb4"),
    ("version", D146_CONTRACT_VERSION, "1"),
    ("scope", D146_SAMPLE_SCOPE, "cognitive_experience_candidates"),
    ("counter_max", D146_COUNTER_MAX, 9_223_372_036_854_775_807),
    (
        "classification_vocab",
        get_args(CognitiveOutcomeQualityClassification),
        (
            "verified_success",
            "bounded_insufficiency",
            "adverse_outcome",
            "invalid_evidence",
        ),
    ),
    (
        "reason_vocab",
        get_args(CognitiveOutcomeQualityReasonCode),
        (
            "verified_success",
            "bounded_insufficiency",
            "critic_exhausted",
            "invalid_cognition",
            "terminal_failure",
            "invalid_experience_candidate",
        ),
    ),
)


@pytest.mark.parametrize(("_name", "actual", "expected"), CONTRACT_CHECKS)
def test_f07_exact_contract_constants(_name: str, actual, expected):
    assert actual == expected


MONITOR_CASES = (
    ("verified_success", "verified_success", "lesson_verified_success"),
    ("bounded_insufficiency", "bounded_insufficiency", "lesson_bounded_insufficiency"),
    ("critic_exhausted", "adverse_outcome", "lesson_critic_exhausted"),
    ("invalid_cognition", "adverse_outcome", "lesson_invalid_cognition"),
    ("terminal_failure", "adverse_outcome", "lesson_terminal_failure"),
)


@pytest.mark.parametrize(("lesson", "classification_field", "lesson_field"), MONITOR_CASES)
def test_f08_monitor_records_exact_one_classification_and_lesson(
    lesson: str,
    classification_field: str,
    lesson_field: str | None,
):
    monitor = CognitiveOutcomeQualityFeedbackMonitor()
    candidate = object() if lesson == "invalid" else candidate_for_lesson(lesson)
    assert monitor.try_record(candidate)
    snapshot = monitor.snapshot()
    assert snapshot.observed == 1
    assert getattr(snapshot, classification_field) == 1
    if lesson_field is not None:
        assert getattr(snapshot, lesson_field) == 1


@pytest.mark.parametrize("count", range(1, 9))
def test_f09_monitor_accumulates_verified_success_without_overcount(count: int):
    monitor = CognitiveOutcomeQualityFeedbackMonitor()
    candidate = candidate_for_lesson("verified_success")
    for _ in range(count):
        assert monitor.try_record(candidate)
    snapshot = monitor.snapshot()
    assert snapshot.observed == count
    assert snapshot.verified_success == count
    assert snapshot.lesson_verified_success == count
    assert snapshot.invalid_evidence == 0


VALID_SNAPSHOTS = (
    CognitiveOutcomeQualityFeedbackSnapshot(),
    CognitiveOutcomeQualityFeedbackSnapshot(
        observed=1,
        verified_success=1,
        lesson_verified_success=1,
    ),
    CognitiveOutcomeQualityFeedbackSnapshot(
        observed=1,
        bounded_insufficiency=1,
        lesson_bounded_insufficiency=1,
    ),
    CognitiveOutcomeQualityFeedbackSnapshot(
        observed=1,
        adverse_outcome=1,
        lesson_critic_exhausted=1,
    ),
    CognitiveOutcomeQualityFeedbackSnapshot(
        observed=1,
        adverse_outcome=1,
        lesson_terminal_failure=1,
    ),
    CognitiveOutcomeQualityFeedbackSnapshot(
        observed=1,
        invalid_evidence=1,
    ),
)


@pytest.mark.parametrize("snapshot", VALID_SNAPSHOTS)
def test_f10_snapshot_invariants_accept_valid_shapes(snapshot):
    assert (
        snapshot.verified_success
        + snapshot.bounded_insufficiency
        + snapshot.adverse_outcome
        + snapshot.invalid_evidence
        == snapshot.observed
    )


DIAGNOSTIC_CASES = (
    ("contract_version", "1"),
    ("implemented", True),
    ("reference_baseline", D146_REFERENCE_BASELINE),
    ("sample_scope", D146_SAMPLE_SCOPE),
    ("reset_on_restart", True),
    ("status", "idle"),
)


@pytest.mark.parametrize(("field_name", "expected"), DIAGNOSTIC_CASES)
def test_f11_diagnostics_exact_metadata(field_name: str, expected):
    diagnostics = CognitiveOutcomeQualityFeedbackDiagnostics(status="idle")
    assert getattr(diagnostics, field_name) == expected


SOURCE_NEEDLES = (
    ("backend/app/services/command_orchestrator.py", "_observe_experience_feedback"),
    ("backend/app/services/cognitive_runtime_observability.py", "try_record_experience_feedback"),
    ("backend/app/api/dependencies.py", "get_cognitive_outcome_quality_feedback_monitor"),
    ("backend/app/services/runtime_diagnostics.py", "cognitive_outcome_quality_feedback"),
    ("backend/app/schemas/diagnostics.py", "cognitive_outcome_quality_feedback"),
)


@pytest.mark.parametrize(("relative", "needle"), SOURCE_NEEDLES)
def test_f12_exact_production_integration_points(relative: str, needle: str):
    source = (ROOT / relative).read_text(encoding="utf-8")
    assert needle in source


def test_f13_monitor_saturates_at_signed_int64_without_breaking_invariants():
    monitor = CognitiveOutcomeQualityFeedbackMonitor()
    monitor._counts["observed"] = D146_COUNTER_MAX
    monitor._counts["verified_success"] = D146_COUNTER_MAX
    monitor._counts["lesson_verified_success"] = D146_COUNTER_MAX
    before = monitor.snapshot()
    assert monitor.try_record(candidate_for_lesson("verified_success"))
    assert monitor.snapshot() == before


def test_f14_monitor_is_thread_safe_for_concurrent_aggregate_updates():
    from concurrent.futures import ThreadPoolExecutor

    monitor = CognitiveOutcomeQualityFeedbackMonitor()
    candidate = candidate_for_lesson("verified_success")

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: monitor.try_record(candidate), range(200)))

    assert all(results)
    snapshot = monitor.snapshot()
    assert snapshot.observed == 200
    assert snapshot.verified_success == 200
    assert snapshot.lesson_verified_success == 200
