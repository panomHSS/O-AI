from __future__ import annotations

import ast
from dataclasses import fields, replace
from pathlib import Path

import pytest

from app.contracts.governed_execution_receipt_postcondition import (
    GovernedExecutionReceiptPostcondition,
)
from tests.test_d191_governed_execution_receipt_postcondition import outcome, projector

ROOT = Path(__file__).resolve().parents[2]

AUTHORITY_FIELDS = (
    "approval_authority",
    "authorization_authority",
    "execution_authority",
    "idempotency_authority",
    "retry_authority",
    "rollback_authority",
    "compensation_authority",
    "trust_authority",
    "learning_authority",
    "memory_write_authority",
    "persistence_authority",
    "experience_write_authority",
    "routing_authority",
    "model_selection_authority",
    "policy_authority",
    "configuration_authority",
    "automatic_retry",
    "automatic_rollback",
    "automatic_compensation",
    "automatic_learning",
    "automatic_execution",
)


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def imports(path: str) -> set[str]:
    tree = ast.parse(source(path))
    result = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module)
    return result


def sample():
    binding, decision = outcome()
    return projector().project(binding=binding, decision_outcome=decision)


def test_d191_projection_excludes_raw_parameters_results_and_lifecycle_identity():
    names = {field.name for field in fields(GovernedExecutionReceiptPostcondition)}
    forbidden = {
        "parameters",
        "steps",
        "output",
        "error",
        "payload",
        "conversation_id",
        "source_turn_id",
        "source_artifact_digest",
        "feedback_fingerprint",
        "candidate_fingerprint",
        "review_fingerprint",
        "promotion_fingerprint",
        "trusted_execution_experience_id",
        "evidence_set_fingerprint",
        "advisory_fingerprint",
        "binding_fingerprint",
        "prompt",
        "response",
        "history",
        "created_at",
        "updated_at",
    }
    assert forbidden.isdisjoint(names)


def test_d191_projection_has_no_retry_rollback_or_preference_decision():
    names = {field.name for field in fields(GovernedExecutionReceiptPostcondition)}
    forbidden = {
        "should_retry",
        "retry_decision",
        "should_rollback",
        "rollback_decision",
        "should_compensate",
        "compensation_decision",
        "safe_to_execute",
        "should_execute",
        "recommended_to_execute",
        "preferred_adapter",
        "preferred_operation",
        "score",
        "rank",
        "weight",
        "confidence",
    }
    assert forbidden.isdisjoint(names)


def test_d191_all_authority_fields_are_hard_false():
    value = sample()
    for name in AUTHORITY_FIELDS:
        assert getattr(value, name) is False
        with pytest.raises(ValueError):
            replace(value, **{name: True})


def test_d191_has_no_database_network_provider_or_memory_dependencies():
    paths = (
        "backend/app/contracts/governed_execution_receipt_postcondition.py",
        "backend/app/services/governed_execution_receipt_postcondition.py",
    )
    modules = set()
    for path in paths:
        modules |= imports(path)
    forbidden = (
        "sqlalchemy",
        "app.models",
        "app.repositories",
        "requests",
        "httpx",
        "socket",
        "subprocess",
        "app.services.memories",
        "app.repositories.memories",
        "app.services.ai_runtime",
        "app.services.ai_router",
        "app.services.tool_runtime",
        "app.services.module_runtime",
        "app.services.command_orchestrator",
        "app.services.cognitive_executive",
    )
    for prefix in forbidden:
        assert not any(
            module == prefix or module.startswith(prefix + ".")
            for module in modules
        )


def test_d191_has_no_d182_to_d190_dependency():
    modules = imports(
        "backend/app/services/governed_execution_receipt_postcondition.py"
    )
    forbidden_fragments = (
        "governed_execution_outcome_feedback",
        "governed_execution_experience",
        "trusted_execution_experience",
    )
    for fragment in forbidden_fragments:
        assert not any(fragment in module for module in modules)


def test_d191_only_uses_execution_guard_for_deterministic_plan_digest():
    text = source("backend/app/services/governed_execution_receipt_postcondition.py")
    assert (
        "from app.services.execution_guard import execution_plan_digest"
        in text
    )
    for token in (
        "ExecutionGuard(",
        ".authorize(",
        "ExecutionPlanner(",
        "CommandExecutionCoordinator(",
        "ToolRuntime(",
        "ModuleRuntime(",
    ):
        assert token not in text


def test_d191_service_contains_no_write_retry_rollback_or_compensation_primitive():
    text = source("backend/app/services/governed_execution_receipt_postcondition.py")
    for token in (
        ".commit(",
        ".rollback(",
        ".add(",
        ".delete(",
        ".update(",
        ".execute(",
        ".retry(",
        ".compensate(",
        "write_memory(",
    ):
        assert token not in text


def test_d191_has_no_llm_embedding_or_similarity_logic():
    text = source(
        "backend/app/services/governed_execution_receipt_postcondition.py"
    ).lower()
    for token in (
        "openai",
        "embedding",
        "vector",
        "cosine",
        "fuzzy",
        "semantic_search",
    ):
        assert token not in text


def test_d191_is_not_public_api_or_existing_runtime_wired():
    needle = "governed_execution_receipt_postcondition"
    class_name = "GovernedExecutionReceiptPostconditionProjector"
    for path in (
        "backend/app/api/dependencies.py",
        "backend/app/api/router.py",
        "backend/app/services/owner_approved_governed_execution.py",
        "backend/app/services/command_execution_coordinator.py",
        "backend/app/services/governed_execution_outcome_feedback.py",
        "backend/app/services/governed_execution_experience_runtime.py",
        "backend/app/services/governed_execution_experience_advisory_runtime_binding.py",
    ):
        text = source(path)
        assert needle not in text
        assert class_name not in text


def test_d191_result_output_and_error_are_not_read_by_projector():
    text = source("backend/app/services/governed_execution_receipt_postcondition.py")
    assert ".output" not in text
    assert ".error" not in text


def test_d191_succeeded_result_never_becomes_verified_postcondition():
    value = sample()
    assert value.result_status == "succeeded"
    assert value.postcondition_status == "unverified"
    assert "verified" not in {value.postcondition_status}
