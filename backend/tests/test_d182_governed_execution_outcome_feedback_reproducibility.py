from __future__ import annotations

import ast
from pathlib import Path

from app.services.governed_execution_outcome_feedback import (
    GovernedExecutionOutcomeFeedbackRecorder,
    GovernedExecutionOutcomeFeedbackStore,
)
from tests.test_d182_governed_execution_outcome_feedback import binding_for, outcome

ROOT = Path(__file__).resolve().parents[2]


def test_d182_same_binding_outcome_has_stable_fingerprint():
    decision = outcome()
    binding = binding_for(decision)
    first_store = GovernedExecutionOutcomeFeedbackStore()
    second_store = GovernedExecutionOutcomeFeedbackStore()
    assert GovernedExecutionOutcomeFeedbackRecorder(store=first_store).try_record(binding, decision)
    assert GovernedExecutionOutcomeFeedbackRecorder(store=second_store).try_record(binding, decision)
    first = first_store.get(decision.approval_id)
    second = second_store.get(decision.approval_id)
    assert first is not None and second is not None
    assert first.classification == second.classification
    assert first.feedback_fingerprint == second.feedback_fingerprint


def test_d182_exact_duplicate_recording_is_idempotent():
    decision = outcome()
    binding = binding_for(decision)
    store = GovernedExecutionOutcomeFeedbackStore()
    recorder = GovernedExecutionOutcomeFeedbackRecorder(store=store)
    assert recorder.try_record(binding, decision)
    first = store.get(decision.approval_id)
    assert recorder.try_record(binding, decision)
    assert store.get(decision.approval_id) is first
    assert store.feedback_count == 1


def test_d182_contract_and_service_add_no_random_time_secret_identity():
    for rel in (
        "backend/app/contracts/governed_execution_outcome_feedback.py",
        "backend/app/services/governed_execution_outcome_feedback.py",
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


def test_d182_new_tests_add_no_skip_or_xfail_debt():
    forbidden = ("pytest.mark." + "skip", "pytest.mark." + "xfail", "unittest." + "skip")
    for path in (
        "backend/tests/test_d182_governed_execution_outcome_feedback.py",
        "backend/tests/test_d182_governed_execution_outcome_feedback_api.py",
        "backend/tests/test_d182_governed_execution_outcome_feedback_security.py",
        "backend/tests/test_d182_governed_execution_outcome_feedback_reproducibility.py",
    ):
        lowered = (ROOT / path).read_text(encoding="utf-8").casefold()
        assert all(marker not in lowered for marker in forbidden)


def test_d182_store_is_process_local_only():
    text = (ROOT / "backend/app/services/governed_execution_outcome_feedback.py").read_text(encoding="utf-8").casefold()
    assert "sqlite" not in text
    assert "repository" not in text
