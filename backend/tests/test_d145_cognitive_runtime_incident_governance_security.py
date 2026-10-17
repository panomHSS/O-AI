import ast
from dataclasses import fields
from pathlib import Path

import pytest

from app.contracts.cognitive_runtime_incident_governance import (
    CognitiveRuntimeIncidentAssessment,
)
from app.contracts.cognitive_runtime_readiness import (
    CognitiveRuntimeReadinessAssessment,
)
from app.contracts.cognitive_runtime_rollout import D144_STAGE_BPS
from app.schemas.chat import ChatRequest
from app.schemas.diagnostics import CognitiveRuntimeRolloutDiagnostics
from app.services.cognitive_runtime_incident_governance import (
    CognitiveRuntimeIncidentGovernanceEvaluator,
)
from app.services.cognitive_runtime_promotion_advisory import (
    CognitiveRuntimePromotionGovernanceEvaluator,
)

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "backend/app/services/cognitive_runtime_incident_governance.py"
CONTRACT = ROOT / "backend/app/contracts/cognitive_runtime_incident_governance.py"


def text(path):
    return (ROOT / path).read_text(encoding="utf-8")


def imports(path):
    tree = ast.parse(text(path))
    result = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module)
    return result


def assess(status="degraded", stage="full"):
    readiness = CognitiveRuntimeReadinessAssessment(status=status)
    advisory = CognitiveRuntimePromotionGovernanceEvaluator.evaluate(
        readiness=readiness
    )
    rollout = CognitiveRuntimeRolloutDiagnostics(
        stage=stage,
        rollout_bps=D144_STAGE_BPS[stage],
        source_promotion_recommendation=advisory.recommendation,
        source_promotion_reason_code=advisory.reason_code,
    )
    return CognitiveRuntimeIncidentGovernanceEvaluator.evaluate(
        readiness=readiness, advisory=advisory, rollout=rollout
    )


def run_case(case):
    if 1 <= case <= 10:
        forbidden = (
            "incident_status", "incident_severity", "incident_action",
            "rollout_stage", "rollout_bps", "rollback", "runtime_disable",
            "containment", "promotion", "incident_authority",
        )[case - 1]
        assert forbidden not in ChatRequest.model_fields

    elif 11 <= case <= 20:
        names = {field.name for field in fields(CognitiveRuntimeIncidentAssessment)}
        forbidden = (
            "message", "prompt", "response", "context", "memory",
            "knowledge", "secret", "conversation_id", "project_id",
            "workspace_id",
        )[case - 11]
        assert forbidden not in names

    elif 21 <= case <= 30:
        source = SERVICE.read_text(encoding="utf-8").lower()
        forbidden = (
            "ai_router", "ai_runtime", "model_id", "provider", "profile_id",
            "execution_planner", "execution_guard", "command_orchestrator",
            "cognitive_executive", "tool_runtime",
        )[case - 21]
        assert forbidden not in source

    elif 31 <= case <= 38:
        result = assess()
        names = (
            "rollback_authority",
            "rollout_stage_authority",
            "runtime_disable_authority",
            "promotion_authority",
            "routing_authority",
            "execution_authority",
            "configuration_authority",
        )
        if case <= 37:
            assert getattr(result, names[case - 31]) is False
        else:
            assert all(getattr(result, name) is False for name in names)

    elif 39 <= case <= 44:
        imported = imports(
            "backend/app/services/cognitive_runtime_incident_governance.py"
        )
        forbidden = (
            "sqlalchemy", "requests", "httpx", "subprocess", "pathlib", "os",
        )[case - 39]
        assert not any(
            module == forbidden or module.startswith(forbidden + ".")
            for module in imported
        )

    elif 45 <= case <= 50:
        source = SERVICE.read_text(encoding="utf-8").lower()
        forbidden = (
            "thread", "scheduler", "background", "asyncio", "create_task",
            "timer(",
        )[case - 45]
        assert forbidden not in source

    elif 51 <= case <= 56:
        source = SERVICE.read_text(encoding="utf-8")
        forbidden = (
            "D142_MAX_FAILED_RATE_BPS",
            "D142_MAX_RUNTIME_BUSY_RATE_BPS",
            "D142_MAX_RUNTIME_UNAVAILABLE_RATE_BPS",
            "D142_MAX_RESPONSE_BLOCKED_RATE_BPS",
            "D142_MIN_TERMINAL_SAMPLES",
            "_rate_bps",
        )[case - 51]
        assert forbidden not in source

    elif 57 <= case <= 60:
        source = SERVICE.read_text(encoding="utf-8")
        checks = (
            "CognitiveRuntimeRolloutSelector" not in source,
            "cognitive_runtime_rollout.py" not in source,
            "automatic_stage_increase" in source,
            "rollout_stage_authority" in CONTRACT.read_text(encoding="utf-8"),
        )
        assert checks[case - 57]

    elif 61 <= case <= 64:
        combined = (
            SERVICE.read_text(encoding="utf-8")
            + CONTRACT.read_text(encoding="utf-8")
        ).lower()
        forbidden = ("d138", "git ", "subprocess", "benchmark")[case - 61]
        assert forbidden not in combined
    else:
        raise AssertionError(case)


@pytest.mark.parametrize(
    "case", range(1, 65), ids=[f"S{i:02d}" for i in range(1, 65)]
)
def test_d145_security_matrix(case):
    run_case(case)
