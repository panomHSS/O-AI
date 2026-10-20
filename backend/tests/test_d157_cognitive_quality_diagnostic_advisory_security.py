from dataclasses import fields
from pathlib import Path

from app.contracts.cognitive_quality_diagnostic_advisory import CognitiveQualityDiagnosticAdvisory

ROOT=Path(__file__).resolve().parents[2]


def test_d157_x_no_raw_content_fields():
    names={f.name for f in fields(CognitiveQualityDiagnosticAdvisory)}
    assert names.isdisjoint({"prompt","message","response","answer","context","memory","knowledge","chain_of_thought","credential","api_key","oauth_token","experience_text","trusted_experience_comment"})


def test_d157_v_w_api_is_exactly_read_only_diagnostic_extension():
    source=(ROOT/"backend/app/api/v1/cognitive_quality.py").read_text(encoding="utf-8")
    assert '@router.get("/diagnostic"' in source
    diagnostic=source[source.index('@router.get("/diagnostic"'):]
    assert "workspace_id" not in diagnostic
    for marker in ("@router.post(","@router.put(","@router.patch(","@router.delete("): assert marker not in source
    assert '"/events"' not in source and '"/raw"' not in source


def test_d157_y_no_provider_runtime_or_governance_imports():
    paths=("backend/app/contracts/cognitive_quality_diagnostic_advisory.py","backend/app/services/cognitive_quality_diagnostic_advisory.py","backend/app/schemas/cognitive_quality_diagnostic.py","backend/app/api/v1/cognitive_quality.py")
    source="\n".join((ROOT/p).read_text(encoding="utf-8") for p in paths)
    forbidden=("OpenAIChatProvider",".responses.create","LocalAIRuntime","d139_","CognitiveRuntimeReadiness","CognitiveRuntimePromotion","AIUsagePricing","AIUsageMeter")
    assert all(marker not in source for marker in forbidden)


def test_d157_w_no_persistence_or_migration_surface():
    service=(ROOT/"backend/app/services/cognitive_quality_diagnostic_advisory.py").read_text(encoding="utf-8")
    assert "session.add(" not in service and "INSERT " not in service and "UPDATE " not in service and "DELETE " not in service
    assert not (ROOT/"backend/alembic/versions/0017_cognitive_quality_diagnostic_advisory.py").exists()


def test_d157_x_authority_fields_are_literal_false_defaults():
    advisory_fields=CognitiveQualityDiagnosticAdvisory.__dataclass_fields__
    for name in ("learning_authority","memory_write_authority","experience_trust_authority","routing_authority","model_selection_authority","provider_selection_authority","profile_selection_authority","prompt_mutation_authority","context_mutation_authority","policy_mutation_authority","configuration_authority","execution_authority","benchmark_promotion_authority","rollout_authority","automatic_learning","automatic_optimization"):
        assert advisory_fields[name].default is False


def test_d157_scope_does_not_reference_d156_persistence_mutators():
    source=(ROOT/"backend/app/services/cognitive_quality_diagnostic_advisory.py").read_text(encoding="utf-8")
    assert "CognitiveQualityObservationRepository" not in source
    assert "CognitiveQualityObservationRecord" not in source
    assert "sessionmaker" not in source
