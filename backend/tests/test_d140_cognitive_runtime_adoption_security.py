from __future__ import annotations

import ast
import hashlib
import inspect
from dataclasses import fields
from pathlib import Path

import pytest

from app.contracts.cognitive_runtime_adoption import CognitiveRuntimeObservation
from app.schemas.chat import ChatRequest
from app.services.cognitive_runtime_observability import CognitiveRuntimeObserver


ROOT = Path(__file__).resolve().parents[2]

_PROTECTED_BLOBS = (
    ("backend/app/api/v1/chat.py", "a0a3def2aaa6980e0d3db470a07b2127c35e4fc0"),
    ("backend/app/schemas/chat.py", "ab6dfea0091740d3fe2da597601d5a9926005ec8"),
    (
        "backend/app/services/cognitive_executive.py",
        "42089c5a087cfe510933efd4a3b0afcb6c131951",
    ),
    (
        "backend/app/services/cognitive_invocation.py",
        "756b959bb8803f78e2555627889fddc6f5d2bcb7",
    ),
    (
        "backend/app/services/cognitive_verification.py",
        "47b35076985ccf37266f68459cc8d326db4afba1",
    ),
    (
        "backend/app/services/cognitive_reasoning_prediction.py",
        "85a16f4f61450fdea2f3239ac02be4358c9c2a69",
    ),
    (
        "backend/app/services/cognitive_planning_decision_goal.py",
        "42087f031a05da16084a3cfee1a3bfc0c4e442b0",
    ),
    (
        "backend/app/services/cognitive_metacognition.py",
        "3be6116b1da2acca0c332ade4d845fca3ba8cd20",
    ),
    (
        "backend/app/services/cognitive_model_intelligence.py",
        "4494acb325514c0a86f1da634554e764008c7c01",
    ),
    (
        "backend/app/services/cognitive_experience.py",
        "686a406701041d41f001450d6d6ae869157c5f57",
    ),
    ("backend/app/services/ai_router.py", "95e1b0b21efe274db9054334197242f9d265aa9c"),
    ("backend/app/services/ai_runtime.py", "32e281cd357ed523467e34e0e2f806eb61e34943"),
    (
        "backend/app/services/execution_planner.py",
        "90a39a297a5062be31cea94db5c578085dd64bdd",
    ),
    (
        "backend/app/services/execution_guard.py",
        "eb278c26e5b268404e9552bb4e1096ccc03b4f44",
    ),
    (
        "backend/benchmarks/d139_registry.py",
        "0841f2ac35308200bcd63a305ca42467f1f38915",
    ),
    (
        "backend/benchmarks/d139_comparator.py",
        "2cf0104d1a10e3cc08a0b9a83510c0a136bfa7f6",
    ),
    (
        "backend/benchmarks/d138_contracts.py",
        "0b4f0c3a18f337c6930c6ca7b4464b821bdf4bd2",
    ),
    (
        "backend/benchmarks/d138_runner.py",
        "65140410b6c356d80312ee00d64b747af42ee480",
    ),
)

_FORBIDDEN_FIELDS = (
    "message",
    "prompt",
    "system_prompt",
    "model_prompt",
    "draft",
    "draft_text",
    "response",
    "response_text",
    "provider_response",
    "chain_of_thought",
    "context_content",
    "memory_content",
)

_FORBIDDEN_OBSERVER_IMPORTS = {
    "subprocess",
    "requests",
    "httpx",
    "urllib",
    "socket",
    "sqlalchemy",
    "app.providers",
    "app.repositories",
    "app.services.ai_runtime",
    "app.services.execution_planner",
    "app.services.execution_guard",
}


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _git_blob_sha(path: str) -> str:
    data = _text(path).encode("utf-8")
    payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    return hashlib.sha1(payload).hexdigest()


