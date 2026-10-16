from __future__ import annotations

import ast
import hashlib
from dataclasses import fields
from pathlib import Path

import pytest

from app.contracts.cognitive_runtime_assurance import (
    CognitiveRuntimeAssuranceSnapshot,
)
from app.contracts.cognitive_runtime_readiness import (
    D142_REFERENCE_BASELINE,
    CognitiveRuntimeReadinessAssessment,
)
from app.schemas.chat import ChatRequest
from app.schemas.diagnostics import CognitiveRuntimeReadinessDiagnostics
from app.services.cognitive_runtime_readiness import (
    CognitiveRuntimeReadinessEvaluator,
)

ROOT = Path(__file__).resolve().parents[2]

_PROTECTED_BLOBS = (
    ("backend/app/api/v1/chat.py", "a0a3def2aaa6980e0d3db470a07b2127c35e4fc0"),
    ("backend/app/schemas/chat.py", "ab6dfea0091740d3fe2da597601d5a9926005ec8"),
    ("backend/app/core/config.py", "b1bf02c33f2f2f9c6ffd93e47ec657780e835bef"),
    ("backend/app/services/cognitive_executive.py", "42089c5a087cfe510933efd4a3b0afcb6c131951"),
    ("backend/app/services/cognitive_invocation.py", "756b959bb8803f78e2555627889fddc6f5d2bcb7"),
    ("backend/app/services/cognitive_verification.py", "47b35076985ccf37266f68459cc8d326db4afba1"),
    ("backend/app/services/cognitive_reasoning_prediction.py", "85a16f4f61450fdea2f3239ac02be4358c9c2a69"),
    ("backend/app/services/cognitive_planning_decision_goal.py", "42087f031a05da16084a3cfee1a3bfc0c4e442b0"),
    ("backend/app/services/cognitive_metacognition.py", "3be6116b1da2acca0c332ade4d845fca3ba8cd20"),
    ("backend/app/services/cognitive_model_intelligence.py", "4494acb325514c0a86f1da634554e764008c7c01"),
    ("backend/app/services/cognitive_experience.py", "686a406701041d41f001450d6d6ae869157c5f57"),
    ("backend/app/services/ai_router.py", "95e1b0b21efe274db9054334197242f9d265aa9c"),
    ("backend/app/services/ai_runtime.py", "32e281cd357ed523467e34e0e2f806eb61e34943"),
    ("backend/app/services/execution_planner.py", "90a39a297a5062be31cea94db5c578085dd64bdd"),
    ("backend/app/services/execution_guard.py", "eb278c26e5b268404e9552bb4e1096ccc03b4f44"),
    ("backend/benchmarks/d139_registry.py", "0841f2ac35308200bcd63a305ca42467f1f38915"),
    ("backend/benchmarks/d139_comparator.py", "2cf0104d1a10e3cc08a0b9a83510c0a136bfa7f6"),
    ("backend/benchmarks/d138_runner.py", "65140410b6c356d80312ee00d64b747af42ee480"),
)

_FORBIDDEN_FIELDS = (
    "user_id",
    "workspace_id",
    "conversation_id",
    "project_id",
    "request_id",
    "message",
    "prompt",
    "response",
    "draft",
    "chain_of_thought",
    "context",
    "memory",
    "knowledge",
    "model_id",
    "provider_id",
    "secret",
)

_FORBIDDEN_IMPORTS = (
    "subprocess",
    "requests",
    "httpx",
    "urllib",
    "socket",
    "sqlalchemy",
    "pathlib",
    "os",
    "app.services.ai_runtime",
    "app.services.ai_router",
    "app.services.execution_planner",
    "app.services.execution_guard",
)


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _git_blob_sha(path: str) -> str:
    data = _text(path).encode("utf-8")
    payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    return hashlib.sha1(payload).hexdigest()


def _imports(path: str) -> set[str]:
    tree = ast.parse(_text(path))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module)
    return result


def _snap(
    *,
    completed: int = 0,
    insufficient: int = 0,
    failed: int = 0,
    runtime_busy: int = 0,
    cognitive_selected: int | None = None,
) -> CognitiveRuntimeAssuranceSnapshot:
    terminal = completed + insufficient + failed
    return CognitiveRuntimeAssuranceSnapshot(
        cognitive_selected=(
            terminal if cognitive_selected is None else cognitive_selected
        ),
        completed=completed,
        insufficient=insufficient,
        failed=failed,
        runtime_busy=runtime_busy,
    )


