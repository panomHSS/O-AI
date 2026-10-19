from dataclasses import fields
from pathlib import Path
from app.contracts.cognitive_quality_observability import CognitiveQualityObservation
ROOT=Path(__file__).resolve().parents[2]

def test_d156_no_raw_content_fields():
    names={f.name for f in fields(CognitiveQualityObservation)}
    assert names.isdisjoint({"prompt","message","response","answer","context","memory","knowledge","chain_of_thought","credential","api_key","oauth_token","decision_comment","raw_turn_id"})

def test_d156_api_read_only_no_raw_events():
    s=(ROOT/"backend/app/api/v1/cognitive_quality.py").read_text(encoding="utf-8")
    assert '@router.get(' in s and '"/events"' not in s
    for x in ("@router.post(","@router.put(","@router.patch(","@router.delete("): assert x not in s

def test_d156_no_provider_execution_imports():
    s="\n".join((ROOT/p).read_text(encoding="utf-8") for p in ("backend/app/services/cognitive_quality_projection.py","backend/app/services/cognitive_quality_observability.py","backend/app/services/cognitive_quality_summary.py","backend/app/api/v1/cognitive_quality.py"))
    assert "OpenAIChatProvider" not in s and ".responses.create" not in s and "LocalAIRuntime" not in s

def test_d156_migration_append_only_no_backfill():
    s=(ROOT/"backend/alembic/versions/0016_cognitive_quality_observability.py").read_text(encoding="utf-8")
    assert "immutable_update" in s and "immutable_delete" in s and "INSERT INTO cognitive_quality_observations" not in s
