from __future__ import annotations

import ast
from dataclasses import fields, replace
from pathlib import Path

import pytest

from app.contracts.governed_execution_experience_retrieval import (
    TrustedExecutionExperienceEvidence,
    TrustedExecutionExperienceEvidenceSet,
)
from tests.test_d188_trusted_execution_experience_retrieval import (
    add_record,
    query,
    service_context,
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


def sample_result():
    with service_context() as (session, _repository, service):
        add_record(session, 1)
        session.commit()
        return service.retrieve(query())


def test_d188_projection_excludes_raw_and_durable_lineage_fields():
    evidence_fields = {
        field.name for field in fields(TrustedExecutionExperienceEvidence)
    }
    forbidden = {
        "conversation_id",
        "source_turn_id",
        "source_artifact_digest",
        "intent_digest",
        "approval_id",
        "execution_request_id",
        "plan_digest",
        "source_feedback_fingerprint",
        "source_candidate_fingerprint",
        "source_review_fingerprint",
        "source_d186_record_fingerprint",
        "source_review_id",
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
    assert forbidden.isdisjoint(evidence_fields)


def test_d188_all_authority_flags_are_hard_false():
    result = sample_result()
    item = result.evidence[0]
    for name in AUTHORITY_FIELDS:
        assert getattr(item, name) is False
        assert getattr(result, name) is False
        with pytest.raises(ValueError):
            replace(item, **{name: True})
        with pytest.raises(ValueError):
            replace(result, **{name: True})


def test_d188_service_and_retrieval_repository_path_are_read_only():
    service_text = source(
        "backend/app/services/trusted_execution_experience_retrieval.py"
    )
    repository_text = source(
        "backend/app/repositories/trusted_execution_experiences.py"
    )
    for forbidden in (
        ".commit(",
        ".rollback(",
        ".add(",
        ".delete(",
        "create_trusted(",
        ".revoke(",
    ):
        assert forbidden not in service_text

    method = repository_text.split(
        "    def retrieve_trusted_evidence(", 1
    )[1].split("\n    def ", 1)[0]
    for forbidden in (
        ".commit(",
        ".rollback(",
        ".add(",
        ".delete(",
        "update(",
        "create_trusted(",
        "revoke(",
    ):
        assert forbidden not in method


def test_d188_has_no_d147_ai_memory_or_execution_authority_dependencies():
    combined_imports = imports(
        "backend/app/contracts/governed_execution_experience_retrieval.py"
    ) | imports(
        "backend/app/services/trusted_execution_experience_retrieval.py"
    )
    forbidden = {
        "app.repositories.trusted_experiences",
        "app.services.trusted_experience_retrieval",
        "app.services.trusted_experience_lifecycle",
        "app.services.ai_runtime",
        "app.services.ai_router",
        "app.services.execution_planner",
        "app.services.execution_guard",
        "app.services.command_execution",
        "app.services.memories",
        "app.repositories.memories",
    }
    assert forbidden.isdisjoint(combined_imports)


def test_d188_is_not_public_api_or_runtime_wired():
    for path in (
        "backend/app/api/dependencies.py",
        "backend/app/api/router.py",
        "backend/app/services/command_orchestrator.py",
        "backend/app/services/cognitive_executive.py",
    ):
        assert "TrustedExecutionExperienceRetrievalService" not in source(path)
        assert "governed_execution_experience_retrieval" not in source(path)


def test_d188_evidence_set_contains_no_score_rank_or_decision_fields():
    names = {
        field.name for field in fields(TrustedExecutionExperienceEvidenceSet)
    }
    assert {
        "score",
        "rank",
        "weight",
        "recommendation",
        "routing_decision",
        "preferred_adapter",
        "authorization",
        "approval",
    }.isdisjoint(names)
