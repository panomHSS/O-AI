from __future__ import annotations

import ast
import inspect
from dataclasses import fields, replace
from pathlib import Path

import pytest

from app.contracts.cognitive_brain import CognitiveOrgan
from app.contracts.cognitive_trusted_experience_consumption import (
    CognitiveTrustedExperienceConsumptionDecision,
)
from app.services.cognitive_executive import CognitiveExecutive
from app.services.cognitive_trusted_experience_consumption import (
    CognitiveTrustedExperienceConsumptionPolicyEvaluator,
)
from tests.test_d150_cognitive_trusted_experience_runtime_binding import (
    AUTHORITY_FIELDS,
    bind,
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
        binding, _ = bind(tiers=(0,))
        result = CognitiveTrustedExperienceConsumptionPolicyEvaluator.evaluate(
            binding=binding
        )
        names = {field.name for field in fields(result)}
        assert set(AUTHORITY_FIELDS).isdisjoint(names)
        for name in AUTHORITY_FIELDS:
            with pytest.raises(TypeError):
                replace(result, **{name: True})
    elif slot == 1:
        names = {
            field.name
            for field in fields(CognitiveTrustedExperienceConsumptionDecision)
        }
        forbidden = {
            "prompt", "response", "normalized_request", "conversation_id",
            "project_id", "request_id", "turn_id", "context", "memory",
            "knowledge", "draft", "chain_of_thought", "decision_comment",
            "history", "instruction", "routing_decision", "execution_decision",
        }
        assert forbidden.isdisjoint(names)
    elif slot == 2:
        names = {
            field.name
            for field in fields(CognitiveTrustedExperienceConsumptionDecision)
        }
        assert {
            "source_selected_count", "best_relevance_tier",
            "authorized_adapter_id", "authorized_model_id",
            "authorized_profile_id", "preferred_model", "preferred_adapter",
            "preferred_profile", "score", "rank", "weight", "confidence",
        }.isdisjoint(names)
    elif slot == 3:
        service_imports = imports(
            "backend/app/services/cognitive_trusted_experience_consumption.py"
        )
        for forbidden in (
            "app.services.ai_runtime",
            "app.services.ai_router",
            "app.services.execution_planner",
            "app.services.execution_guard",
            "app.services.command_orchestrator",
            "app.services.memories",
            "app.repositories",
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
            "backend/app/services/cognitive_trusted_experience_consumption.py"
        ).lower()
        for forbidden in (
            "openai", "embedding", "vector", "cosine", "fuzzy",
            "preferred_model", "route_mode", "confidence_boost",
        ):
            assert forbidden not in source
    elif slot == 5:
        source = text(
            "backend/app/services/cognitive_trusted_experience_consumption.py"
        )
        for forbidden in (
            ".commit(", ".rollback(", "session.add(", "session.delete(",
            "create_pending(", ".transition(", "update(",
        ):
            assert forbidden not in source
    elif slot == 6:
        for method_name in ("_primary_prompt", "_critic_prompt", "_revision_prompt"):
            source = inspect.getsource(getattr(CognitiveExecutive, method_name))
            assert "consumption" not in source
            assert "policy_fingerprint" not in source
    elif slot == 7:
        source = text("backend/app/services/command_orchestrator.py")
        assert "trusted_experience_consumption" not in source
        assert "consumption_decision" not in source
    elif slot == 8:
        source = text("backend/app/api/dependencies.py")
        assert "cognitive_trusted_experience_consumption" not in source
        assert "ConsumptionPolicyEvaluator" not in source
    elif slot == 9:
        for path in (
            "backend/app/api/v1/chat.py",
            "backend/app/api/router.py",
            "backend/app/schemas/chat.py",
            "backend/app/schemas/diagnostics.py",
        ):
            source = text(path)
            assert "cognitive_trusted_experience_consumption" not in source
            assert "trusted_experience_consumption_decision" not in source
    elif slot == 10:
        source = (
            text("backend/app/contracts/cognitive_trusted_experience_consumption.py")
            + text("backend/app/services/cognitive_trusted_experience_consumption.py")
        ).lower()
        for forbidden in (
            "background", "scheduler", "thread", "cache", "alembic",
            "create_all", "migration",
        ):
            assert forbidden not in source
    elif slot == 11:
        assert len(CognitiveOrgan) == 17
        assert "CognitiveOrgan" not in text(
            "backend/app/contracts/cognitive_trusted_experience_consumption.py"
        )
        assert "CognitiveOrgan" not in text(
            "backend/app/services/cognitive_trusted_experience_consumption.py"
        )
    elif slot == 12:
        names = {
            field.name
            for field in fields(CognitiveTrustedExperienceConsumptionDecision)
        }
        assert "source_selected_count" not in names
        assert "best_relevance_tier" not in names
    elif slot == 13:
        source = text(
            "backend/app/services/cognitive_trusted_experience_consumption.py"
        ).lower()
        assert "for attempt" not in source
        assert "while " not in source
        assert "retry" not in source
    elif slot == 14:
        executive = text("backend/app/services/cognitive_executive.py")
        bind_pos = executive.index("trusted_experience_binding =")
        policy_pos = executive.index(
            "trusted_experience_consumption_decision =",
            bind_pos,
        )
        session_pos = executive.index(
            "session = self._invocation_coordinator.new_session(",
            policy_pos,
        )
        synth_pos = executive.index("self._synthesize_verify(", session_pos)
        assert bind_pos < policy_pos < session_pos < synth_pos
        region = executive[synth_pos:executive.index(
            "state.draft_response = final_draft",
            synth_pos,
        )]
        assert "consumption_decision" not in region
    else:
        for method_name in (
            "_build_cognitive_state",
            "_synthesize_verify",
            "_primary_prompt",
            "_critic_prompt",
            "_revision_prompt",
        ):
            source = inspect.getsource(getattr(CognitiveExecutive, method_name))
            assert "consumption_decision" not in source
            assert "ConsumptionPolicyEvaluator" not in source


@pytest.mark.parametrize(
    "case",
    range(1, 81),
    ids=[f"S{i:02d}" for i in range(1, 81)],
)
def test_d151_security_matrix(case: int) -> None:
    run_case(case)
