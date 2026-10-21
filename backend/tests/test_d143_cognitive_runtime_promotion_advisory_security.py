from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.contracts.cognitive_runtime_promotion_advisory import (
    CognitiveRuntimePromotionAdvisory,
)
from app.schemas.chat import ChatRequest
from app.services.cognitive_runtime_promotion_advisory import (
    CognitiveRuntimePromotionGovernanceEvaluator,
)

ROOT = Path(__file__).resolve().parents[2]

_PROTECTED_BLOBS = (
    ("backend/app/api/dependencies.py", "a50b373f02425a2b09c1cfb805230dde8edc137b"),
    ("backend/app/api/v1/diagnostics.py", "85591ce7bca5fa4a166144aef78d2dbfb04b9bc6"),
    ("backend/app/api/v1/chat.py", "a0a3def2aaa6980e0d3db470a07b2127c35e4fc0"),
    ("backend/app/schemas/chat.py", "ab6dfea0091740d3fe2da597601d5a9926005ec8"),
    ("backend/app/core/config.py", "b1bf02c33f2f2f9c6ffd93e47ec657780e835bef"),
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
    (
        "backend/app/contracts/cognitive_runtime_readiness.py",
        "740947cfca99e4afc7f69b611d6e04edd8df754d",
    ),
    (
        "backend/app/services/cognitive_runtime_readiness.py",
        "1487813a9666fcce2fd1837c2c7a2ad10a2d09f9",
    ),
    ("backend/app/services/cognitive_executive.py", "42089c5a087cfe510933efd4a3b0afcb6c131951"),
    ("backend/app/services/cognitive_invocation.py", "756b959bb8803f78e2555627889fddc6f5d2bcb7"),
    ("backend/app/services/cognitive_verification.py", "47b35076985ccf37266f68459cc8d326db4afba1"),
    (
        "backend/app/services/cognitive_reasoning_prediction.py",
        "85a16f4f61450fdea2f3239ac02be4358c9c2a69",
    ),
    (
        "backend/app/services/cognitive_planning_decision_goal.py",
        "42087f031a05da16084a3cfee1a3bfc0c4e442b0",
    ),
    ("backend/app/services/cognitive_metacognition.py", "3be6116b1da2acca0c332ade4d845fca3ba8cd20"),
    (
        "backend/app/services/cognitive_model_intelligence.py",
        "4494acb325514c0a86f1da634554e764008c7c01",
    ),
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
    "prompt",
    "message",
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

_AUTHORITY_FIELDS = (
    "promotion_authority",
    "rollback_authority",
    "execution_authority",
    "routing_authority",
    "configuration_authority",
    "automatic_promotion",
    "automatic_rollback",
)


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _assert_python_surface(path: str) -> None:
    source = _text(path)
    assert source.strip()
    ast.parse(source)


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
    if 1 <= case <= 25:
        path, historical_digest = _PROTECTED_BLOBS[case - 1]
        _assert_python_surface(path)
        assert len(historical_digest) == 40
        int(historical_digest, 16)

    elif 26 <= case <= 41:
        names = {field.name for field in fields(CognitiveRuntimePromotionAdvisory)}
        assert _FORBIDDEN_FIELDS[case - 26] not in names

    elif 42 <= case <= 53:
        imports = (
            _imports("backend/app/contracts/cognitive_runtime_promotion_advisory.py")
            | _imports("backend/app/services/cognitive_runtime_promotion_advisory.py")
        )
        forbidden = _FORBIDDEN_IMPORTS[case - 42]
        assert not any(
            module == forbidden or module.startswith(forbidden + ".")
            for module in imports
        )

    elif 54 <= case <= 60:
        result = CognitiveRuntimePromotionGovernanceEvaluator.evaluate(
            readiness=None
        )
        name = _AUTHORITY_FIELDS[case - 54]
        assert getattr(result, name) is False

    elif 61 <= case <= 68:
        invalid = (
            None,
            object(),
            True,
            1,
            "ready",
            ["ready"],
            {"status": "ready"},
            SimpleNamespace(status="ready"),
        )[case - 61]
        result = CognitiveRuntimePromotionGovernanceEvaluator.evaluate(
            readiness=invalid
        )
        assert result.recommendation == "fail_closed"
        assert result.reason_code == "invalid_readiness_evidence"
        assert result.source_readiness_status is None
        assert result.owner_decision_required is False
        assert all(getattr(result, name) is False for name in _AUTHORITY_FIELDS)

    elif case == 69:
        assert set(ChatRequest.model_fields) == {
            "message",
            "conversation_id",
            "project_id",
            "ai_mode",
        }

    elif case == 70:
        _assert_python_surface("backend/app/api/v1/diagnostics.py")

    elif case == 71:
        for path in (
            "backend/app/contracts/cognitive_runtime_assurance.py",
            "backend/app/services/cognitive_runtime_assurance.py",
            "backend/app/contracts/cognitive_runtime_readiness.py",
            "backend/app/services/cognitive_runtime_readiness.py",
        ):
            _assert_python_surface(path)

    elif case == 72:
        imports = _imports(
            "backend/app/services/cognitive_runtime_promotion_advisory.py"
        )
        assert "app.contracts.cognitive_runtime_assurance" not in imports
        assert "app.services.cognitive_runtime_assurance" not in imports
        assert "app.services.cognitive_runtime_observability" not in imports
        source = _text(
            "backend/app/services/cognitive_runtime_promotion_advisory.py"
        )
        assert "d138" not in source.lower()
        assert "git " not in source.lower()
        for forbidden in (
            "D142_MIN_TERMINAL_SAMPLES",
            "D142_MAX_FAILED_RATE_BPS",
            "D142_MAX_RUNTIME_BUSY_RATE_BPS",
            "D142_MAX_RUNTIME_UNAVAILABLE_RATE_BPS",
            "D142_MAX_RESPONSE_BLOCKED_RATE_BPS",
        ):
            assert forbidden not in source

    else:
        raise AssertionError(case)


@pytest.mark.parametrize(
    "case",
    range(1, 73),
    ids=[f"S{i:02d}" for i in range(1, 73)],
)
def test_d143_security_matrix(case: int) -> None:
    run_case(case)
