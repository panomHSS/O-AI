"""D141 process-local aggregate cognitive-runtime assurance."""

from __future__ import annotations

from threading import Lock

from app.contracts.cognitive_brain import CognitiveFailureCode, CognitiveTurnState
from app.contracts.cognitive_runtime_adoption import CognitiveRuntimeObservation
from app.contracts.cognitive_runtime_assurance import (
    D141_COUNTER_MAX,
    CognitiveRuntimeAssuranceSnapshot,
)

_FAILURE_BUCKET = {
    CognitiveFailureCode.TURN_IN_PROGRESS: "runtime_busy",
    CognitiveFailureCode.TURN_DEADLINE_EXCEEDED: "runtime_unavailable",
    CognitiveFailureCode.CONTEXT_UNSTABLE: "runtime_unavailable",
    CognitiveFailureCode.CRITIC_UNAVAILABLE: "runtime_unavailable",
    CognitiveFailureCode.STALE_LATE_RESULT: "runtime_unavailable",
    CognitiveFailureCode.INVALID_COGNITION: "response_blocked",
    CognitiveFailureCode.CONTRACT_VIOLATION: "response_blocked",
}


class CognitiveRuntimeAssurance:
    """Thread-safe aggregate evidence with no routing or execution authority."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._counters = {
            "cognitive_selected": 0,
            "legacy_selected": 0,
            "completed": 0,
            "insufficient": 0,
            "failed": 0,
            "runtime_busy": 0,
            "runtime_unavailable": 0,
            "response_blocked": 0,
        }

    @staticmethod
    def _saturating_increment(value: int) -> int:
        if type(value) is not int or not 0 <= value <= D141_COUNTER_MAX:
            raise ValueError("cognitive_runtime_assurance_counter_invalid")
        return min(D141_COUNTER_MAX, value + 1)

    def record_selection(self, event: CognitiveRuntimeObservation) -> None:
        if not isinstance(event, CognitiveRuntimeObservation):
            raise ValueError("cognitive_runtime_assurance_event_invalid")
        if event.terminal_state is not None:
            raise ValueError("cognitive_runtime_assurance_selection_invalid")
        key = {
            "cognitive": "cognitive_selected",
            "legacy": "legacy_selected",
        }.get(event.selected_lane)
        if key is None:
            raise ValueError("cognitive_runtime_assurance_lane_invalid")
        with self._lock:
            self._counters[key] = self._saturating_increment(self._counters[key])

    def record_outcome(self, event: CognitiveRuntimeObservation) -> None:
        if not isinstance(event, CognitiveRuntimeObservation):
            raise ValueError("cognitive_runtime_assurance_event_invalid")
        if event.selected_lane != "cognitive" or event.terminal_state is None:
            raise ValueError("cognitive_runtime_assurance_outcome_invalid")

        failure_bucket: str | None = None
        if event.terminal_state is CognitiveTurnState.COMPLETED:
            terminal_key = "completed"
            if event.failure_code is not None:
                raise ValueError("cognitive_runtime_assurance_outcome_invalid")
        elif event.terminal_state is CognitiveTurnState.INSUFFICIENT:
            terminal_key = "insufficient"
            if event.failure_code is not CognitiveFailureCode.INSUFFICIENT_EVIDENCE:
                raise ValueError("cognitive_runtime_assurance_outcome_invalid")
        elif event.terminal_state is CognitiveTurnState.FAILED:
            terminal_key = "failed"
            failure_bucket = _FAILURE_BUCKET.get(event.failure_code)
            if failure_bucket is None:
                raise ValueError("cognitive_runtime_assurance_failure_invalid")
        else:
            raise ValueError("cognitive_runtime_assurance_outcome_invalid")

        with self._lock:
            terminal_total = (
                self._counters["completed"]
                + self._counters["insufficient"]
                + self._counters["failed"]
            )
            if terminal_total >= self._counters["cognitive_selected"]:
                raise ValueError("cognitive_runtime_assurance_selection_required")
            self._counters[terminal_key] = self._saturating_increment(
                self._counters[terminal_key]
            )
            if failure_bucket is not None:
                self._counters[failure_bucket] = self._saturating_increment(
                    self._counters[failure_bucket]
                )

    def snapshot(self) -> CognitiveRuntimeAssuranceSnapshot:
        with self._lock:
            values = dict(self._counters)
        return CognitiveRuntimeAssuranceSnapshot(**values)


__all__ = ["CognitiveRuntimeAssurance"]