def _imports(path: str) -> set[str]:
    tree = ast.parse(_text(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def run_case(case: int) -> None:
    if 1 <= case <= 18:
        path, expected = _PROTECTED_BLOBS[case - 1]
        assert _git_blob_sha(path) == expected
    elif 19 <= case <= 22:
        names = set(ChatRequest.model_fields)
        forbidden = (
            "task_kind",
            "cognitive_runtime",
            "use_cognitive",
            "enable_brain",
        )[case - 19]
        assert forbidden not in names
    elif 23 <= case <= 26:
        names = set(ChatRequest.model_fields)
        forbidden = (
            "adapter_id",
            "model_id",
            "profile_id",
            "route",
        )[case - 23]
        assert forbidden not in names
    elif case == 27:
        assert set(ChatRequest.model_fields) == {
            "message",
            "conversation_id",
            "project_id",
            "ai_mode",
        }
    elif case == 28:
        assert "backend/app/api/v1/chat.py" not in {
            "backend/app/contracts/cognitive_runtime_adoption.py",
            "backend/app/services/cognitive_runtime_observability.py",
        }
    elif case == 29:
        text = _text("backend/app/api/dependencies.py")
        assert "_d136_live_runtime_enabled" not in text
    elif case == 30:
        text = _text("backend/app/api/dependencies.py")
        assert "settings.oai_cognitive_runtime_enabled" in text
        assert (
            "get_conversation_service not in request.app.dependency_overrides"
            in text
        )
    elif 31 <= case <= 42:
        names = {field.name for field in fields(CognitiveRuntimeObservation)}
        assert _FORBIDDEN_FIELDS[case - 31] not in names
    elif case == 43:
        names = {field.name for field in fields(CognitiveRuntimeObservation)}
        assert "api_key" not in names
    elif case == 44:
        names = {field.name for field in fields(CognitiveRuntimeObservation)}
        assert "credential" not in names
    elif case == 45:
        names = {field.name for field in fields(CognitiveRuntimeObservation)}
        assert "token" not in names
    elif case == 46:
        names = {field.name for field in fields(CognitiveRuntimeObservation)}
        assert "secret" not in names
    elif 47 <= case <= 53:
        imports = _imports(
            "backend/app/services/cognitive_runtime_observability.py"
        )
        forbidden = tuple(sorted(_FORBIDDEN_OBSERVER_IMPORTS))[case - 47]
        assert not any(
            module == forbidden or module.startswith(forbidden + ".")
            for module in imports
        )
    elif case == 54:
        source = inspect.getsource(CognitiveRuntimeObserver)
        assert "message:" not in source
        assert "prompt:" not in source
        assert "response_text" not in source
    elif case == 55:
        source = _text("backend/app/services/command_orchestrator.py").lower()
        assert "fallback" not in source
    elif case == 56:
        source = _text("backend/app/services/command_orchestrator.py").lower()
        assert "for attempt" not in source
    elif case == 57:
        source = _text("backend/app/services/command_orchestrator.py").lower()
        assert "while " not in source
    elif case == 58:
        source = _text("backend/app/services/command_orchestrator.py")
        assert "except CognitiveExecutiveFailure as error:" in source
    elif case == 59:
        source = _text("backend/app/services/command_orchestrator.py")
        cognitive = source.index("if self._cognitive_executive is not None:")
        legacy = source.index('selected_lane="legacy"', cognitive)
        block = source[cognitive:legacy]
        assert "return self._normalized(" in block
    elif case == 60:
        source = _text("backend/app/services/command_orchestrator.py")
        cognitive = source.index("if self._cognitive_executive is not None:")
        legacy = source.index('selected_lane="legacy"', cognitive)
        block = source[cognitive:legacy]
        assert "self._planner.plan(" not in block
    elif case == 61:
        source = _text("backend/app/services/command_orchestrator.py")
        assert "task_kind = AITaskKind.GENERAL_CHAT" in source
    elif case == 62:
        source = _text("backend/app/services/command_orchestrator.py")
        assert "class _GeneralChatExecutionPlanner:" in source
        assert source.count("task_kind=AITaskKind.GENERAL_CHAT") >= 2
        assert "self._planner.plan(command)" in source
        assert "self._planner.plan(command, ai_mode=ai_mode)" in source
    elif case == 63:
        source = _text("backend/app/services/orchestration_error_normalizer.py")
        assert "str(error)" not in source
    elif case == 64:
        source = _text("backend/app/services/orchestration_error_normalizer.py")
        assert "repr(error)" not in source
    elif case == 65:
        source = _text("backend/app/services/cognitive_runtime_observability.py")
        assert "except Exception:" in source
    elif case == 66:
        source = _text("backend/app/services/command_orchestrator.py")
        assert source.count("except Exception:") >= 2
    elif case == 67:
        imports = _imports("backend/app/contracts/cognitive_runtime_adoption.py")
        assert not any(module.startswith("app.providers") for module in imports)
    elif case == 68:
        imports = _imports("backend/app/contracts/cognitive_runtime_adoption.py")
        assert not any(module.startswith("app.repositories") for module in imports)
    elif case == 69:
        source = _text("backend/app/contracts/cognitive_runtime_adoption.py")
        assert "owner_approval" not in source
    elif case == 70:
        source = _text("backend/app/services/cognitive_runtime_observability.py")
        assert "subprocess" not in source
    elif case == 71:
        source = _text("backend/app/services/cognitive_runtime_observability.py")
        assert "background" not in source.lower()
    elif case == 72:
        for path in (
            "backend/tests/test_d140_cognitive_runtime_adoption.py",
            "backend/tests/test_d140_cognitive_runtime_adoption_reproducibility.py",
            "backend/tests/test_d140_cognitive_runtime_adoption_security.py",
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
def test_d140_security_matrix(case: int) -> None:
    run_case(case)
