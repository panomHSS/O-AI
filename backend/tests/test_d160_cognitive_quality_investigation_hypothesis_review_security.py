from dataclasses import fields
from pathlib import Path

from app.contracts.cognitive_quality_investigation_hypothesis_review import (
    CognitiveQualityInvestigationHypothesisReview,
)

ROOT = Path(__file__).resolve().parents[2]


def test_d160_privacy_no_raw_content_or_causal_fields():
    names = {field.name for field in fields(CognitiveQualityInvestigationHypothesisReview)}
    assert names.isdisjoint({
        "prompt","message","response","answer","context","memory","knowledge","chain_of_thought",
        "credential","api_key","oauth_token","experience_text","trusted_experience_comment",
        "provider_payload","raw_observation","turn_event","root_cause","caused_by","causal_effect",
        "proven_cause","fix_required","change_required",
    })


def test_d160_authority_fields_literal_false():
    packet_fields = CognitiveQualityInvestigationHypothesisReview.__dataclass_fields__
    for name in (
        "learning_authority","memory_write_authority","experience_trust_authority","routing_authority",
        "model_selection_authority","provider_selection_authority","profile_selection_authority",
        "prompt_mutation_authority","context_mutation_authority","policy_mutation_authority",
        "configuration_authority","execution_authority","benchmark_promotion_authority",
        "rollout_authority","automatic_learning","automatic_optimization",
    ):
        assert packet_fields[name].default is False


def test_d160_api_exact_read_only_extension():
    source = (ROOT / "backend/app/api/v1/cognitive_quality.py").read_text(encoding="utf-8")
    route_token = '"/investigation-hypothesis-review",'
    assert source.count(route_token) == 1
    block = source[source.index(route_token):]
    assert "@router.get(" in source[:source.index(route_token)]
    assert "workspace_id" not in block
    for marker in ("@router.post(", "@router.put(", "@router.patch(", "@router.delete("):
        assert marker not in source
    for marker in ('"/events"', '"/raw"', '"/apply"', '"/run-benchmark"', '"/validate-hypothesis"'):
        assert marker not in source


def test_d160_dependency_wiring_is_d159_only():
    source = (ROOT / "backend/app/api/dependencies.py").read_text(encoding="utf-8")
    start = source.index("def get_cognitive_quality_investigation_hypothesis_review_service")
    end = source.index("\n\ndef ", start + 5)
    block = source[start:end]
    assert "get_cognitive_quality_investigation_evidence_service" in block
    assert "get_workspace_scope" in block
    assert "get_cognitive_quality_investigation_planning_service" not in block
    assert "get_cognitive_quality_diagnostic_service" not in block
    assert "get_cognitive_quality_summary_service" not in block
    assert "get_db" not in block
    assert "CognitiveQualityObservationRepository" not in block
    assert "Session" not in block


def test_d160_service_no_direct_d156_d157_d158_repository_provider_or_benchmark_runtime():
    source = (ROOT / "backend/app/services/cognitive_quality_investigation_hypothesis_review.py").read_text(encoding="utf-8")
    assert "CognitiveQualityInvestigationEvidenceService" in source
    forbidden = (
        "CognitiveQualityObservationRepository","CognitiveQualitySummaryService",
        "CognitiveQualityDiagnosticService","CognitiveQualityInvestigationPlanningService",
        "sessionmaker","session.add(","INSERT ","UPDATE ","DELETE ",
        "OpenAIChatProvider",".responses.create","LocalAIRuntime","AIUsagePricing","AIUsageMeter",
        "benchmarks.d138_runner","benchmarks.d139_registry","benchmarks.d139_comparator",
        "run_live_evaluation","assess_candidate",
    )
    assert all(marker not in source for marker in forbidden)


def test_d160_no_persistence_or_migration_surface():
    assert not (ROOT / "backend/alembic/versions/0017_cognitive_quality_investigation_hypothesis_review.py").exists()
    assert not (ROOT / "backend/app/models/cognitive_quality_investigation_hypothesis_review.py").exists()
    assert not (ROOT / "backend/app/repositories/cognitive_quality_investigation_hypothesis_review.py").exists()


def test_d160_router_remains_generic_cognitive_quality_mount():
    source = (ROOT / "backend/app/api/router.py").read_text(encoding="utf-8")
    assert "cognitive_quality_router" in source
    assert "investigation_hypothesis_review" not in source
