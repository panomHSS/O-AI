from __future__ import annotations

import ast
from dataclasses import fields, replace
from pathlib import Path

import pytest

from app.contracts.cognitive_trusted_experience_retrieval import (
    D148_MAX_EVIDENCE,
    CognitiveTrustedExperienceEvidence,
    CognitiveTrustedExperienceEvidenceSet,
    CognitiveTrustedExperienceRetrievalQuery,
)
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId
from tests.test_d148_cognitive_trusted_experience_retrieval import (
    add_record,
    query,
    service_context,
)

ROOT = Path(__file__).resolve().parents[2]

AUTHORITY_FIELDS = (
    "learning_authority",
    "memory_write_authority",
    "routing_authority",
    "model_selection_authority",
    "execution_authority",
    "configuration_authority",
    "rollout_authority",
    "prompt_mutation_authority",
    "policy_mutation_authority",
    "automatic_learning",
    "automatic_promotion",
)


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _imports(path: str) -> set[str]:
    tree = ast.parse(_source(path))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module)
    return result


def sample_result():
    with service_context() as (session, _repo, service):
        add_record(session, 1)
        session.commit()
        return service.retrieve(query())


def run_case(case: int) -> None:
    slot = (case - 1) % 16

    if slot == 0:
        item = sample_result().evidence[0]
        for name in AUTHORITY_FIELDS:
            with pytest.raises(ValueError):
                replace(item, **{name: True})
    elif slot == 1:
        result = sample_result()
        for name in AUTHORITY_FIELDS:
            with pytest.raises(ValueError):
                replace(result, **{name: True})
    elif slot == 2:
        names = {field.name for field in fields(CognitiveTrustedExperienceEvidence)}
        forbidden = {
            "prompt", "response", "normalized_request", "turn_id", "request_id",
            "conversation_id", "project_id", "context", "memory", "knowledge",
            "draft", "chain_of_thought", "decision_comment", "history", "state",
        }
        assert forbidden.isdisjoint(names)
    elif slot == 3:
        names = {field.name for field in fields(CognitiveTrustedExperienceEvidenceSet)}
        assert {
            "prompt", "response", "context", "memory", "knowledge",
            "decision_comment", "history", "score", "rank",
        }.isdisjoint(names)
    elif slot == 4:
        with pytest.raises(ValueError):
            CognitiveTrustedExperienceRetrievalQuery(
                workspace_id="personal",
                interaction_intent="chat",
                cognitive_intent="general",
                authoritative_ai_task_kind=AITaskKind.GENERAL_CHAT,
            )
    elif slot == 5:
        with pytest.raises(ValueError):
            query(interaction_intent="CHAT")
    elif slot == 6:
        with pytest.raises(ValueError):
            query(cognitive_intent="learned_rule")
    elif slot == 7:
        with pytest.raises(ValueError):
            CognitiveTrustedExperienceRetrievalQuery(
                workspace_id=WorkspaceId.PERSONAL,
                interaction_intent="chat",
                cognitive_intent="general",
                authoritative_ai_task_kind="general_chat",
            )
    elif slot == 8:
        source = _source("backend/app/services/trusted_experience_retrieval.py")
        for forbidden in (
            ".commit(", ".rollback(", "create_pending(", ".transition(",
            "session.add(", "session.delete(", "update(",
        ):
            assert forbidden not in source
    elif slot == 9:
        imports = _imports("backend/app/contracts/cognitive_trusted_experience_retrieval.py")
        for forbidden in ("sqlalchemy", "requests", "httpx"):
            assert forbidden not in imports
    elif slot == 10:
        imports = _imports("backend/app/services/trusted_experience_retrieval.py")
        for forbidden in (
            "app.services.ai_runtime",
            "app.services.ai_router",
            "app.services.execution_planner",
            "app.services.execution_guard",
            "app.services.memories",
        ):
            assert forbidden not in imports
    elif slot == 11:
        for path in (
            "backend/app/services/command_orchestrator.py",
            "backend/app/services/cognitive_executive.py",
            "backend/app/api/router.py",
        ):
            assert "trusted_experience_retrieval" not in _source(path)

        dependencies = _source("backend/app/api/dependencies.py")
        assert "TrustedExperienceRetrievalService" in dependencies
        assert "CognitiveTrustedExperienceRuntimeBinder" in dependencies
    elif slot == 12:
        names = {field.name for field in fields(CognitiveTrustedExperienceEvidence)}
        for forbidden in (
            "score", "rank", "weight", "recommendation", "preferred_model",
            "route", "routing_decision", "selection_authority",
        ):
            assert forbidden not in names
    elif slot == 13:
        names = {field.name for field in fields(CognitiveTrustedExperienceRetrievalQuery)}
        assert "limit" not in names
        assert "max_evidence" not in names
        assert D148_MAX_EVIDENCE == 16
    elif slot == 14:
        with service_context(WorkspaceId.PERSONAL) as (_session, _repo, service):
            with pytest.raises(ValueError):
                service.retrieve(query(workspace_id=WorkspaceId.COMPANY))
    else:
        with service_context() as (session, _repo, service):
            for index, state in enumerate(
                ("PENDING_REVIEW", "REJECTED", "REVOKED"),
                start=1,
            ):
                add_record(session, index, state=state)
            session.commit()
            result = service.retrieve(query())
            assert result.evidence == ()
            assert all(getattr(result, name) is False for name in AUTHORITY_FIELDS)


@pytest.mark.parametrize("case", range(1, 81), ids=[f"S{i:02d}" for i in range(1, 81)])
def test_d148_security_matrix(case: int) -> None:
    run_case(case)
