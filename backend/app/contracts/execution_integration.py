"""D40 immutable integration outcome contract for the frozen v1 action lane."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.command import Result
from app.contracts.execution_authorization import ExecutionAuthorization
from app.contracts.execution_planning import (
    ExecutionPlanningOutcome,
    ExecutionTargetKind,
)


ExecutionIntegrationStatus: TypeAlias = Literal[
    "completed",
    "blocked",
    "rejected",
    "unavailable",
]

_INTEGRATION_STATUSES = frozenset(
    {"completed", "blocked", "rejected", "unavailable"}
)
_EXECUTION_TARGETS = frozenset({"tool", "module"})


@dataclass(frozen=True, slots=True)
class ExecutionIntegrationOutcome:
    """One D40 Tool/Module coordination outcome without presentation concerns."""

    request_id: str
    status: ExecutionIntegrationStatus
    target_kind: ExecutionTargetKind | None
    planning: ExecutionPlanningOutcome
    authorization: ExecutionAuthorization | None
    result: Result | None
    reason_code: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.request_id, str)
            or not self.request_id
            or self.request_id != self.request_id.strip()
        ):
            raise ValueError("request_id must be a non-empty trimmed string.")
        if self.status not in _INTEGRATION_STATUSES:
            raise ValueError(
                f"Unsupported integration status: {self.status!r}."
            )
        if (
            not isinstance(self.reason_code, str)
            or not self.reason_code
            or self.reason_code != self.reason_code.strip()
        ):
            raise ValueError(
                "reason_code must be a non-empty trimmed string."
            )
        if not isinstance(self.planning, ExecutionPlanningOutcome):
            raise TypeError(
                "planning must be an ExecutionPlanningOutcome."
            )
        if self.planning.request_id != self.request_id:
            raise ValueError(
                "planning request_id must match integration request_id."
            )
        if (
            self.authorization is not None
            and not isinstance(
                self.authorization,
                ExecutionAuthorization,
            )
        ):
            raise TypeError(
                "authorization must be an ExecutionAuthorization or None."
            )
        if (
            self.authorization is not None
            and self.authorization.request_id != self.request_id
        ):
            raise ValueError(
                "authorization request_id must match integration request_id."
            )
        if self.result is not None and not isinstance(self.result, Result):
            raise TypeError("result must be a Result or None.")
        if (
            self.result is not None
            and self.result.request_id != self.request_id
        ):
            raise ValueError(
                "result request_id must match integration request_id."
            )

        if self.planning.status == "planned":
            if self.target_kind != self.planning.target_kind:
                raise ValueError(
                    "integration target_kind must match planned target."
                )
        elif self.target_kind is not None:
            raise ValueError(
                "non-planned integration outcomes must not set target_kind."
            )

        if self.status == "completed":
            if self.target_kind not in _EXECUTION_TARGETS:
                raise ValueError(
                    "completed integration requires Tool or Module target."
                )
            if (
                self.authorization is None
                or self.authorization.status != "authorized"
            ):
                raise ValueError(
                    "completed integration requires authorization."
                )
            if (
                self.authorization.target_kind
                != self.target_kind
            ):
                raise ValueError(
                    "authorization target must match integration target."
                )
            if self.result is None:
                raise ValueError(
                    "completed integration requires a Result."
                )
        else:
            if self.result is not None:
                raise ValueError(
                    "non-completed integration must not carry a Result."
                )

        if self.status == "unavailable":
            if self.authorization is not None:
                raise ValueError(
                    "unavailable integration must not carry authorization."
                )
        if self.status == "blocked":
            if (
                self.authorization is None
                or self.authorization.status != "blocked"
            ):
                raise ValueError(
                    "blocked integration requires blocked authorization."
                )
