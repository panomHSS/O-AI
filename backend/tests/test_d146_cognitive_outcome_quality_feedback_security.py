from __future__ import annotations

from dataclasses import fields, replace
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.contracts.cognitive_brain import CognitiveTurnState
from app.contracts.cognitive_outcome_quality_feedback import (
    CognitiveOutcomeQualityFeedbackAssessment,
    CognitiveOutcomeQualityFeedbackSnapshot,
)
from app.schemas.diagnostics import CognitiveOutcomeQualityFeedbackDiagnostics
from app.services.cognitive_outcome_quality_feedback import (
    CognitiveOutcomeQualityFeedbackEvaluator,
)
from tests.test_d146_cognitive_outcome_quality_feedback import candidate_for_lesson

ROOT = Path(__file__).resolve().parents[2]


def tampered_candidate(case: int):
    if case == 0:
        return None
    if case == 1:
        return object()
    if case == 2:
        return "candidate"
    if case == 3:
        return {}

    candidate = candidate_for_lesson("verified_success")
    mutations = (
        ("candidate_fingerprint", "bad"),
        ("lesson_code", "learned"),
        ("retention_disposition", "durable"),
        ("promotion_disposition", "promoted"),
        ("outcome_class", "failure"),
        ("terminal_state", CognitiveTurnState.FAILED),
        ("verification_result", "revise"),
        ("publication_disposition", "blocked"),
        ("critic_exhausted", True),
        ("revision_count", 99),
        ("observed_confidence_class", None),
        ("authorized_adapter_id", "\n"),
    )
    field_name, value = mutations[case - 4]
    object.__setattr__(candidate, field_name, value)
    return candidate


@pytest.mark.parametrize("case", range(16), ids=[f"S{i:02d}" for i in range(1, 17)])
def test_s01_malformed_or_wrong_type_evidence_fails_to_invalid_evidence(case: int):
    assessment = CognitiveOutcomeQualityFeedbackEvaluator.evaluate(
        tampered_candidate(case)
    )
    assert assessment.classification == "invalid_evidence"
    assert assessment.reason_code == "invalid_experience_candidate"
    assert assessment.source_candidate_fingerprint is None
    assert assessment.feedback_fingerprint is None


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


@pytest.mark.parametrize("field_name", AUTHORITY_FLAGS)
def test_s02_assessment_rejects_any_authority_true(field_name: str):
    assessment = CognitiveOutcomeQualityFeedbackEvaluator.evaluate(
        candidate_for_lesson("verified_success")
    )
    with pytest.raises(ValueError):
        replace(assessment, **{field_name: True})


@pytest.mark.parametrize("field_name", AUTHORITY_FLAGS)
def test_s03_diagnostics_rejects_any_authority_true(field_name: str):
    payload = {
        "status": "idle",
        field_name: True,
    }
    with pytest.raises(ValidationError):
        CognitiveOutcomeQualityFeedbackDiagnostics(**payload)


FORBIDDEN_IMPORT_TOKENS = (
    "sqlalchemy",
    "sqlite3",
    "requests",
    "httpx",
    "OpenAI",
    "AIRuntime",
    "ExecutionPlanner",
    "ExecutionGuard",
    "MemoryRepository",
    "KnowledgeRepository",
    "CognitiveRuntimeReadinessEvaluator",
    "CognitiveRuntimePromotionGovernanceEvaluator",
    "CognitiveRuntimeRolloutSelector",
    "CognitiveRuntimeIncidentGovernanceEvaluator",
)


@pytest.mark.parametrize("token", FORBIDDEN_IMPORT_TOKENS)
def test_s04_d146_core_has_no_persistence_model_or_downstream_authority_dependency(
    token: str,
):
    source = "\n".join(
        (
            (ROOT / "backend/app/contracts/cognitive_outcome_quality_feedback.py").read_text(
                encoding="utf-8"
            ),
            (ROOT / "backend/app/services/cognitive_outcome_quality_feedback.py").read_text(
                encoding="utf-8"
            ),
        )
    )
    assert token not in source


PRIVACY_FIELDS = (
    "turn_id",
    "request_id",
    "conversation_id",
    "project_id",
    "workspace_id",
    "candidate_fingerprint",
    "feedback_fingerprint",
    "prompt",
    "response",
    "context_digest",
    "adapter_id",
    "model_id",
)


@pytest.mark.parametrize("field_name", PRIVACY_FIELDS)
def test_s05_aggregate_snapshot_and_diagnostics_expose_no_per_turn_or_identity_field(
    field_name: str,
):
    snapshot_fields = {field.name for field in fields(CognitiveOutcomeQualityFeedbackSnapshot)}
    diagnostics_fields = set(CognitiveOutcomeQualityFeedbackDiagnostics.model_fields)
    assert field_name not in snapshot_fields
    assert field_name not in diagnostics_fields
