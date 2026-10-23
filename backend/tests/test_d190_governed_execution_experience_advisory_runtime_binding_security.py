from __future__ import annotations

import ast
from dataclasses import fields, replace
from pathlib import Path

import pytest

from app.contracts.governed_execution_experience_advisory_runtime_binding import (
    GovernedExecutionExperienceAdvisoryRuntimeBinding,
)
from tests.test_d190_governed_execution_experience_advisory_runtime_binding import (
    RetrievalStub,
    action,
    binder,
    pending,
)

ROOT = Path(__file__).resolve().parents[2]

AUTHORITY_FIELDS = (
    "approval_authority",
    "authorization_authority",
    "execution_authority",
    "retry_authority",
    "rollback_authority",
    "trust_authority",
    "learning_authority",
    "memory_write_authority",
    "persistence_authority",
    "experience_write_authority",
    "routing_authority",
    "model_selection_authority",
    "policy_authority",
    "configuration_authority",
    "automatic_trust",
    "automatic_promotion",
    "automatic_learning",
    "automatic_execution",
)


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def imports(path: str) -> set[str]:
    tree = ast.parse(source(path))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module)
    return result


def sample():
    intent = action()
    return binder(RetrievalStub((0,))).bind(
        intent=intent,
        preparation=pending(intent),
    )


def test_d190_projection_excludes_raw_action_and_experience_identity():
    names = {
        field.name
        for field in fields(GovernedExecutionExperienceAdvisoryRuntimeBinding)
    }
    forbidden = {
        "parameters",
        "source_turn_id",
        "source_artifact_digest",
        "approval_id",
        "execution_request_id",
        "trusted_execution_experience_id",
        "promotion_fingerprint",
        "conversation_id",
        "plan_digest",
        "source_feedback_fingerprint",
        "source_candidate_fingerprint",
        "source_review_fingerprint",
        "source_d186_record_fingerprint",
        "raw_result",
        "output",
        "error",
        "payload",
        "prompt",
        "response",
        "history",
        "created_at",
        "updated_at",
    }
    assert forbidden.isdisjoint(names)


def test_d190_projection_has_no_decision_or_preference_fields():
    names = {
        field.name
        for field in fields(GovernedExecutionExperienceAdvisoryRuntimeBinding)
    }
    forbidden = {
        "safe_to_execute",
        "should_execute",
        "recommended_to_execute",
        "approval",
        "authorization",
        "guard_decision",
        "execution_decision",
        "routing_decision",
        "policy_decision",
        "preferred_adapter",
        "preferred_operation",
        "score",
        "rank",
        "weight",
        "confidence",
    }
    assert forbidden.isdisjoint(names)


def test_d190_all_authority_and_learning_flags_are_hard_false():
    result = sample()
    for name in AUTHORITY_FIELDS:
        assert getattr(result, name) is False
        with pytest.raises(ValueError):
            replace(result, **{name: True})


def test_d190_contract_and_service_have_no_write_or_network_dependencies():
    combined_imports = imports(
        "backend/app/contracts/"
        "governed_execution_experience_advisory_runtime_binding.py"
    ) | imports(
        "backend/app/services/"
        "governed_execution_experience_advisory_runtime_binding.py"
    )
    forbidden_prefixes = (
        "sqlalchemy",
        "app.models",
        "app.repositories",
        "requests",
        "httpx",
        "socket",
        "subprocess",
    )
    for prefix in forbidden_prefixes:
        assert not any(
            module == prefix or module.startswith(prefix + ".")
            for module in combined_imports
        )


def test_d190_has_no_experience_learning_memory_or_trust_write_dependencies():
    modules = imports(
        "backend/app/services/"
        "governed_execution_experience_advisory_runtime_binding.py"
    )
    forbidden = (
        "app.services.governed_execution_outcome_feedback",
        "app.services.governed_execution_experience_candidate",
        "app.services.governed_execution_experience_review",
        "app.services.governed_execution_experience_owner_review",
        "app.services.governed_execution_experience_trust",
        "app.services.cognitive_experience",
        "app.services.memories",
        "app.repositories.memories",
        "app.services.trusted_experience_lifecycle",
    )
    for prefix in forbidden:
        assert not any(
            module == prefix or module.startswith(prefix + ".")
            for module in modules
        )


def test_d190_has_no_ai_routing_guard_or_execution_runtime_dependencies():
    modules = imports(
        "backend/app/services/"
        "governed_execution_experience_advisory_runtime_binding.py"
    )
    forbidden = (
        "app.services.ai_runtime",
        "app.services.ai_router",
        "app.services.execution_planner",
        "app.services.execution_guard",
        "app.services.command_execution",
        "app.services.command_orchestrator",
        "app.services.cognitive_executive",
        "app.services.tool_runtime",
        "app.services.module_runtime",
    )
    for prefix in forbidden:
        assert not any(
            module == prefix or module.startswith(prefix + ".")
            for module in modules
        )


def test_d190_service_contains_no_write_primitive():
    text = source(
        "backend/app/services/"
        "governed_execution_experience_advisory_runtime_binding.py"
    )
    for forbidden in (
        ".commit(",
        ".rollback(",
        ".add(",
        ".delete(",
        ".update(",
        "create_trusted(",
        "create_review(",
        "promote(",
        "revoke(",
        "write_memory(",
    ):
        assert forbidden not in text


def test_d190_has_no_llm_embedding_or_similarity_logic():
    text = source(
        "backend/app/services/"
        "governed_execution_experience_advisory_runtime_binding.py"
    ).lower()
    for forbidden in (
        "openai",
        "embedding",
        "vector",
        "cosine",
        "fuzzy",
        "semantic_search",
    ):
        assert forbidden not in text


def test_d190_is_not_public_api_or_existing_runtime_wired():
    for path in (
        "backend/app/api/dependencies.py",
        "backend/app/api/router.py",
        "backend/app/services/command_orchestrator.py",
        "backend/app/services/cognitive_executive.py",
        "backend/app/services/governed_action_runtime.py",
        "backend/app/services/structured_action_semantic_runtime.py",
        "backend/app/services/explicit_action_semantic_runtime.py",
    ):
        text = source(path)
        assert "GovernedExecutionExperienceAdvisoryRuntimeBinder" not in text
        assert (
            "governed_execution_experience_advisory_runtime_binding"
            not in text
        )


def test_d190_unavailable_does_not_expose_exception_detail():
    intent = action()
    result = binder(
        RetrievalStub(
            error=RuntimeError(
                "private provider payload / secret stack detail"
            )
        )
    ).bind(
        intent=intent,
        preparation=pending(intent),
    )
    rendered = repr(result)
    assert "private provider" not in rendered
    assert "secret stack" not in rendered


def test_d190_binding_does_not_modify_upstream_approval_semantics():
    intent = action()
    preparation = pending(intent)
    before_approval = preparation.approval
    before_status = preparation.status
    before_confirmation = preparation.confirmation_required

    result = binder(RetrievalStub((0,))).bind(
        intent=intent,
        preparation=preparation,
    )
    assert result.binding_status == "bound"
    assert preparation.approval is before_approval
    assert preparation.status == before_status == "pending_approval"
    assert preparation.confirmation_required is before_confirmation is True
