"""D79 automation proposal/approval lifecycle contracts v1."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from app.contracts.automation import (
    AUTOMATION_CONTRACT_VERSION,
    AUTOMATION_KIND_LOCAL_REMINDER,
)


AUTOMATION_APPROVAL_TTL = timedelta(minutes=10)
AUTOMATION_ACTIVE_MAX = 32
AUTOMATION_PENDING_MAX = 64
AUTOMATION_ONCE_MIN_LEAD = timedelta(minutes=1)
AUTOMATION_ONCE_MAX_HORIZON = timedelta(days=365)
AUTOMATION_LIST_MAX = 100


@dataclass(frozen=True, slots=True)
class AutomationPreview:
    contract_version: str
    kind: Literal["local_reminder"]
    message: str
    schedule_kind: Literal["once", "daily"]
    run_at: str | None
    daily_local_time: str | None
    timezone: str
    max_runs: int

    def __post_init__(self) -> None:
        if self.contract_version != AUTOMATION_CONTRACT_VERSION:
            raise ValueError("automation_preview_contract_invalid")
        if self.kind != AUTOMATION_KIND_LOCAL_REMINDER:
            raise ValueError("automation_preview_kind_invalid")
        if self.schedule_kind == "once":
            if self.run_at is None or self.daily_local_time is not None:
                raise ValueError("automation_preview_schedule_invalid")
        elif self.schedule_kind == "daily":
            if self.run_at is not None or self.daily_local_time is None:
                raise ValueError("automation_preview_schedule_invalid")
        else:
            raise ValueError("automation_preview_schedule_invalid")


@dataclass(frozen=True, slots=True)
class AutomationProposalOutcome:
    status: Literal["pending"]
    reason_code: str
    automation_id: str
    definition_digest: str
    preview: AutomationPreview
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class AutomationDecisionOutcome:
    status: Literal["approved", "denied"]
    reason_code: str
    automation_id: str
    definition_digest: str
    preview: AutomationPreview
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class AutomationCancelOutcome:
    status: Literal["cancelled"]
    reason_code: str
    automation_id: str
    definition_digest: str


@dataclass(frozen=True, slots=True)
class AutomationDefinitionView:
    automation_id: str
    definition_digest: str
    status: Literal[
        "pending",
        "approved",
        "denied",
        "cancelled",
        "completed",
    ]
    preview: AutomationPreview
    expires_at: datetime
    approved_at: datetime | None
    terminal_at: datetime | None


@dataclass(frozen=True, slots=True)
class AutomationRunView:
    automation_id: str
    run_id: str
    scheduled_for: datetime
    status: Literal[
        "claimed",
        "delivered",
        "missed",
        "indeterminate",
    ]
    message: str


__all__ = [
    "AUTOMATION_ACTIVE_MAX",
    "AUTOMATION_APPROVAL_TTL",
    "AUTOMATION_LIST_MAX",
    "AUTOMATION_ONCE_MAX_HORIZON",
    "AUTOMATION_ONCE_MIN_LEAD",
    "AUTOMATION_PENDING_MAX",
    "AutomationCancelOutcome",
    "AutomationDecisionOutcome",
    "AutomationDefinitionView",
    "AutomationPreview",
    "AutomationProposalOutcome",
    "AutomationRunView",
]
