from __future__ import annotations

import ast
from dataclasses import fields, replace
from pathlib import Path

import pytest

from app.contracts.cognitive_brain import CognitiveOrgan
from app.contracts.cognitive_trusted_experience_advisory import (
    CognitiveTrustedExperienceAdvisory,
)
from app.contracts.task_aware_ai_routing import AITaskKind
from app.services.cognitive_trusted_experience_advisory import (
    CognitiveTrustedExperienceAdvisoryEvaluator,
)
from tests.test_d149_cognitive_trusted_experience_advisory import evaluate, make_set

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


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _imports(path: str) -> set[str]:
    tree = ast.parse(_text(path))
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
        result = evaluate(make_set((0,)))
        for name in AUTHORITY_FIELDS:
            with pytest.raises(ValueError):
                replace(result, **{name: True})
    elif slot == 1:
        names = {field.name for field in fields(CognitiveTrustedExperienceAdvisory)}
        forbidden = {
            "prompt", "response", "normalized_request", "conversation_id",
            "project_id", "decision_comment", "history",
            "authorized_adapter_id", "authorized_model_id", "authorized_profile_id",
        }
        assert forbidden.isdisjoint(names)
    elif slot == 2:
        names = {field.name for field in fields(CognitiveTrustedExperienceAdvisory)}
        assert {
            "score", "rank", "weight", "confidence", "preferred_model",
            "preferred_adapter", "preferred_profile", "recommendation_text",
        }.isdisjoint(names)
    elif slot == 3:
        imports = (
            _imports("backend/app/contracts/cognitive_trusted_experience_advisory.py")
            | _imports("backend/app/services/cognitive_trusted_experience_advisory.py")
        )
        for forbidden in (
            "sqlalchemy", "app.models", "app.repositories",
            "requests", "httpx", "socket", "subprocess",
        ):
            assert not any(module == forbidden or module.startswith(forbidden + ".") for module in imports)
    elif slot == 4:
        imports = _imports("backend/app/services/cognitive_trusted_experience_advisory.py")
        for forbidden in (
            "app.services.ai_runtime", "app.services.ai_router",
            "app.services.execution_planner", "app.services.execution_guard",
            "app.services.cognitive_executive", "app.services.command_orchestrator",
        ):
            assert not any(module == forbidden or module.startswith(forbidden + ".") for module in imports)
    elif slot == 5:
        for path in (
            "backend/app/services/cognitive_executive.py",
            "backend/app/services/command_orchestrator.py",
            "backend/app/api/dependencies.py",
            "backend/app/api/router.py",
        ):
            assert "cognitive_trusted_experience_advisory" not in _text(path)
    elif slot == 6:
        result = evaluate(None)
        assert result.advisory_status == "invalid_evidence"
        assert result.workspace_id is None
        assert result.source_evidence_set_fingerprint is None
        assert result.source_selected_count is None
        assert result.source_truncated is None
        assert all(getattr(result, name) is False for name in AUTHORITY_FIELDS)
    elif slot == 7:
        source = make_set((0,))
        object.__setattr__(source.evidence[0], "routing_authority", True)
        assert evaluate(source).advisory_status == "invalid_evidence"
    elif slot == 8:
        source = make_set((0,))
        object.__setattr__(
            source.evidence[0],
            "authoritative_ai_task_kind",
            AITaskKind.SOFTWARE_ENGINEERING,
        )
        assert evaluate(source).advisory_status == "invalid_evidence"
    elif slot == 9:
        source = _text("backend/app/services/cognitive_trusted_experience_advisory.py").lower()
        for forbidden in ("openai", "embedding", "vector", "cosine", "fuzzy"):
            assert forbidden not in source
    elif slot == 10:
        source = _text("backend/app/services/cognitive_trusted_experience_advisory.py")
        for forbidden in (
            ".commit(", ".rollback(", "session.add(", "session.delete(",
            "create_pending(", ".transition(",
        ):
            assert forbidden not in source
    elif slot == 11:
        assert len(CognitiveOrgan) == 17
        assert "CognitiveOrgan" not in _text("backend/app/contracts/cognitive_trusted_experience_advisory.py")
        assert "CognitiveOrgan" not in _text("backend/app/services/cognitive_trusted_experience_advisory.py")
    elif slot == 12:
        one = evaluate(make_set((0,)))
        many = evaluate(make_set((0,) * 16))
        assert one.advisory_status == many.advisory_status == "exact_match"
        assert one.best_relevance_tier == many.best_relevance_tier == 0
    elif slot == 13:
        source = make_set((0,))
        changed = replace(
            source.evidence[0],
            authorized_model_id="another-model",
            authorized_adapter_id="another-adapter",
            authorized_profile_id="another-profile",
        )
        object.__setattr__(source, "evidence", (changed,))
        result = evaluate(source)
        assert result.advisory_status == "exact_match"
        assert result.best_relevance_tier == 0
    elif slot == 14:
        names = {field.name for field in fields(CognitiveTrustedExperienceAdvisory)}
        assert {"instruction", "policy_decision", "routing_decision", "execution_decision"}.isdisjoint(names)
    else:
        evaluator = CognitiveTrustedExperienceAdvisoryEvaluator()
        assert vars(evaluator) == {}
        first = evaluator.evaluate(evidence_set=make_set((0, 1)))
        second = evaluator.evaluate(evidence_set=make_set((0, 1)))
        assert first == second
        assert vars(evaluator) == {}


@pytest.mark.parametrize("case", range(1, 81), ids=[f"S{i:02d}" for i in range(1, 81)])
def test_d149_security_matrix(case: int) -> None:
    run_case(case)
