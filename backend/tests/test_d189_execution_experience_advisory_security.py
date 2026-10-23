from __future__ import annotations

import ast
from dataclasses import fields, replace
from pathlib import Path

import pytest

from app.contracts.governed_execution_experience_advisory import (
    ExecutionExperienceAdvisory,
)
from app.services.trusted_execution_experience_advisory import (
    TrustedExecutionExperienceAdvisoryEvaluator,
)
from tests.test_d189_execution_experience_advisory import evaluate, make_set

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
    "routing_authority",
    "model_selection_authority",
    "policy_authority",
    "configuration_authority",
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


def test_d189_advisory_projection_is_privacy_minimized():
    names = {field.name for field in fields(ExecutionExperienceAdvisory)}
    forbidden = {
        "trusted_execution_experience_id",
        "promotion_fingerprint",
        "conversation_id",
        "source_turn_id",
        "approval_id",
        "execution_request_id",
        "plan_digest",
        "source_artifact_digest",
        "intent_digest",
        "source_feedback_fingerprint",
        "source_candidate_fingerprint",
        "source_review_fingerprint",
        "source_d186_record_fingerprint",
        "raw_result",
        "output",
        "error",
        "parameters",
        "payload",
        "prompt",
        "response",
        "history",
        "created_at",
        "updated_at",
    }
    assert forbidden.isdisjoint(names)


def test_d189_output_has_no_decision_preference_or_score_fields():
    names = {field.name for field in fields(ExecutionExperienceAdvisory)}
    forbidden = {
        "score",
        "rank",
        "weight",
        "confidence",
        "recommendation",
        "recommendation_text",
        "instruction",
        "safe_to_execute",
        "should_execute",
        "preferred_adapter",
        "preferred_operation",
        "approval",
        "authorization",
        "policy_decision",
        "routing_decision",
        "execution_decision",
    }
    assert forbidden.isdisjoint(names)


def test_d189_all_authority_fields_are_hard_false():
    result = evaluate(make_set((0,)))
    for name in AUTHORITY_FIELDS:
        assert getattr(result, name) is False
        with pytest.raises(ValueError):
            replace(result, **{name: True})


def test_d189_contract_and_service_have_no_persistence_or_network_dependencies():
    modules = imports(
        "backend/app/contracts/governed_execution_experience_advisory.py"
    ) | imports(
        "backend/app/services/trusted_execution_experience_advisory.py"
    )
    forbidden = (
        "sqlalchemy",
        "app.models",
        "app.repositories",
        "requests",
        "httpx",
        "socket",
        "subprocess",
    )
    for prefix in forbidden:
        assert not any(
            module == prefix or module.startswith(prefix + ".")
            for module in modules
        )


def test_d189_service_has_no_ai_memory_or_execution_runtime_dependencies():
    modules = imports(
        "backend/app/services/trusted_execution_experience_advisory.py"
    )
    forbidden = (
        "app.services.ai_runtime",
        "app.services.ai_router",
        "app.services.execution_planner",
        "app.services.execution_guard",
        "app.services.execution_approval",
        "app.services.command_execution",
        "app.services.command_orchestrator",
        "app.services.cognitive_executive",
        "app.services.tool_runtime",
        "app.services.module_runtime",
        "app.services.memories",
    )
    for prefix in forbidden:
        assert not any(
            module == prefix or module.startswith(prefix + ".")
            for module in modules
        )


def test_d189_service_contains_no_write_primitive():
    text = source(
        "backend/app/services/trusted_execution_experience_advisory.py"
    )
    for forbidden in (
        ".commit(",
        ".rollback(",
        ".add(",
        ".delete(",
        ".update(",
        "create_",
        "revoke(",
    ):
        assert forbidden not in text


def test_d189_has_no_llm_embedding_or_similarity_logic():
    text = source(
        "backend/app/services/trusted_execution_experience_advisory.py"
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


def test_d189_does_not_depend_on_d147_d149_or_d150_domains():
    combined = source(
        "backend/app/contracts/governed_execution_experience_advisory.py"
    ) + source(
        "backend/app/services/trusted_execution_experience_advisory.py"
    )
    for forbidden in (
        "cognitive_trusted_experience_retrieval",
        "cognitive_trusted_experience_advisory",
        "cognitive_trusted_experience_runtime_binding",
        "trusted_experience_retrieval",
    ):
        assert forbidden not in combined


def test_d189_is_not_public_api_or_runtime_wired():
    for path in (
        "backend/app/api/dependencies.py",
        "backend/app/api/router.py",
        "backend/app/services/command_orchestrator.py",
        "backend/app/services/cognitive_executive.py",
    ):
        text = source(path)
        assert "TrustedExecutionExperienceAdvisoryEvaluator" not in text
        assert "governed_execution_experience_advisory" not in text
        assert "trusted_execution_experience_advisory" not in text


def test_d189_invalid_input_exposes_no_attacker_source_metadata():
    result = TrustedExecutionExperienceAdvisoryEvaluator.evaluate(
        evidence_set={"workspace_id": "company", "fingerprint": "attacker"}
    )
    assert result.advisory_status == "invalid_evidence"
    assert result.workspace_id is None
    assert result.source_evidence_set_fingerprint is None
    assert result.source_selected_count is None
    assert result.source_truncated is None


def test_d189_evaluator_is_stateless():
    evaluator = TrustedExecutionExperienceAdvisoryEvaluator()
    assert vars(evaluator) == {}
    first = evaluator.evaluate(evidence_set=make_set((0, 3)))
    second = evaluator.evaluate(evidence_set=make_set((0, 3)))
    assert first == second
    assert vars(evaluator) == {}
