"""D142 immutable cognitive-runtime production-readiness advisory contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.cognitive_runtime_assurance import D141_COUNTER_MAX

D142_REFERENCE_BASELINE = "6f8e803da9e77d43e1eeb06a8ae3d5e69fb80299"
D142_SAMPLE_SCOPE = "process_lifetime"
D142_RATE_SCALE_BPS = 10_000

D142_MIN_TERMINAL_SAMPLES = 100
D142_MAX_FAILED_RATE_BPS = 100
D142_MAX_RUNTIME_BUSY_RATE_BPS = 100
D142_MAX_RUNTIME_UNAVAILABLE_RATE_BPS = 50
D142_MAX_RESPONSE_BLOCKED_RATE_BPS = 100

CognitiveRuntimeReadinessStatus: TypeAlias = Literal[
    "disabled",
    "collecting",
    "ready",
    "degraded",
    "unavailable",
]


def _bounded_int(
    value: object,
    *,
    minimum: int,
    maximum: int,
    code: str,
) -> int:
    if isinstance(value, bool) or type(value) is not int:
        raise ValueError(code)
    if not minimum <= value <= maximum:
        raise ValueError(code)
    return value


@dataclass(frozen=True, slots=True)
class CognitiveRuntimeReadinessAssessment:
    """Read-only process-lifetime readiness evidence; never control authority."""

    status: CognitiveRuntimeReadinessStatus
    reference_baseline: str = D142_REFERENCE_BASELINE
    sample_scope: Literal["process_lifetime"] = D142_SAMPLE_SCOPE
    reset_on_restart: Literal[True] = True

    terminal_samples: int | None = None
    failed_rate_bps: int | None = None
    insufficient_rate_bps: int | None = None
    runtime_busy_rate_bps: int | None = None
    runtime_unavailable_rate_bps: int | None = None
    response_blocked_rate_bps: int | None = None

    minimum_terminal_samples: int = D142_MIN_TERMINAL_SAMPLES
    max_failed_rate_bps: int = D142_MAX_FAILED_RATE_BPS
    max_runtime_busy_rate_bps: int = D142_MAX_RUNTIME_BUSY_RATE_BPS
    max_runtime_unavailable_rate_bps: int = D142_MAX_RUNTIME_UNAVAILABLE_RATE_BPS
    max_response_blocked_rate_bps: int = D142_MAX_RESPONSE_BLOCKED_RATE_BPS

    execution_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    promotion_authority: Literal[False] = False
    rollback_authority: Literal[False] = False
    automatic_promotion: Literal[False] = False
    automatic_rollback: Literal[False] = False

    def __post_init__(self) -> None:
        if self.status not in {
            "disabled",
            "collecting",
            "ready",
            "degraded",
            "unavailable",
        }:
            raise ValueError("cognitive_runtime_readiness_status_invalid")
        if self.reference_baseline != D142_REFERENCE_BASELINE:
            raise ValueError("cognitive_runtime_readiness_baseline_invalid")
        if self.sample_scope != D142_SAMPLE_SCOPE:
            raise ValueError("cognitive_runtime_readiness_scope_invalid")
        if self.reset_on_restart is not True:
            raise ValueError("cognitive_runtime_readiness_reset_invalid")

        if self.terminal_samples is not None:
            _bounded_int(
                self.terminal_samples,
                minimum=0,
                maximum=D141_COUNTER_MAX,
                code="cognitive_runtime_readiness_terminal_samples_invalid",
            )
        for name in (
            "failed_rate_bps",
            "insufficient_rate_bps",
            "runtime_busy_rate_bps",
            "runtime_unavailable_rate_bps",
            "response_blocked_rate_bps",
        ):
            value = getattr(self, name)
            if value is not None:
                _bounded_int(
                    value,
                    minimum=0,
                    maximum=D142_RATE_SCALE_BPS,
                    code=f"cognitive_runtime_readiness_{name}_invalid",
                )

        expected_policy = {
            "minimum_terminal_samples": D142_MIN_TERMINAL_SAMPLES,
            "max_failed_rate_bps": D142_MAX_FAILED_RATE_BPS,
            "max_runtime_busy_rate_bps": D142_MAX_RUNTIME_BUSY_RATE_BPS,
            "max_runtime_unavailable_rate_bps": D142_MAX_RUNTIME_UNAVAILABLE_RATE_BPS,
            "max_response_blocked_rate_bps": D142_MAX_RESPONSE_BLOCKED_RATE_BPS,
        }
        for name, expected in expected_policy.items():
            if getattr(self, name) != expected:
                raise ValueError(f"cognitive_runtime_readiness_{name}_invalid")

        for name in (
            "execution_authority",
            "routing_authority",
            "promotion_authority",
            "rollback_authority",
            "automatic_promotion",
            "automatic_rollback",
        ):
            if getattr(self, name) is not False:
                raise ValueError(f"cognitive_runtime_readiness_{name}_invalid")

        if self.status == "unavailable":
            evidence = (
                self.terminal_samples,
                self.failed_rate_bps,
                self.insufficient_rate_bps,
                self.runtime_busy_rate_bps,
                self.runtime_unavailable_rate_bps,
                self.response_blocked_rate_bps,
            )
            if any(item is not None for item in evidence):
                raise ValueError("cognitive_runtime_readiness_unavailable_evidence_invalid")


__all__ = [
    "D142_MAX_FAILED_RATE_BPS",
    "D142_MAX_RESPONSE_BLOCKED_RATE_BPS",
    "D142_MAX_RUNTIME_BUSY_RATE_BPS",
    "D142_MAX_RUNTIME_UNAVAILABLE_RATE_BPS",
    "D142_MIN_TERMINAL_SAMPLES",
    "D142_RATE_SCALE_BPS",
    "D142_REFERENCE_BASELINE",
    "D142_SAMPLE_SCOPE",
    "CognitiveRuntimeReadinessAssessment",
    "CognitiveRuntimeReadinessStatus",
]
