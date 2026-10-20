from dataclasses import fields
from pathlib import Path

from app.contracts.cognitive_quality_investigation_evidence import CognitiveQualityInvestigationEvidencePacket

ROOT=Path(__file__).resolve().parents[2]


def test_d159_privacy_no_raw_content_fields():
    names={f.name for f in fields(CognitiveQualityInvestigationEvidencePacket)}
    assert names.isdisjoint({
        "prompt","message","response","answer","context","memory","knowledge","chain_of_thought",
        "credential","api_key","oauth_token","experience_text","trusted_experience_comment",
        "provider_payload","raw_observation","turn_event",
    })


def test_d159_authority_fields_literal_false():
    packet_fields=CognitiveQualityInvestigationEvidencePacket.__dataclass_fields__
    for name in (
        "learning_authority","memory_write_authority","experience_trust_authority","routing_authority",
        "model_selection_authority","provider_selection_authority","profile_selection_authority",
        "prompt_mutation_authority","context_mutation_authority","policy_mutation_authority",
        "configuration_authority","execution_authority","benchmark_promotion_authority",
        "rollout_authority","automatic_learning","automatic_optimization",
    ):
        assert packet_fields[name].default is False


def test_d159_api_exact_read_only_extension():
    source=(ROOT/"backend/app/api/v1/cognitive_quality.py").read_text(encoding="utf-8")
    assert source.count('@router.get("/investigation-evidence"')==1
    block=source[source.index('@router.get("/investigation-evidence"'):]
    assert "workspace_id" not in block
    for marker in ("@router.post(","@router.put(","@router.patch(","@router.delete("):
        assert marker not in source
    for marker in ('"/events"','"/raw"','"/apply"','"/run-benchmark"','"/collect-control"'):
        assert marker not in source


def test_d159_dependency_wiring_no_repository():
    source=(ROOT/"backend/app/api/dependencies.py").read_text(encoding="utf-8")
    start=source.index("def get_cognitive_quality_investigation_evidence_service")
    end=source.index("\n\ndef ",start+5)
    block=source[start:end]
    assert "get_cognitive_quality_investigation_planning_service" in block
    assert "get_cognitive_quality_summary_service" in block
    assert "get_workspace_scope" in block
    assert "get_db" not in block
    assert "CognitiveQualityObservationRepository" not in block
    assert "Session" not in block


def test_d159_service_no_repository_provider_benchmark_runtime():
    source=(ROOT/"backend/app/services/cognitive_quality_investigation_evidence.py").read_text(encoding="utf-8")
    assert "CognitiveQualityInvestigationPlanningService" in source
    assert "CognitiveQualitySummaryService" in source
    forbidden=(
        "CognitiveQualityObservationRepository","sessionmaker","session.add(","INSERT ","UPDATE ","DELETE ",
        "OpenAIChatProvider",".responses.create","LocalAIRuntime","AIUsagePricing","AIUsageMeter",
        "benchmarks.d138_runner","benchmarks.d139_registry","benchmarks.d139_comparator",
        "run_live_evaluation","assess_candidate",
    )
    assert all(marker not in source for marker in forbidden)


def test_d159_no_persistence_or_migration_surface():
    assert not (ROOT/"backend/alembic/versions/0017_cognitive_quality_investigation_evidence.py").exists()
    assert not (ROOT/"backend/app/models/cognitive_quality_investigation_evidence.py").exists()
    assert not (ROOT/"backend/app/repositories/cognitive_quality_investigation_evidence.py").exists()


def test_d159_router_remains_generic_cognitive_quality_mount():
    source=(ROOT/"backend/app/api/router.py").read_text(encoding="utf-8")
    assert "cognitive_quality_router" in source
    assert "investigation_evidence" not in source
