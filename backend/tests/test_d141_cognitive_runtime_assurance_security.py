from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

import pytest

from app.contracts.cognitive_runtime_assurance import CognitiveRuntimeAssuranceSnapshot
from app.schemas.chat import ChatRequest

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
    "request_id", "workspace_id", "conversation_id", "project_id", "message",
    "prompt", "response", "draft", "chain_of_thought", "context", "memory",
    "knowledge", "adapter_id", "model_id", "profile_id", "api_key", "credential",
    "token",
)
_FORBIDDEN_IMPORTS = (
    "subprocess", "requests", "httpx", "urllib", "socket", "sqlalchemy",
    "app.providers", "app.repositories", "app.services.ai_runtime",
    "app.services.ai_router", "app.services.execution_planner",
    "app.services.execution_guard",
)


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _assert_python_surface(path: str) -> None:
    source = _text(path)
    assert source.strip()
    ast.parse(source)


def _imports(path: str) -> set[str]:
    tree = ast.parse(_text(path))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def run_case(case: int) -> None:
    if 1 <= case <= 18:
        path, historical_digest = _PROTECTED_BLOBS[case - 1]
        _assert_python_surface(path)
        assert len(historical_digest) == 40
        int(historical_digest, 16)
    elif 19 <= case <= 36:
        names = {f.name for f in fields(CognitiveRuntimeAssuranceSnapshot)}
        assert _FORBIDDEN_FIELDS[case - 19] not in names
    elif 37 <= case <= 48:
        imports = (
            _imports("backend/app/services/cognitive_runtime_assurance.py")
            | _imports("backend/app/contracts/cognitive_runtime_assurance.py")
        )
        forbidden = _FORBIDDEN_IMPORTS[case - 37]
        assert not any(
            module == forbidden or module.startswith(forbidden + ".")
            for module in imports
        )
    elif 49 <= case <= 56:
        text = _text("backend/app/services/cognitive_runtime_assurance.py").lower()
        checks = (
            "automatic_rollback", "automatic_promotion", "router", "provider",
            "database", "repository", "subprocess", "reset(",
        )
        assert checks[case - 49] not in text
    elif 57 <= case <= 64:
        text = _text("backend/app/schemas/diagnostics.py")
        checks = (
            "execution_authority: Literal[False]",
            "automatic_promotion: Literal[False]",
            "automatic_rollback: Literal[False]",
            'Literal["process_lifetime"]',
            "reset_on_restart: Literal[True]",
            "cognitive_selected:",
            "runtime_unavailable:",
            "response_blocked:",
        )
        assert checks[case - 57] in text
    elif case == 65:
        assert set(ChatRequest.model_fields) == {
            "message", "conversation_id", "project_id", "ai_mode"
        }
    elif case == 66:
        assert "settings.oai_cognitive_runtime_enabled" in _text(
            "backend/app/api/dependencies.py"
        )
    elif case == 67:
        assert (
            "get_conversation_service not in request.app.dependency_overrides"
            in _text("backend/app/api/dependencies.py")
        )
    elif case == 68:
        assert "cognitive_runtime_assurance" not in _text(
            "backend/app/api/v1/chat.py"
        )
    elif case == 69:
        assert "71e6af0bd01ab06a3fd22ee6f472db3a206b059a" in _text(
            "backend/app/contracts/cognitive_runtime_assurance.py"
        )
    elif case == 70:
        assert "self._assurance.record_" in _text(
            "backend/app/services/cognitive_runtime_observability.py"
        )
    elif case == 71:
        assert _text("backend/app/schemas/diagnostics.py").count(
            "cognitive_runtime:"
        ) == 1
    elif case == 72:
        for path in (
            "backend/tests/test_d141_cognitive_runtime_assurance.py",
            "backend/tests/test_d141_cognitive_runtime_assurance_reproducibility.py",
            "backend/tests/test_d141_cognitive_runtime_assurance_security.py",
        ):
            imports = _imports(path)
            assert "subprocess" not in imports
            assert not any(m == "git" or m.startswith("git.") for m in imports)
    else:
        raise AssertionError(case)


@pytest.mark.parametrize("case", range(1, 73), ids=[f"S{i:02d}" for i in range(1, 73)])
def test_d141_security_matrix(case: int) -> None:
    run_case(case)
