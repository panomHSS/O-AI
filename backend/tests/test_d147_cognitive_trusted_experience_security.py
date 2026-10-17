from __future__ import annotations

import ast
from dataclasses import fields, replace
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.contracts.cognitive_trusted_experience import (
    CognitiveTrustedExperienceEligibilityAssessment,
    CognitiveTrustedExperienceProposal,
    evaluate_cognitive_trusted_experience_eligibility,
)
from app.schemas.diagnostics import CognitiveTrustedExperienceLifecycleDiagnostics
from app.schemas.trusted_experiences import TrustedExperienceDecisionRequest
from app.services.cognitive_outcome_quality_feedback import (
    CognitiveOutcomeQualityFeedbackEvaluator,
)
from tests.test_d146_cognitive_outcome_quality_feedback import candidate_for_lesson

ROOT = Path(__file__).resolve().parents[2]

AUTHORITY_FLAGS = (
    "learning_authority",
    "memory_write_authority",
    "routing_authority",
    "model_selection_authority",
    "execution_authority",
    "configuration_authority",
    "rollout_authority",
    "automatic_trust",
    "automatic_learning",
    "automatic_promotion",
)


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _imports(path: str) -> set[str]:
    tree = ast.parse(_source(path))
    result = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module)
    return result


def proposal():
    candidate = candidate_for_lesson("verified_success")
    feedback = CognitiveOutcomeQualityFeedbackEvaluator.evaluate(candidate)
    result = evaluate_cognitive_trusted_experience_eligibility(
        candidate=candidate,
        feedback=feedback,
    )
    assert result.proposal is not None
    return result.proposal


def run_case(case: int) -> None:
    slot = (case - 1) % 16
    variant = (case - 1) // 16
    if slot == 0:
        field_name = AUTHORITY_FLAGS[variant % len(AUTHORITY_FLAGS)]
        value = proposal()
        with pytest.raises(ValueError):
            replace(value, **{field_name: True})
    elif slot == 1:
        field_name = AUTHORITY_FLAGS[variant % len(AUTHORITY_FLAGS)]
        with pytest.raises(ValueError):
            CognitiveTrustedExperienceLifecycleDiagnostics(
                status="idle",
                **{field_name: True},
            )
    elif slot == 2:
        with pytest.raises(ValidationError):
            TrustedExperienceDecisionRequest(
                decision_comment="ok",
                workspace_id="company",
            )
    elif slot == 3:
        with pytest.raises(ValidationError):
            TrustedExperienceDecisionRequest(
                decision_comment="ok",
                state="TRUSTED",
            )
    elif slot == 4:
        bad = candidate_for_lesson("verified_success")
        object.__setattr__(bad, "candidate_fingerprint", "bad")
        feedback = CognitiveOutcomeQualityFeedbackEvaluator.evaluate(bad)
        result = evaluate_cognitive_trusted_experience_eligibility(
            candidate=bad,
            feedback=feedback,
        )
        assert result.eligibility == "invalid_evidence"
        assert result.proposal is None
    elif slot == 5:
        result = evaluate_cognitive_trusted_experience_eligibility(
            candidate=object(),
            feedback=object(),
        )
        assert result.eligibility == "invalid_evidence"
    elif slot == 6:
        names = {field.name for field in fields(CognitiveTrustedExperienceProposal)}
        assert {
            "turn_id", "request_id", "conversation_id", "project_id",
            "prompt", "response", "chain_of_thought",
        }.isdisjoint(names)
    elif slot == 7:
        names = set(CognitiveTrustedExperienceLifecycleDiagnostics.model_fields)
        assert {
            "id", "workspace_id", "candidate_fingerprint",
            "feedback_fingerprint", "model_id", "profile_id",
        }.isdisjoint(names)
    elif slot == 8:
        source = _source("backend/app/contracts/cognitive_trusted_experience.py").lower()
        assert "sqlalchemy" not in source
        assert "requests" not in source
        assert "httpx" not in source
    elif slot == 9:
        imports = _imports("backend/app/services/trusted_experience_lifecycle.py")
        for forbidden in (
            "app.services.ai_runtime",
            "app.services.ai_router",
            "app.services.execution_planner",
            "app.services.execution_guard",
            "app.services.memories",
        ):
            assert forbidden not in imports
    elif slot == 10:
        source = _source("backend/app/api/v1/trusted_experiences.py")
        assert '@router.post(\n    "",' not in source
        assert "@router.patch" not in source
        assert "@router.put" not in source
        assert "@router.delete" not in source
    elif slot == 11:
        migration = _source(
            "backend/alembic/versions/0014_trusted_experience_lifecycle.py"
        )
        for name in (
            "trg_trusted_experiences_transition_guard",
            "trg_trusted_experience_events_immutable_update",
            "trg_trusted_experience_events_immutable_delete",
            "trg_trusted_experiences_no_delete",
        ):
            assert name in migration
    elif slot == 12:
        source = _source("backend/app/models/trusted_experience.py").lower()
        for forbidden in (
            "prompt", "response_text", "conversation_id", "project_id",
            "turn_id", "request_id", "chain_of_thought",
        ):
            assert forbidden not in source
    elif slot == 13:
        value = proposal()
        for field_name in AUTHORITY_FLAGS:
            assert getattr(value, field_name) is False
    elif slot == 14:
        assessment = CognitiveTrustedExperienceEligibilityAssessment(
            eligibility="invalid_evidence",
            reason_code="invalid_evidence",
            proposal=None,
        )
        for field_name in AUTHORITY_FLAGS:
            assert getattr(assessment, field_name) is False
    else:
        source = _source("backend/app/services/cognitive_runtime_observability.py")
        assert "try_capture_trusted_experience" in source
        assert "except Exception:" in source
        assert "sqlalchemy" not in source


@pytest.mark.parametrize("case", range(1, 81), ids=[f"S{i:02d}" for i in range(1, 81)])
def test_d147_security_matrix(case: int) -> None:
    run_case(case)
