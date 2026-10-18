\
from __future__ import annotations

import ast
import inspect
from dataclasses import fields, replace
from pathlib import Path

import pytest

from app.contracts.cognitive_brain import CognitiveOrgan
from app.contracts.cognitive_trusted_experience_runtime_binding import (
    CognitiveTrustedExperienceRuntimeBinding,
)
from app.services.cognitive_executive import CognitiveExecutive
from tests.test_d150_cognitive_trusted_experience_runtime_binding import (
    AUTHORITY_FIELDS,
    bind,
    make_task,
)

ROOT = Path(__file__).resolve().parents[2]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def imports(path: str) -> set[str]:
    tree = ast.parse(text(path))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module)
    return result


def run_case(case: int) -> None:
    slot = (case - 1) % 16

    if slot == 0:
        result, _ = bind(tiers=(0,))
        names = {field.name for field in fields(CognitiveTrustedExperienceRuntimeBinding)}
        assert set(AUTHORITY_FIELDS).isdisjoint(names)
        for name in AUTHORITY_FIELDS:
            with pytest.raises(TypeError):
                replace(result, **{name: True})
    elif slot == 1:
        names = {field.name for field in fields(CognitiveTrustedExperienceRuntimeBinding)}
        forbidden = {
            "prompt", "response", "normalized_request", "conversation_id",
            "project_id", "request_id", "turn_id", "context", "memory",
            "knowledge", "draft", "chain_of_thought", "decision_comment",
            "history", "instruction", "policy_decision", "routing_decision",
            "execution_decision",
        }
        assert forbidden.isdisjoint(names)
    elif slot == 2:
        names = {field.name for field in fields(CognitiveTrustedExperienceRuntimeBinding)}
        assert {
            "authorized_adapter_id",
            "authorized_model_id",
            "authorized_profile_id",
            "preferred_model",
            "preferred_adapter",
            "preferred_profile",
            "score",
            "rank",
            "weight",
            "confidence",
        }.isdisjoint(names)
    elif slot == 3:
        service_imports = imports(
            "backend/app/services/cognitive_trusted_experience_runtime_binding.py"
        )
        for forbidden in (
            "app.services.ai_runtime",
            "app.services.ai_router",
            "app.services.execution_planner",
            "app.services.execution_guard",
            "app.services.command_orchestrator",
            "app.services.memories",
            "app.services.planning",
            "app.services.reasoning",
            "sqlalchemy",
            "requests",
            "httpx",
            "socket",
            "subprocess",
        ):
            assert not any(
                module == forbidden or module.startswith(forbidden + ".")
                for module in service_imports
            )
    elif slot == 4:
        source = text(
            "backend/app/services/cognitive_trusted_experience_runtime_binding.py"
        ).lower()
        for forbidden in (
            "openai", "embedding", "vector", "cosine", "fuzzy",
            "preferred_model", "route_mode",
        ):
            assert forbidden not in source
    elif slot == 5:
        source = text(
            "backend/app/services/cognitive_trusted_experience_runtime_binding.py"
        )
        for forbidden in (
            ".commit(", ".rollback(", "session.add(", "session.delete(",
            "create_pending(", ".transition(", "update(",
        ):
            assert forbidden not in source
    elif slot == 6:
        for method_name in ("_primary_prompt", "_critic_prompt", "_revision_prompt"):
            source = inspect.getsource(getattr(CognitiveExecutive, method_name))
            assert "trusted_experience" not in source
            assert "runtime_binding" not in source
    elif slot == 7:
        source = text("backend/app/services/command_orchestrator.py")
        assert "trusted_experience_binding" not in source
        assert "cognitive_trusted_experience_runtime_binding" not in source
    elif slot == 8:
        source = text("backend/app/api/dependencies.py")
        assert "TrustedExperienceRetrievalService" in source
        assert "CognitiveTrustedExperienceRuntimeBinder" in source
        assert "cognitive_trusted_experience_advisory" not in source
    elif slot == 9:
        for path in (
            "backend/app/api/v1/chat.py",
            "backend/app/api/router.py",
            "backend/app/schemas/chat.py",
            "backend/app/schemas/diagnostics.py",
        ):
            source = text(path)
            assert "cognitive_trusted_experience_runtime_binding" not in source
            assert "trusted_experience_binding" not in source
    elif slot == 10:
        source = (
            text("backend/app/contracts/cognitive_trusted_experience_runtime_binding.py")
            + text("backend/app/services/cognitive_trusted_experience_runtime_binding.py")
        ).lower()
        for forbidden in (
            "background", "scheduler", "thread", "cache", "alembic",
            "create_all", "migration",
        ):
            assert forbidden not in source
    elif slot == 11:
        assert len(CognitiveOrgan) == 17
        assert "CognitiveOrgan" not in text(
            "backend/app/contracts/cognitive_trusted_experience_runtime_binding.py"
        )
        assert "CognitiveOrgan" not in text(
            "backend/app/services/cognitive_trusted_experience_runtime_binding.py"
        )
    elif slot == 12:
        result, _ = bind()
        assert result.binding_status == "bound"
        assert result.advisory_status == "no_evidence"
        assert result.source_selected_count == 0
    elif slot == 13:
        unavailable = CognitiveTrustedExperienceRuntimeBinding.unavailable(
            make_task().envelope.workspace_id
        )
        assert unavailable.binding_status == "unavailable"
        assert unavailable.source_evidence_set_fingerprint is None
        assert unavailable.source_selected_count is None
        assert unavailable.source_truncated is None
        assert unavailable.advisory_status is None
        assert unavailable.best_relevance_tier is None
        assert unavailable.mixed_relevance is None
        assert unavailable.advisory_fingerprint is None
    elif slot == 14:
        executive = text("backend/app/services/cognitive_executive.py")
        before = executive.index("trusted_experience_binding =")
        synth = executive.index("self._synthesize_verify(", before)
        assert before < synth
        assert "trusted_experience_binding" not in executive[synth:executive.index(
            "state.draft_response = final_draft", synth
        )]
    else:
        source = text(
            "backend/app/services/cognitive_trusted_experience_runtime_binding.py"
        ).lower()
        assert "for attempt" not in source
        assert "while " not in source
        assert source.count("self._retrieval_service.retrieve(") == 1
        assert source.count("cognitivetrustedexperienceadvisoryevaluator.evaluate(") == 1


@pytest.mark.parametrize(
    "case",
    range(1, 81),
    ids=[f"S{i:02d}" for i in range(1, 81)],
)
def test_d150_security_matrix(case: int) -> None:
    run_case(case)
