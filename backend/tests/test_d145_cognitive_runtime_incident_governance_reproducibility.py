from dataclasses import asdict
from pathlib import Path

import pytest

from app.contracts.cognitive_runtime_readiness import (
    CognitiveRuntimeReadinessAssessment,
)
from app.contracts.cognitive_runtime_rollout import D144_STAGE_BPS
from app.schemas.diagnostics import CognitiveRuntimeRolloutDiagnostics
from app.services.cognitive_runtime_incident_governance import (
    CognitiveRuntimeIncidentGovernanceEvaluator,
)
from app.services.cognitive_runtime_promotion_advisory import (
    CognitiveRuntimePromotionGovernanceEvaluator,
)

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "backend/app/services/cognitive_runtime_incident_governance.py"
RUNTIME = ROOT / "backend/app/services/runtime_diagnostics.py"


def assess(status="ready", stage="full"):
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
    scenarios = (
        ("disabled", "control_only"),
        ("collecting", "canary_1"),
        ("ready", "canary_5"),
        ("degraded", "canary_10"),
        ("degraded", "canary_25"),
        ("degraded", "full"),
        ("unavailable", "control_only"),
        ("unavailable", "full"),
    )

    if 1 <= case <= 12:
        status, stage = scenarios[(case - 1) % len(scenarios)]
        a = assess(status, stage)
        b = assess(status, stage)
        assert a == b
        assert asdict(a) == asdict(b)

    elif 13 <= case <= 20:
        ordered = list(scenarios)
        if case % 2 == 0:
            ordered.reverse()
        first = {item: asdict(assess(*item)) for item in ordered}
        second = {item: asdict(assess(*item)) for item in reversed(ordered)}
        assert first == second

    elif 21 <= case <= 28:
        source = SERVICE.read_text(encoding="utf-8").lower()
        forbidden = (
            "import time", "from time", "datetime", "monotonic",
            "perf_counter", "sleep(", "utcnow", "timestamp(",
        )[case - 21]
        assert forbidden not in source

    elif 29 <= case <= 34:
        source = SERVICE.read_text(encoding="utf-8").lower()
        forbidden = (
            "import random", "from random", "secrets.", "uuid4(",
            "randint(", "choice(",
        )[case - 29]
        assert forbidden not in source

    elif 35 <= case <= 40:
        evaluator_a = CognitiveRuntimeIncidentGovernanceEvaluator()
        evaluator_b = CognitiveRuntimeIncidentGovernanceEvaluator()
        checks = (
            vars(evaluator_a) == {},
            vars(evaluator_b) == {},
            type(evaluator_a) is type(evaluator_b),
            assess("ready", "full") == assess("ready", "full"),
            assess("degraded", "canary_5") == assess("degraded", "canary_5"),
            assess("unavailable", "full") == assess("unavailable", "full"),
        )
        assert checks[case - 35]

    elif 41 <= case <= 44:
        source = RUNTIME.read_text(encoding="utf-8")
        checks = (
            source.count("CognitiveRuntimeReadinessEvaluator.evaluate(") == 1,
            source.count(
                "CognitiveRuntimePromotionGovernanceEvaluator.evaluate("
            ) == 1,
            source.count(
                "CognitiveRuntimeIncidentGovernanceEvaluator.evaluate("
            ) == 1,
            "rollout=rollout_diagnostics" in source,
        )
        assert checks[case - 41]

    elif 45 <= case <= 48:
        result = assess(*scenarios[case - 45])
        other = assess(*scenarios[case - 45])
        a, b = asdict(result), asdict(other)
        checks = (
            a == b,
            tuple(a) == tuple(b),
            list(a.values()) == list(b.values()),
            repr(result) == repr(other),
        )
        assert checks[case - 45]
    else:
        raise AssertionError(case)


@pytest.mark.parametrize(
    "case", range(1, 49), ids=[f"R{i:02d}" for i in range(1, 49)]
)
def test_d145_reproducibility_matrix(case):
    run_case(case)