def run_case(case: int) -> None:
    if 1 <= case <= 18:
        path, expected = _PROTECTED_BLOBS[case - 1]
        assert _git_blob_sha(path) == expected

    elif 19 <= case <= 34:
        names = {field.name for field in fields(CognitiveRuntimeReadinessAssessment)}
        assert _FORBIDDEN_FIELDS[case - 19] not in names

    elif 35 <= case <= 46:
        imports = (
            _imports("backend/app/contracts/cognitive_runtime_readiness.py")
            | _imports("backend/app/services/cognitive_runtime_readiness.py")
        )
        forbidden = _FORBIDDEN_IMPORTS[case - 35]
        assert not any(
            module == forbidden or module.startswith(forbidden + ".")
            for module in imports
        )

    elif 47 <= case <= 56:
        assessment = CognitiveRuntimeReadinessEvaluator.evaluate(
            enabled=True,
            snapshot=_snap(completed=100),
        )
        if 47 <= case <= 52:
            name = (
                "execution_authority",
                "routing_authority",
                "promotion_authority",
                "rollback_authority",
                "automatic_promotion",
                "automatic_rollback",
            )[case - 47]
            assert getattr(assessment, name) is False
        elif case == 53:
            model = CognitiveRuntimeReadinessDiagnostics(status="collecting")
            assert model.execution_authority is False
            assert model.routing_authority is False
        elif case == 54:
            assert vars(CognitiveRuntimeReadinessEvaluator()) == {}
        elif case == 55:
            before = _snap(completed=100)
            saved = repr(before)
            CognitiveRuntimeReadinessEvaluator.evaluate(
                enabled=True,
                snapshot=before,
            )
            assert repr(before) == saved
        else:
            assert assessment.reference_baseline == D142_REFERENCE_BASELINE

    elif 57 <= case <= 64:
        if case == 57:
            result = CognitiveRuntimeReadinessEvaluator.evaluate(
                enabled=True,
                snapshot=None,
            )
            assert result.status == "unavailable"
        elif case == 58:
            result = CognitiveRuntimeReadinessEvaluator.evaluate(
                enabled=True,
                snapshot=object(),
            )
            assert result.status == "unavailable"
        elif case == 59:
            result = CognitiveRuntimeReadinessEvaluator.evaluate(
                enabled=False,
                snapshot=None,
            )
            assert result.status == "disabled"
        elif case == 60:
            result = CognitiveRuntimeReadinessEvaluator.evaluate(
                enabled=True,
                snapshot=_snap(completed=1, runtime_busy=2, cognitive_selected=2),
            )
            assert result.status == "unavailable"
        elif case == 61:
            result = CognitiveRuntimeReadinessEvaluator.evaluate(
                enabled=False,
                snapshot=_snap(completed=1, runtime_busy=2, cognitive_selected=2),
            )
            assert result.status == "disabled"
            assert result.terminal_samples is None
        elif case == 62:
            result = CognitiveRuntimeReadinessEvaluator.evaluate(
                enabled=True,
                snapshot=_snap(),
            )
            assert result.status == "collecting"
        elif case == 63:
            result = CognitiveRuntimeReadinessEvaluator.evaluate(
                enabled=True,
                snapshot=_snap(completed=99),
            )
            assert result.status == "collecting"
        else:
            result = CognitiveRuntimeReadinessEvaluator.evaluate(
                enabled=True,
                snapshot=_snap(completed=100),
            )
            assert result.status == "ready"

    elif case == 65:
        assert set(ChatRequest.model_fields) == {
            "message",
            "conversation_id",
            "project_id",
            "ai_mode",
        }
    elif case == 66:
        assert _git_blob_sha("backend/app/api/v1/chat.py") == (
            "a0a3def2aaa6980e0d3db470a07b2127c35e4fc0"
        )
    elif case == 67:
        assert _git_blob_sha("backend/app/schemas/chat.py") == (
            "ab6dfea0091740d3fe2da597601d5a9926005ec8"
        )
    elif case == 68:
        assert _git_blob_sha("backend/app/core/config.py") == (
            "b1bf02c33f2f2f9c6ffd93e47ec657780e835bef"
        )
    elif case == 69:
        assert _git_blob_sha("backend/app/api/dependencies.py") == (
            "a50b373f02425a2b09c1cfb805230dde8edc137b"
        )
        assert "cognitive_runtime_readiness" not in _text(
            "backend/app/api/dependencies.py"
        )
    elif case == 70:
        assert _git_blob_sha("backend/app/api/v1/diagnostics.py") == (
            "85591ce7bca5fa4a166144aef78d2dbfb04b9bc6"
        )
    elif case == 71:
        for path, expected in (
            (
                "backend/app/contracts/cognitive_runtime_assurance.py",
                "eb6bbf8d79b41a53b9a2b233b0b9e32838ebba94",
            ),
            (
                "backend/app/services/cognitive_runtime_assurance.py",
                "993505dc3fa60f399d4561a03397424eb2ab7645",
            ),
            (
                "backend/app/services/cognitive_runtime_observability.py",
                "691ec252f04edf5415241b868e16fc13e2223f51",
            ),
        ):
            assert _git_blob_sha(path) == expected
    elif case == 72:
        assert _git_blob_sha("backend/benchmarks/d138_runner.py") == (
            "65140410b6c356d80312ee00d64b747af42ee480"
        )
        for path in (
            "backend/tests/test_d142_cognitive_runtime_readiness.py",
            "backend/tests/test_d142_cognitive_runtime_readiness_reproducibility.py",
            "backend/tests/test_d142_cognitive_runtime_readiness_security.py",
        ):
            imports = _imports(path)
            assert "subprocess" not in imports
            assert not any(
                module == "git" or module.startswith("git.")
                for module in imports
            )
    else:
        raise AssertionError(case)


@pytest.mark.parametrize(
    "case",
    range(1, 73),
    ids=[f"S{i:02d}" for i in range(1, 73)],
)
def test_d142_security_matrix(case: int) -> None:
    run_case(case)
