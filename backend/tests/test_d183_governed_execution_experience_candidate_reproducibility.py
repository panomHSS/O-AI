from __future__ import annotations

import ast
from pathlib import Path

from app.services.governed_execution_experience_candidate import (
    GovernedExecutionExperienceProjector,
)
from tests.test_d183_governed_execution_experience_candidate import feedback_for

ROOT = Path(__file__).resolve().parents[2]


def test_d183_same_evidence_produces_equal_candidate_and_fingerprint():
    feedback = feedback_for()
    first = GovernedExecutionExperienceProjector.project(feedback)
    second = GovernedExecutionExperienceProjector.project(feedback)
    assert first is not None and second is not None
    assert first == second
    assert first.candidate_fingerprint == second.candidate_fingerprint


def test_d183_source_identity_change_changes_candidate_fingerprint():
    first = GovernedExecutionExperienceProjector.project(
        feedback_for(
            approval_id="approval-d183-a",
            request_id="request-d183-a",
        )
    )
    second = GovernedExecutionExperienceProjector.project(
        feedback_for(
            approval_id="approval-d183-b",
            request_id="request-d183-b",
        )
    )
    assert first is not None and second is not None
    assert first.source_feedback_fingerprint != second.source_feedback_fingerprint
    assert first.candidate_fingerprint != second.candidate_fingerprint


def test_d183_contract_and_service_add_no_random_time_or_secret_identity():
    for rel in (
        "backend/app/contracts/governed_execution_experience_candidate.py",
        "backend/app/services/governed_execution_experience_candidate.py",
    ):
        tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
        roots = {module.split(".", 1)[0] for module in modules}
        assert roots.isdisjoint({"random", "secrets", "time"})


def test_d183_new_tests_add_no_skip_or_xfail_debt():
    forbidden = (
        "pytest.mark." + "skip",
        "pytest.mark." + "xfail",
        "unittest." + "skip",
    )
    for path in (
        "backend/tests/test_d183_governed_execution_experience_candidate.py",
        "backend/tests/test_d183_governed_execution_experience_candidate_security.py",
        "backend/tests/test_d183_governed_execution_experience_candidate_reproducibility.py",
    ):
        lowered = (ROOT / path).read_text(encoding="utf-8").casefold()
        assert all(marker not in lowered for marker in forbidden)


def test_d183_implementation_is_storeless_and_process_passive():
    text = (
        ROOT / "backend/app/services/governed_execution_experience_candidate.py"
    ).read_text(encoding="utf-8").casefold()
    for forbidden in (
        "store",
        "repository",
        "sqlite",
        "database",
        "thread",
        "lock(",
        "queue",
        "scheduler",
    ):
        assert forbidden not in text
