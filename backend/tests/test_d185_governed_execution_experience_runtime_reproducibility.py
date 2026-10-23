from __future__ import annotations

import ast
from pathlib import Path

from app.services.governed_execution_experience_runtime import (
    GovernedExecutionExperienceRuntimeIntegration,
    GovernedExecutionExperienceRuntimeStore,
)
from app.services.governed_execution_outcome_feedback import (
    GovernedExecutionOutcomeFeedbackStore,
)
from tests.test_d183_governed_execution_experience_candidate import feedback_for

ROOT = Path(__file__).resolve().parents[2]


def project(feedback):
    feedback_store = GovernedExecutionOutcomeFeedbackStore()
    feedback_store.register(feedback)
    runtime_store = GovernedExecutionExperienceRuntimeStore()
    integration = GovernedExecutionExperienceRuntimeIntegration(
        feedback_store=feedback_store,
        runtime_store=runtime_store,
    )
    assert integration.try_integrate(feedback.approval_id)
    outcome = runtime_store.get(feedback.approval_id)
    assert outcome is not None
    return outcome


def test_d185_same_feedback_produces_equal_runtime_outcome():
    feedback = feedback_for()
    assert project(feedback) == project(feedback)


def test_d185_same_feedback_preserves_equal_candidate_and_review_fingerprints():
    feedback = feedback_for()
    first = project(feedback)
    second = project(feedback)
    assert first.candidate is not None and second.candidate is not None
    assert first.review is not None and second.review is not None
    assert (
        first.candidate.candidate_fingerprint
        == second.candidate.candidate_fingerprint
    )
    assert first.review.proposal is not None and second.review.proposal is not None
    assert (
        first.review.proposal.review_fingerprint
        == second.review.proposal.review_fingerprint
    )


def test_d185_owner_decline_is_deterministic():
    feedback = feedback_for(
        decision="denied",
        execution_status="blocked",
        result_status=None,
    )
    first = project(feedback)
    second = project(feedback)
    assert first == second
    assert first.runtime_status == "review_ineligible"
    assert first.review is not None
    assert first.review.reason_code == "owner_declined"


def test_d185_adverse_outcome_is_deterministic():
    feedback = feedback_for(
        decision="approved",
        execution_status="completed",
        result_status="failed",
    )
    first = project(feedback)
    second = project(feedback)
    assert first == second
    assert first.runtime_status == "review_ineligible"
    assert first.review is not None
    assert first.review.reason_code == "adverse_execution_outcome"


def test_d185_contract_and_service_add_no_random_time_secret_or_generated_uuid():
    for rel in (
        "backend/app/contracts/governed_execution_experience_runtime.py",
        "backend/app/services/governed_execution_experience_runtime.py",
    ):
        tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
        modules = set()
        calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
        roots = {module.split(".", 1)[0] for module in modules}
        assert roots.isdisjoint({"random", "secrets", "time"})
        assert "uuid4" not in calls


def test_d185_new_tests_add_no_skip_or_xfail_debt():
    forbidden = (
        "pytest.mark." + "skip",
        "pytest.mark." + "xfail",
        "unittest." + "skip",
    )
    for path in (
        "backend/tests/test_d185_governed_execution_experience_runtime.py",
        "backend/tests/test_d185_governed_execution_experience_runtime_api.py",
        "backend/tests/test_d185_governed_execution_experience_runtime_security.py",
        "backend/tests/test_d185_governed_execution_experience_runtime_reproducibility.py",
    ):
        lowered = (ROOT / path).read_text(encoding="utf-8").casefold()
        assert all(marker not in lowered for marker in forbidden)


def test_d185_runtime_service_is_process_local_and_has_no_durable_store_dependency():
    tree = ast.parse(
        (
            ROOT
            / "backend/app/services/governed_execution_experience_runtime.py"
        ).read_text(encoding="utf-8")
    )
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    roots = {module.split(".", 1)[0] for module in modules}
    assert roots.isdisjoint(
        {
            "sqlalchemy",
            "sqlite3",
            "alembic",
            "multiprocessing",
            "queue",
        }
    )
