"""D141 immutable aggregate cognitive-runtime assurance contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

D141_REFERENCE_BASELINE = "71e6af0bd01ab06a3fd22ee6f472db3a206b059a"
D141_SAMPLE_SCOPE = "process_lifetime"
D141_COUNTER_MAX = 9_223_372_036_854_775_807

CognitiveRuntimeAssuranceStatus: TypeAlias = Literal[
    "disabled", "idle", "observing", "unavailable"
]


def _counter(value: object, *, code: str) -> int:
    if (
        isinstance(value, bool)
        or type(value) is not int
        or not 0 <= value <= D141_COUNTER_MAX
    ):
        raise ValueError(code)
    return value


@dataclass(frozen=True, slots=True)
class CognitiveRuntimeAssuranceSnapshot:
    """Aggregate process-lifetime evidence only; never request/user content."""

    cognitive_selected: int = 0
    legacy_selected: int = 0
    completed: int = 0
    insufficient: int = 0
    failed: int = 0
    runtime_busy: int = 0
    runtime_unavailable: int = 0
    response_blocked: int = 0
    reference_baseline: str = D141_REFERENCE_BASELINE
    sample_scope: Literal["process_lifetime"] = D141_SAMPLE_SCOPE
    reset_on_restart: Literal[True] = True

    def __post_init__(self) -> None:
        for name in (
            "cognitive_selected",
            "legacy_selected",
            "completed",
            "insufficient",
            "failed",
            "runtime_busy",
            "runtime_unavailable",
            "response_blocked",
        ):
            _counter(
                getattr(self, name),
                code=f"cognitive_runtime_assurance_{name}_invalid",
            )
        if self.completed + self.insufficient + self.failed > self.cognitive_selected:
            raise ValueError("cognitive_runtime_assurance_terminal_count_invalid")
        if self.reference_baseline != D141_REFERENCE_BASELINE:
            raise ValueError("cognitive_runtime_assurance_baseline_invalid")
        if self.sample_scope != D141_SAMPLE_SCOPE:
            raise ValueError("cognitive_runtime_assurance_scope_invalid")
        if self.reset_on_restart is not True:
            raise ValueError("cognitive_runtime_assurance_reset_invalid")


__all__ = [
    "D141_COUNTER_MAX",
    "D141_REFERENCE_BASELINE",
    "D141_SAMPLE_SCOPE",
    "CognitiveRuntimeAssuranceSnapshot",
    "CognitiveRuntimeAssuranceStatus",
]
