from __future__ import annotations

import ast
from pathlib import Path

from app.services.owner_approved_governed_execution import CognitiveExecutionBindingStore
from tests.test_d181_owner_approved_governed_execution import (
    build_d45,
    binding_from,
    proposal,
)


ROOT = Path(__file__).resolve().parents[2]


def test_d181_repeated_exact_registration_is_identity_stable():
    d45, _, _ = build_d45()
    binding = binding_from(proposal(d45))
    store = CognitiveExecutionBindingStore()
    first = store.register(binding)
    second = store.register(binding)
    assert first is binding
    assert second is binding
    assert store.binding_count == 1


def test_d181_contract_and_service_add_no_random_secret_or_time_authority():
    for rel in (
        "backend/app/contracts/owner_approved_governed_execution.py",
        "backend/app/services/owner_approved_governed_execution.py",
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


def test_d181_new_tests_add_no_skip_or_xfail_debt():
    forbidden = (
        "pytest.mark." + "skip",
        "pytest.mark." + "xfail",
        "unittest." + "skip",
    )
    for path in (
        "backend/tests/test_d181_owner_approved_governed_execution.py",
        "backend/tests/test_d181_owner_approved_governed_execution_api.py",
        "backend/tests/test_d181_owner_approved_governed_execution_security.py",
        "backend/tests/test_d181_owner_approved_governed_execution_reproducibility.py",
    ):
        lowered = (ROOT / path).read_text(encoding="utf-8").casefold()
        assert all(marker not in lowered for marker in forbidden)


def test_d181_binding_store_is_process_local_only():
    text = (
        ROOT / "backend/app/services/owner_approved_governed_execution.py"
    ).read_text(encoding="utf-8")
    assert "sqlite" not in text.casefold()
    assert "repository" not in text.casefold()
