from __future__ import annotations

import ast
from pathlib import Path

from app.services.governed_execution_experience_review import (
    GovernedExecutionExperienceReviewEvaluator,
)
from tests.test_d184_governed_execution_experience_review import candidate_for

ROOT = Path(__file__).resolve().parents[2]


def test_d184_same_evidence_produces_equal_assessment_proposal_and_fingerprint():
    candidate = candidate_for()
    first = GovernedExecutionExperienceReviewEvaluator.evaluate(candidate)
    second = GovernedExecutionExperienceReviewEvaluator.evaluate(candidate)
    assert first == second
    assert first.proposal is not None and second.proposal is not None
    assert first.proposal == second.proposal
    assert first.proposal.review_fingerprint == second.proposal.review_fingerprint


def test_d184_source_identity_change_changes_review_fingerprint():
    first = GovernedExecutionExperienceReviewEvaluator.evaluate(
        candidate_for(
            approval_id="approval-d184-a",
            request_id="request-d184-a",
        )
    )
    second = GovernedExecutionExperienceReviewEvaluator.evaluate(
        candidate_for(
            approval_id="approval-d184-b",
            request_id="request-d184-b",
        )
    )
    assert first.proposal is not None and second.proposal is not None
    assert first.proposal.source_candidate_fingerprint != second.proposal.source_candidate_fingerprint
    assert first.proposal.review_fingerprint != second.proposal.review_fingerprint


def test_d184_safe_lineage_change_changes_review_fingerprint():
    first = GovernedExecutionExperienceReviewEvaluator.evaluate(candidate_for())
    second = GovernedExecutionExperienceReviewEvaluator.evaluate(
        candidate_for(effect="none")
    )
    assert first.proposal is not None and second.proposal is not None
    assert first.proposal.review_fingerprint != second.proposal.review_fingerprint


def test_d184_contract_and_service_add_no_random_time_secret_or_generated_uuid():
    for rel in (
        "backend/app/contracts/governed_execution_experience_review.py",
        "backend/app/services/governed_execution_experience_review.py",
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
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        assert "uuid4" not in calls


def test_d184_new_tests_add_no_skip_or_xfail_debt():
    forbidden = (
        "pytest.mark." + "skip",
        "pytest.mark." + "xfail",
        "unittest." + "skip",
    )
    for path in (
        "backend/tests/test_d184_governed_execution_experience_review.py",
        "backend/tests/test_d184_governed_execution_experience_review_security.py",
        "backend/tests/test_d184_governed_execution_experience_review_reproducibility.py",
    ):
        lowered = (ROOT / path).read_text(encoding="utf-8").casefold()
        assert all(marker not in lowered for marker in forbidden)


def test_d184_implementation_is_storeless_and_process_passive():
    for rel in (
        "backend/app/contracts/governed_execution_experience_review.py",
        "backend/app/services/governed_execution_experience_review.py",
    ):
        tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
        roots = {module.split(".", 1)[0] for module in modules}
        assert roots.isdisjoint(
            {"sqlalchemy", "threading", "multiprocessing", "queue", "sqlite3"}
        )
