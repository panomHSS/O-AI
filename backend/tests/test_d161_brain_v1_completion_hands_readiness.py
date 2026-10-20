from dataclasses import fields
from pathlib import Path

from app.contracts.cognitive_quality_investigation_hypothesis_review import (
    CognitiveQualityInvestigationHypothesisReview,
)

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs/specs/D161_BRAIN_V1_COMPLETION_HANDS_READINESS_GATE_V1.md"

SOURCE_BASELINE = "7dba1db0684b0994b2d27d54ccd2f2a4620cb572"
DB_BASELINE = "0016_cognitive_quality_observability"
READINESS_OUTCOMES = (
    "ready_for_hands_design",
    "brain_gap_requires_closure",
    "invalid_readiness_evidence",
)

REPRESENTATIVE_EVIDENCE = (
    "backend/tests/test_d136_cognitive_executive.py",
    "backend/tests/test_d136_cognitive_executive_security.py",
    "backend/tests/test_d146_cognitive_outcome_quality_feedback.py",
    "backend/tests/test_d150_cognitive_trusted_experience_runtime_binding.py",
    "backend/tests/test_d151_cognitive_trusted_experience_consumption.py",
    "backend/tests/test_d152_cognitive_trusted_experience_context_projection.py",
    "backend/tests/test_d153_cognitive_trusted_experience_reasoning.py",
    "backend/tests/test_d154_cognitive_trusted_experience_verification.py",
    "backend/tests/test_d155_ai_usage_observability.py",
    "backend/tests/test_d156_longitudinal_cognitive_quality_observability.py",
    "backend/tests/test_d157_cognitive_quality_diagnostic_advisory.py",
    "backend/tests/test_d158_cognitive_quality_investigation_planning.py",
    "backend/tests/test_d159_cognitive_quality_investigation_evidence.py",
    "backend/tests/test_d160_cognitive_quality_investigation_hypothesis_review.py",
    "backend/tests/test_d160_cognitive_quality_investigation_hypothesis_review_security.py",
    "backend/tests/test_alembic_fresh_database.py",
)


def test_d161_a_frozen_identity_and_outcomes():
    assert SOURCE_BASELINE == "7dba1db0684b0994b2d27d54ccd2f2a4620cb572"
    assert DB_BASELINE == "0016_cognitive_quality_observability"
    assert READINESS_OUTCOMES == (
        "ready_for_hands_design",
        "brain_gap_requires_closure",
        "invalid_readiness_evidence",
    )


def test_d161_b_reuses_existing_evidence():
    assert [p for p in REPRESENTATIVE_EVIDENCE if not (ROOT / p).is_file()] == []


def test_d161_c_d160_remains_noncausal_and_nonexecuting():
    names = {f.name for f in fields(CognitiveQualityInvestigationHypothesisReview)}
    assert names.isdisjoint({
        "root_cause", "caused_by", "causal_effect", "proven_cause",
        "validated_hypothesis", "fix_required", "change_required",
        "tool", "browser", "workflow", "execution_plan",
    })
    contract_fields = CognitiveQualityInvestigationHypothesisReview.__dataclass_fields__
    for name in (
        "learning_authority","memory_write_authority","experience_trust_authority",
        "routing_authority","model_selection_authority","provider_selection_authority",
        "profile_selection_authority","prompt_mutation_authority","context_mutation_authority",
        "policy_mutation_authority","configuration_authority","execution_authority",
        "benchmark_promotion_authority","rollout_authority","automatic_learning",
        "automatic_optimization",
    ):
        assert contract_fields[name].default is False


def test_d161_d_no_d161_runtime_persistence_or_api_surface():
    forbidden = (
        "backend/app/contracts/brain_v1_completion.py",
        "backend/app/services/brain_v1_completion.py",
        "backend/app/schemas/brain_v1_completion.py",
        "backend/app/models/brain_v1_completion.py",
        "backend/app/repositories/brain_v1_completion.py",
        "backend/alembic/versions/0017_brain_v1_completion.py",
        "backend/app/api/v1/brain_v1_completion.py",
    )
    assert all(not (ROOT / path).exists() for path in forbidden)


def test_d161_e_db_boundary_remains_0016():
    versions = ROOT / "backend/alembic/versions"
    assert (versions / "0016_cognitive_quality_observability.py").is_file()
    assert not any(p.name.startswith("0017_") for p in versions.glob("*.py"))


def test_d161_f_d160_direct_dependency_remains_d159_only():
    source = (ROOT / "backend/app/services/cognitive_quality_investigation_hypothesis_review.py").read_text(encoding="utf-8")
    assert "CognitiveQualityInvestigationEvidenceService" in source
    for forbidden in (
        "CognitiveQualityObservationRepository",
        "CognitiveQualitySummaryService",
        "CognitiveQualityDiagnosticService",
        "CognitiveQualityInvestigationPlanningService",
        "OpenAIChatProvider",
        ".responses.create",
        "run_live_evaluation",
        "assess_candidate",
    ):
        assert forbidden not in source


def test_d161_g_spec_preserves_hands_and_production_boundaries():
    source = SPEC.read_text(encoding="utf-8")
    for marker in (
        "SOURCE READY FOR HANDS DESIGN != PRODUCTION AUTONOMY READY != EXECUTION AUTHORIZATION",
        "automatic self-learning",
        "automatic hypothesis validation",
        "D161 does not authorize tool use, browser use, workflow execution",
        "D156 production migration / live cognitive-quality evidence is not established in this flow.",
        "Brain V1 Source Complete",
        "Arms / Hands **Design Reconciliation only**",
        "There is no automatic D162, D163, D164, or later Brain milestone.",
    ):
        assert marker in source


def test_d161_h_scope_is_nonruntime():
    assert list((ROOT / "backend/app").rglob("*d161*")) == []
    assert list((ROOT / "backend/alembic").rglob("*d161*")) == []
    assert SPEC.is_file()
