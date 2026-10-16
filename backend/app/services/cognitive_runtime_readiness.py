"""D142 deterministic cognitive-runtime production-readiness advisory."""

from __future__ import annotations

from app.contracts.cognitive_runtime_assurance import (
    D141_REFERENCE_BASELINE,
    D141_SAMPLE_SCOPE,
    CognitiveRuntimeAssuranceSnapshot,
)
from app.contracts.cognitive_runtime_readiness import (
    D142_MAX_FAILED_RATE_BPS,
    D142_MAX_RESPONSE_BLOCKED_RATE_BPS,
    D142_MAX_RUNTIME_BUSY_RATE_BPS,
    D142_MAX_RUNTIME_UNAVAILABLE_RATE_BPS,
    D142_MIN_TERMINAL_SAMPLES,
    D142_RATE_SCALE_BPS,
    CognitiveRuntimeReadinessAssessment,
)


class CognitiveRuntimeReadinessEvaluator:
    """Pure, stateless D142 advisory evaluator with no runtime authority."""

    @staticmethod
    def _rate_bps(*, numerator: int, denominator: int) -> int:
        if (
            isinstance(numerator, bool)
            or type(numerator) is not int
            or numerator < 0
            or isinstance(denominator, bool)
            or type(denominator) is not int
            or denominator <= 0
            or numerator > denominator
        ):
            raise ValueError("cognitive_runtime_readiness_rate_input_invalid")
        return numerator * D142_RATE_SCALE_BPS // denominator

    @staticmethod
    def _unavailable_or_disabled(
        *,
        enabled: bool,
    ) -> CognitiveRuntimeReadinessAssessment:
        return CognitiveRuntimeReadinessAssessment(
            status=("unavailable" if enabled else "disabled")
        )

    @classmethod
    def evaluate(
        cls,
        *,
        enabled: bool,
        snapshot: object | None,
    ) -> CognitiveRuntimeReadinessAssessment:
        if type(enabled) is not bool:
            raise ValueError("cognitive_runtime_readiness_enabled_invalid")

        if not isinstance(snapshot, CognitiveRuntimeAssuranceSnapshot):
            return cls._unavailable_or_disabled(enabled=enabled)

        try:
            if snapshot.reference_baseline != D141_REFERENCE_BASELINE:
                raise ValueError(
                    "cognitive_runtime_readiness_evidence_baseline_invalid"
                )
            if snapshot.sample_scope != D141_SAMPLE_SCOPE:
                raise ValueError(
                    "cognitive_runtime_readiness_evidence_scope_invalid"
                )
            if snapshot.reset_on_restart is not True:
                raise ValueError(
                    "cognitive_runtime_readiness_evidence_reset_invalid"
                )

            terminal_samples = (
                snapshot.completed + snapshot.insufficient + snapshot.failed
            )
            if terminal_samples > snapshot.cognitive_selected:
                raise ValueError(
                    "cognitive_runtime_readiness_terminal_count_invalid"
                )

            if terminal_samples == 0:
                rates = {
                    "failed_rate_bps": None,
                    "insufficient_rate_bps": None,
                    "runtime_busy_rate_bps": None,
                    "runtime_unavailable_rate_bps": None,
                    "response_blocked_rate_bps": None,
                }
            else:
                rates = {
                    "failed_rate_bps": cls._rate_bps(
                        numerator=snapshot.failed,
                        denominator=terminal_samples,
                    ),
                    "insufficient_rate_bps": cls._rate_bps(
                        numerator=snapshot.insufficient,
                        denominator=terminal_samples,
                    ),
                    "runtime_busy_rate_bps": cls._rate_bps(
                        numerator=snapshot.runtime_busy,
                        denominator=terminal_samples,
                    ),
                    "runtime_unavailable_rate_bps": cls._rate_bps(
                        numerator=snapshot.runtime_unavailable,
                        denominator=terminal_samples,
                    ),
                    "response_blocked_rate_bps": cls._rate_bps(
                        numerator=snapshot.response_blocked,
                        denominator=terminal_samples,
                    ),
                }
        except Exception:
            return cls._unavailable_or_disabled(enabled=enabled)

        if not enabled:
            status = "disabled"
        elif terminal_samples < D142_MIN_TERMINAL_SAMPLES:
            status = "collecting"
        else:
            governed_rates = (
                (rates["failed_rate_bps"], D142_MAX_FAILED_RATE_BPS),
                (rates["runtime_busy_rate_bps"], D142_MAX_RUNTIME_BUSY_RATE_BPS),
                (
                    rates["runtime_unavailable_rate_bps"],
                    D142_MAX_RUNTIME_UNAVAILABLE_RATE_BPS,
                ),
                (
                    rates["response_blocked_rate_bps"],
                    D142_MAX_RESPONSE_BLOCKED_RATE_BPS,
                ),
            )
            degraded = any(
                rate is None or rate > threshold
                for rate, threshold in governed_rates
            )
            status = "degraded" if degraded else "ready"

        return CognitiveRuntimeReadinessAssessment(
            status=status,
            terminal_samples=terminal_samples,
            failed_rate_bps=rates["failed_rate_bps"],
            insufficient_rate_bps=rates["insufficient_rate_bps"],
            runtime_busy_rate_bps=rates["runtime_busy_rate_bps"],
            runtime_unavailable_rate_bps=rates["runtime_unavailable_rate_bps"],
            response_blocked_rate_bps=rates["response_blocked_rate_bps"],
        )


__all__ = ["CognitiveRuntimeReadinessEvaluator"]
