from __future__ import annotations

import ast
import inspect
from dataclasses import fields, replace
from pathlib import Path

import pytest

from app.contracts.governed_execution_retry import (
    GovernedExecutionRetryEligibility,
    compute_governed_execution_retry_candidate_fingerprint,
)
from tests.test_d193_governed_execution_retry import assess, idempotency
from tests.test_d192_governed_execution_idempotency import binding, receipt

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


def eligible_sample():
    current = binding()
    prior = receipt(current, result_status="failed")
    idem = idempotency(current, (prior,))
    result, _ = assess(current, idem, (prior,))
    assert result.status == "eligible_for_owner_review"
    return result


def test_d193_projection_excludes_raw_private_and_execution_instance_fields():
    names = {field.name for field in fields(GovernedExecutionRetryEligibility)}
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
        "execution_reason_code",
        "result",
        "prompt",
        "response",
        "history",
        "created_at",
        "updated_at",
        "feedback_fingerprint",
        "review_fingerprint",
        "promotion_fingerprint",
        "trusted_execution_experience_id",
        "advisory_fingerprint",
    }
    assert forbidden.isdisjoint(names)


def test_d193_has_no_positive_retry_or_execution_override_fields():
    names = {field.name for field in fields(GovernedExecutionRetryEligibility)}
    forbidden = {
        "retry_allowed",
        "should_retry",
        "retry_now",
        "safe_to_retry",
        "safe_to_execute",
        "execute_retry",
        "force_retry",
        "bypass_approval",
        "reuse_approval",
        "recommended_to_execute",
        "should_execute",
    }
    assert forbidden.isdisjoint(names)


def test_d193_all_authority_fields_are_hard_false():
    value = eligible_sample()
    for name in AUTHORITY_FIELDS:
        assert getattr(value, name) is False
        with pytest.raises(ValueError):
            replace(value, **{name: True})


def test_d193_reuse_flags_are_hard_false():
    value = eligible_sample()
    for name in (
        "reuse_prior_approval_permitted",
        "reuse_prior_authorization_permitted",
        "reuse_prior_execution_request_permitted",
    ):
        assert getattr(value, name) is False
        with pytest.raises(ValueError):
            replace(value, **{name: True})


def test_d193_fresh_authority_requirements_are_descriptive_not_authority():
    value = eligible_sample()
    assert value.fresh_owner_approval_required is True
    assert value.new_execution_request_required is True
    assert value.approval_authority is False
    assert value.authorization_authority is False
    assert value.retry_authority is False
    assert value.execution_authority is False


def test_d193_candidate_function_takes_no_raw_prior_instance_ids():
    names = set(
        inspect.signature(
            compute_governed_execution_retry_candidate_fingerprint
        ).parameters
    )
    assert {
        "approval_id",
        "execution_request_id",
        "plan_digest",
        "parameters",
        "output",
        "error",
    }.isdisjoint(names)
    assert "prior_receipt_fingerprint" in names


def test_d193_production_has_no_database_network_provider_memory_dependencies():
    modules = imports(
        "backend/app/contracts/governed_execution_retry.py"
    ) | imports(
        "backend/app/services/governed_execution_retry.py"
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
        "app.services.execution_approval_service",
    )
    for prefix in forbidden:
        assert not any(
            module == prefix or module.startswith(prefix + ".")
            for module in modules
        )


def test_d193_service_depends_only_on_d181_d191_d192_workspace_and_d193_contract():
    modules = imports("backend/app/services/governed_execution_retry.py")
    allowed_app = {
        "app.contracts.governed_execution_idempotency",
        "app.contracts.governed_execution_receipt_postcondition",
        "app.contracts.governed_execution_retry",
        "app.contracts.owner_approved_governed_execution",
        "app.contracts.workspace",
    }
    app_modules = {module for module in modules if module.startswith("app.")}
    assert app_modules == allowed_app


def test_d193_has_no_d182_to_d190_experience_dependency():
    modules = imports("backend/app/services/governed_execution_retry.py")
    forbidden_fragments = (
        "governed_execution_outcome_feedback",
        "governed_execution_experience",
        "trusted_execution_experience",
        "review_lifecycle",
        "trust_eligibility",
        "advisory_runtime",
    )
    for fragment in forbidden_fragments:
        assert not any(fragment in module for module in modules)


def test_d193_service_contains_no_write_execute_authorize_or_recovery_primitive():
    text = source("backend/app/services/governed_execution_retry.py")
    for token in (
        ".commit(",
        ".rollback(",
        ".add(",
        ".delete(",
        ".update(",
        ".execute(",
        ".authorize(",
        ".approve(",
        ".retry(",
        ".compensate(",
        "write_memory(",
    ):
        assert token not in text


def test_d193_service_does_not_read_result_output_or_error():
    text = source("backend/app/services/governed_execution_retry.py")
    assert ".output" not in text
    assert ".error" not in text
    assert ".result_status" in text


def test_d193_has_no_llm_embedding_fuzzy_or_provider_error_classification():
    text = source("backend/app/services/governed_execution_retry.py").lower()
    for token in (
        "openai",
        "embedding",
        "vector",
        "cosine",
        "fuzzy",
        "semantic_search",
        "similarity",
        "timeout",
        "rate limit",
        "rate_limit",
        "http status",
    ):
        assert token not in text


def test_d193_is_not_public_api_or_existing_runtime_wired():
    needle = "governed_execution_retry"
    class_name = "GovernedExecutionRetryEvaluator"
    for path in (
        "backend/app/api/dependencies.py",
        "backend/app/api/router.py",
        "backend/app/services/owner_approved_governed_execution.py",
        "backend/app/services/command_execution_coordinator.py",
        "backend/app/services/governed_action.py",
        "backend/app/services/governed_execution_receipt_postcondition.py",
        "backend/app/services/governed_execution_idempotency.py",
        "backend/app/services/governed_execution_outcome_feedback.py",
        "backend/app/services/governed_execution_experience_runtime.py",
        "backend/app/services/governed_execution_experience_advisory_runtime_binding.py",
    ):
        text = source(path)
        assert needle not in text
        assert class_name not in text


def test_d193_spec_freezes_fresh_owner_review_and_no_automatic_retry():
    text = source("docs/specs/D193_EXECUTION_RETRY_V1.md")
    for marker in (
        "Execution failure != Retry authority.",
        "Retry eligibility != Retry authorization.",
        "Prior approval cannot be reused.",
        "fresh_owner_approval_required = true",
        "new_execution_request_required = true",
        "Automatic retry is forbidden.",
        "R1/R2/R3",
        "no DB table",
        "no API/runtime wiring",
    ):
        assert marker in text
