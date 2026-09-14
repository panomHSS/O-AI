"""Immutable D35 contracts for deterministic execution planning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.command import ExecutionPlan


PlanningStatus: TypeAlias = Literal["planned", "rejected", "unavailable"]
ExecutionTargetKind: TypeAlias = Literal["ai", "tool", "module"]

_PLANNING_STATUSES = frozenset({"planned", "rejected", "unavailable"})
_TARGET_KINDS = frozenset({"ai", "tool", "module"})


@dataclass(frozen=True, slots=True)
class ExecutionPlanningOutcome:
    """A proposed planning result that never authorizes or performs execution."""

    request_id: str
    status: PlanningStatus
    target_kind: ExecutionTargetKind | None
    plan: ExecutionPlan | None
    reason_code: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.request_id, str)
            or not self.request_id
            or self.request_id != self.request_id.strip()
        ):
            raise ValueError("request_id must be a non-empty trimmed string.")

        if self.status not in _PLANNING_STATUSES:
            raise ValueError(f"Unsupported planning status: {self.status!r}.")

        if (
            not isinstance(self.reason_code, str)
            or not self.reason_code
            or self.reason_code != self.reason_code.strip()
        ):
            raise ValueError("reason_code must be a non-empty trimmed string.")

        if self.status == "planned":
            if self.plan is None:
                raise ValueError("planned outcomes require an ExecutionPlan.")
            if self.target_kind not in _TARGET_KINDS:
                raise ValueError("planned outcomes require a valid target_kind.")
            if self.plan.request_id != self.request_id:
                raise ValueError(
                    "planned outcome request_id must match ExecutionPlan.request_id."
                )
        else:
            if self.plan is not None:
                raise ValueError("non-planned outcomes must not include a plan.")
            if self.target_kind is not None:
                raise ValueError(
                    "non-planned outcomes must not include a target_kind."
                )
