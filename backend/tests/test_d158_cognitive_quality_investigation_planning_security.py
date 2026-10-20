from dataclasses import fields
from pathlib import Path

from app.contracts.cognitive_quality_investigation_planning import CognitiveQualityInvestigationPlan

ROOT=Path(__file__).resolve().parents[2]


def test_d158_y_no_raw_content_fields():
    names={f.name for f in fields(CognitiveQualityInvestigationPlan)}
    assert names.isdisjoint({
        "prompt","message","response","answer","context","memory","knowledge","chain_of_thought",
        "credential","api_key","oauth_token","experience_text","trusted_experience_comment","provider_payload",
    })


def test_d158_y_api_is_exactly_read_only_investigation_plan_extension():
    source=(ROOT/"backend/app/api/v1/cognitive_quality.py").read_text(encoding="utf-8")
    assert '@router.get("/investigation-plan"' in source
    investigation=source[source.index('@router.get("/investigation-plan"'):]
    assert "workspace_id" not in investigation
    for marker in ("@router.post(","@router.put(","@router.patch(","@router.delete("):
        assert marker not in source
    for marker in ('"/events"','"/raw"','"/apply-plan"','"/run-benchmark"'):
        assert marker not in source


def test_d158_y_service_depends_on_d157_not_d156_persistence_or_summary():
    source=(ROOT/"backend/app/services/cognitive_quality_investigation_planning.py").read_text(encoding="utf-8")
    assert "CognitiveQualityDiagnosticService" in source
    forbidden=(
        "CognitiveQualityObservationRepository","CognitiveQualityObservationRecord",
        "CognitiveQualitySummaryService","sessionmaker","session.add(","INSERT ","UPDATE ","DELETE ",
    )
    assert all(marker not in source for marker in forbidden)


def test_d158_y_no_provider_runtime_or_benchmark_execution_imports():
    paths=(
        "backend/app/contracts/cognitive_quality_investigation_planning.py",
        "backend/app/services/cognitive_quality_investigation_planning.py",
        "backend/app/schemas/cognitive_quality_investigation.py",
        "backend/app/api/v1/cognitive_quality.py",
    )
    source="\n".join((ROOT/path).read_text(encoding="utf-8") for path in paths)
    forbidden=(
        "OpenAIChatProvider",".responses.create","LocalAIRuntime","AIUsagePricing","AIUsageMeter",
        "BenchmarkRunner","run_benchmark","CognitiveRuntimePromotion",
    )
    assert all(marker not in source for marker in forbidden)


def test_d158_y_no_persistence_or_migration_surface():
    assert not (ROOT/"backend/alembic/versions/0017_cognitive_quality_investigation_planning.py").exists()
    assert not (ROOT/"backend/app/models/cognitive_quality_investigation.py").exists()
    assert not (ROOT/"backend/app/repositories/cognitive_quality_investigation.py").exists()


def test_d158_b_authority_fields_are_literal_false_defaults():
    plan_fields=CognitiveQualityInvestigationPlan.__dataclass_fields__
    for name in (
        "learning_authority","memory_write_authority","experience_trust_authority","routing_authority",
        "model_selection_authority","provider_selection_authority","profile_selection_authority",
        "prompt_mutation_authority","context_mutation_authority","policy_mutation_authority",
        "configuration_authority","execution_authority","benchmark_promotion_authority",
        "rollout_authority","automatic_learning","automatic_optimization",
    ):
        assert plan_fields[name].default is False


def test_d158_dependency_wiring_composes_existing_d157_service_only():
    source=(ROOT/"backend/app/api/dependencies.py").read_text(encoding="utf-8")
    start=source.index("def get_cognitive_quality_investigation_planning_service")
    end=source.index("\n\ndef ",start+5)
    block=source[start:end]
    assert "get_cognitive_quality_diagnostic_service" in block
    assert "get_db" not in block
    assert "CognitiveQualityObservationRepository" not in block
