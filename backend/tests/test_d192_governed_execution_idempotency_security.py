from __future__ import annotations

import ast
from dataclasses import fields, replace
from pathlib import Path

import pytest

from app.contracts.governed_execution_idempotency import (
    GovernedExecutionIdempotencyAssessment,
)
from tests.test_d192_governed_execution_idempotency import (
    HistoryStub,
    binding,
    evaluator,
    receipt,
)

ROOT = Path(__file__).resolve().parents[2]

AUTHORITY_FIELDS = (
    "approval_authority",
    "authorization_authority",
    "execution_authority",
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
    current = binding()
    prior = receipt(current)
    return evaluator(HistoryStub((prior,))).evaluate(binding=current)


def test_d192_projection_excludes_raw_and_execution_instance_identity():
    names = {field.name for field in fields(GovernedExecutionIdempotencyAssessment)}
    forbidden = {
        "parameters",
        "steps",
        "output",
        "error",
        "payload",
        "conversation_id",
        "source_turn_id",
        "source_artifact_digest",
        "approval_id",
        "execution_request_id",
        "plan_digest",
        "result",
        "prompt",
        "response",
        "history",
        "created_at",
        "updated_at",
        "feedback_fingerprint",
        "candidate_fingerprint",
        "review_fingerprint",
        "promotion_fingerprint",
        "trusted_execution_experience_id",
        "advisory_fingerprint",
    }
    assert forbidden.isdisjoint(names)


def test_d192_projection_has_no_positive_execution_or_retry_override_fields():
    names = {field.name for field in fields(GovernedExecutionIdempotencyAssessment)}
    forbidden = {
        "safe_to_execute",
        "should_execute",
        "recommended_to_execute",
        "retry_allowed",
        "should_retry",
        "retry_now",
        "force_execute",
        "ignore_duplicate",
        "override_idempotency",
        "should_rollback",
        "should_compensate",
    }
    assert forbidden.isdisjoint(names)


def test_d192_all_authority_fields_are_hard_false():
    value = sample()
    for name in AUTHORITY_FIELDS:
        assert getattr(value, name) is False
        with pytest.raises(ValueError):
            replace(value, **{name: True})


def test_d192_clear_still_has_no_execution_authority():
    value = evaluator(HistoryStub()).evaluate(binding=binding())
    assert value.status == "clear"
    assert value.automatic_reexecution_suppressed is False
    assert value.execution_authority is False
    assert value.authorization_authority is False


def test_d192_production_has_no_database_network_provider_memory_dependencies():
    modules = imports(
        "backend/app/contracts/governed_execution_idempotency.py"
    ) | imports(
        "backend/app/services/governed_execution_idempotency.py"
    )
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
        "app.services.execution_planner",
        "app.services.execution_guard",
        "app.services.command_execution_coordinator",
    )
    for prefix in forbidden:
        assert not any(
            module == prefix or module.startswith(prefix + ".")
            for module in modules
        )


def test_d192_service_depends_on_d181_d191_workspace_only_for_domain_inputs():
    modules = imports("backend/app/services/governed_execution_idempotency.py")
    allowed_app = {
        "app.contracts.governed_execution_idempotency",
        "app.contracts.governed_execution_receipt_postcondition",
        "app.contracts.owner_approved_governed_execution",
        "app.contracts.workspace",
    }
    app_modules = {module for module in modules if module.startswith("app.")}
    assert app_modules == allowed_app


def test_d192_has_no_d182_to_d190_experience_dependency():
    modules = imports("backend/app/services/governed_execution_idempotency.py")
    forbidden_fragments = (
        "governed_execution_outcome_feedback",
        "governed_execution_experience",
        "trusted_execution_experience",
        "review",
        "trust",
        "advisory",
    )
    for fragment in forbidden_fragments:
        assert not any(fragment in module for module in modules)


def test_d192_service_contains_no_write_execute_retry_or_recovery_primitive():
    text = source("backend/app/services/governed_execution_idempotency.py")
    for token in (
        ".commit(",
        ".rollback(",
        ".add(",
        ".delete(",
        ".update(",
        ".execute(",
        ".authorize(",
        ".retry(",
        ".compensate(",
        "write_memory(",
    ):
        assert token not in text


def test_d192_service_does_not_read_result_output_or_error():
    text = source("backend/app/services/governed_execution_idempotency.py")
    assert ".output" not in text
    assert ".error" not in text
    assert "result_status" not in text


def test_d192_has_no_llm_embedding_fuzzy_or_semantic_dedup_logic():
    text = source("backend/app/services/governed_execution_idempotency.py").lower()
    for token in (
        "openai",
        "embedding",
        "vector",
        "cosine",
        "fuzzy",
        "semantic_search",
        "similarity",
    ):
        assert token not in text


def test_d192_is_not_public_api_or_existing_runtime_wired():
    needle = "governed_execution_idempotency"
    class_name = "GovernedExecutionIdempotencyEvaluator"
    for path in (
        "backend/app/api/dependencies.py",
        "backend/app/api/router.py",
        "backend/app/services/owner_approved_governed_execution.py",
        "backend/app/services/command_execution_coordinator.py",
        "backend/app/services/governed_action.py",
        "backend/app/services/governed_execution_receipt_postcondition.py",
        "backend/app/services/governed_execution_outcome_feedback.py",
        "backend/app/services/governed_execution_experience_runtime.py",
        "backend/app/services/governed_execution_experience_advisory_runtime_binding.py",
    ):
        text = source(path)
        assert needle not in text
        assert class_name not in text


def test_d192_history_query_exposes_no_execution_instance_or_raw_action_fields():
    current = binding()
    history = HistoryStub()
    evaluator(history).evaluate(binding=current)
    query = history.queries[0]
    names = set(query.__dataclass_fields__)
    forbidden = {
        "parameters",
        "conversation_id",
        "source_turn_id",
        "source_artifact_digest",
        "approval_id",
        "execution_request_id",
        "plan_digest",
        "output",
        "error",
    }
    assert forbidden.isdisjoint(names)


def test_d192_unavailable_does_not_expose_history_exception_detail():
    value = evaluator(
        HistoryStub(error=RuntimeError("private database/provider detail"))
    ).evaluate(binding=binding())
    rendered = repr(value)
    assert "private database" not in rendered
    assert "provider detail" not in rendered
