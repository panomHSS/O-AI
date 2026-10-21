from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.core.config import get_settings
from app.db.verification import (
    NULLABLE_COLUMNS,
    TARGET_REVISION,
    verify_database,
)


ROOT = Path(__file__).resolve().parents[2]

EXPECTED_COGNITIVE_QUALITY_NULLABLE = {
    "interaction_intent",
    "cognitive_intent",
    "task_kind",
    "verification_result",
    "publication_disposition",
    "critic_exhausted",
    "confidence_class",
    "adapter_id",
    "model_id",
    "profile_id",
    "source_candidate_fingerprint",
    "source_feedback_fingerprint",
}


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_current_database_target_is_exact_alembic_head() -> None:
    script = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))

    assert tuple(script.get_heads()) == (TARGET_REVISION,)
    assert TARGET_REVISION == "0016_cognitive_quality_observability"


def test_cognitive_quality_verifier_nullability_matches_0016_contract() -> None:
    assert (
        NULLABLE_COLUMNS["cognitive_quality_observations"]
        == EXPECTED_COGNITIVE_QUALITY_NULLABLE
    )


def test_fresh_current_head_passes_database_verification(tmp_path: Path) -> None:
    database = tmp_path / "d171-current-head.db"
    database_url = f"sqlite:///{database.as_posix()}"
    previous = os.environ.get("OAI_DATABASE_URL")
    os.environ["OAI_DATABASE_URL"] = database_url
    get_settings.cache_clear()

    try:
        command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
        result = verify_database(database_url)
    finally:
        if previous is None:
            os.environ.pop("OAI_DATABASE_URL", None)
        else:
            os.environ["OAI_DATABASE_URL"] = previous
        get_settings.cache_clear()

    assert result.revision == TARGET_REVISION


def test_d171_introduces_no_database_migration() -> None:
    versions = ROOT / "backend" / "alembic" / "versions"

    assert not any("d171" in path.name.casefold() for path in versions.glob("*.py"))


def test_historical_tests_do_not_freeze_stale_current_revision() -> None:
    for path in (
        "backend/tests/test_d99_workspace_context_ux_security.py",
        "backend/tests/test_d100_integration_security_inventory.py",
    ):
        source = _source(path)
        assert (
            'assert TARGET_REVISION == "0013_context_snapshot_persistence"'
            not in source
        )


def test_d137_scope_evidence_is_not_current_working_tree_state() -> None:
    source = _source("backend/tests/test_d137_newborn_brain_security.py")

    assert '"status", "--porcelain"' not in source
    assert "D137_IMPLEMENTATION_COMMIT" in source
    assert '"diff-tree"' in source


def test_d140_d143_do_not_freeze_current_mutable_files_by_blob_sha() -> None:
    for path in (
        "backend/tests/test_d140_cognitive_runtime_adoption_security.py",
        "backend/tests/test_d141_cognitive_runtime_assurance_security.py",
        "backend/tests/test_d142_cognitive_runtime_readiness_security.py",
        "backend/tests/test_d143_cognitive_runtime_promotion_advisory_security.py",
    ):
        source = _source(path)
        assert "_git_blob_sha(" not in source
        assert "import hashlib" not in source
        assert "_assert_python_surface(" in source
        assert "_PROTECTED_BLOBS" in source


def test_d148_allows_only_the_later_authorized_composition_seam() -> None:
    source = _source(
        "backend/tests/test_d148_cognitive_trusted_experience_retrieval_security.py"
    )

    assert 'dependencies = _source("backend/app/api/dependencies.py")' in source
    assert 'assert "TrustedExperienceRetrievalService" in dependencies' in source
    assert 'assert "CognitiveTrustedExperienceRuntimeBinder" in dependencies' in source


def test_d171_reconciliation_adds_no_skip_or_xfail_escape_hatch() -> None:
    for path in (
        "backend/tests/test_context_snapshot_persistence.py",
        "backend/tests/test_d99_workspace_context_ux_security.py",
        "backend/tests/test_d100_integration_security_inventory.py",
        "backend/tests/test_d137_newborn_brain_security.py",
        "backend/tests/test_d140_cognitive_runtime_adoption_security.py",
        "backend/tests/test_d141_cognitive_runtime_assurance_security.py",
        "backend/tests/test_d142_cognitive_runtime_readiness_security.py",
        "backend/tests/test_d143_cognitive_runtime_promotion_advisory_security.py",
        "backend/tests/test_d148_cognitive_trusted_experience_retrieval_security.py",
        "backend/tests/test_d171_full_regression_baseline_stabilization.py",
    ):
        source = _source(path)
        assert "pytest.mark." + "skip" not in source
        assert "pytest.mark." + "xfail" not in source
