"""Strict D79 owner API schemas for local reminder automations."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.automation import (
    DailyAutomationSchedule,
    OnceAutomationSchedule,
)
from app.contracts.automation_delivery import (
    AutomationDeliveryView,
    AutomationSettingsView,
)
from app.contracts.automation_approval import (
    AutomationCancelOutcome,
    AutomationDecisionOutcome,
    AutomationDefinitionView,
    AutomationPreview,
    AutomationProposalOutcome,
    AutomationRunView,
)


class OnceAutomationScheduleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["once"]
    run_at: datetime


class DailyAutomationScheduleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["daily"]
    local_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")


AutomationScheduleInput = Annotated[
    OnceAutomationScheduleInput | DailyAutomationScheduleInput,
    Field(discriminator="kind"),
]


class AutomationProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["local_reminder"]
    message: str = Field(min_length=1, max_length=1000)
    schedule: AutomationScheduleInput
    max_runs: int = Field(ge=1, le=31)


class AutomationDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    definition_digest: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )


class AutomationPreviewResponse(BaseModel):
    contract_version: str
    kind: Literal["local_reminder"]
    message: str
    schedule_kind: Literal["once", "daily"]
    run_at: str | None
    daily_local_time: str | None
    timezone: str
    max_runs: int

    @classmethod
    def from_contract(
        cls,
        value: AutomationPreview,
    ) -> "AutomationPreviewResponse":
        return cls(
            contract_version=value.contract_version,
            kind=value.kind,
            message=value.message,
            schedule_kind=value.schedule_kind,
            run_at=value.run_at,
            daily_local_time=value.daily_local_time,
            timezone=value.timezone,
            max_runs=value.max_runs,
        )


class AutomationProposalResponse(BaseModel):
    status: Literal["pending"]
    reason_code: str
    automation_id: str
    definition_digest: str
    preview: AutomationPreviewResponse
    expires_at: datetime

    @classmethod
    def from_outcome(
        cls,
        value: AutomationProposalOutcome,
    ) -> "AutomationProposalResponse":
        return cls(
            status=value.status,
            reason_code=value.reason_code,
            automation_id=value.automation_id,
            definition_digest=value.definition_digest,
            preview=AutomationPreviewResponse.from_contract(
                value.preview
            ),
            expires_at=value.expires_at,
        )


class AutomationDecisionResponse(BaseModel):
    status: Literal["approved", "denied"]
    reason_code: str
    automation_id: str
    definition_digest: str
    preview: AutomationPreviewResponse
    expires_at: datetime

    @classmethod
    def from_outcome(
        cls,
        value: AutomationDecisionOutcome,
    ) -> "AutomationDecisionResponse":
        return cls(
            status=value.status,
            reason_code=value.reason_code,
            automation_id=value.automation_id,
            definition_digest=value.definition_digest,
            preview=AutomationPreviewResponse.from_contract(
                value.preview
            ),
            expires_at=value.expires_at,
        )


class AutomationCancelResponse(BaseModel):
    status: Literal["cancelled"]
    reason_code: str
    automation_id: str
    definition_digest: str

    @classmethod
    def from_outcome(
        cls,
        value: AutomationCancelOutcome,
    ) -> "AutomationCancelResponse":
        return cls(
            status=value.status,
            reason_code=value.reason_code,
            automation_id=value.automation_id,
            definition_digest=value.definition_digest,
        )


class AutomationDefinitionResponse(BaseModel):
    automation_id: str
    definition_digest: str
    status: Literal[
        "pending",
        "approved",
        "denied",
        "cancelled",
        "completed",
    ]
    preview: AutomationPreviewResponse
    expires_at: datetime
    approved_at: datetime | None
    terminal_at: datetime | None

    @classmethod
    def from_view(
        cls,
        value: AutomationDefinitionView,
    ) -> "AutomationDefinitionResponse":
        return cls(
            automation_id=value.automation_id,
            definition_digest=value.definition_digest,
            status=value.status,
            preview=AutomationPreviewResponse.from_contract(
                value.preview
            ),
            expires_at=value.expires_at,
            approved_at=value.approved_at,
            terminal_at=value.terminal_at,
        )


class AutomationListResponse(BaseModel):
    items: list[AutomationDefinitionResponse]


class AutomationRunResponse(BaseModel):
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

    @classmethod
    def from_view(
        cls,
        value: AutomationRunView,
    ) -> "AutomationRunResponse":
        return cls(
            automation_id=value.automation_id,
            run_id=value.run_id,
            scheduled_for=value.scheduled_for,
            status=value.status,
            message=value.message,
        )


class AutomationRunListResponse(BaseModel):
    items: list[AutomationRunResponse]


class AutomationSettingsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    owner_timezone: str

    @classmethod
    def from_view(
        cls,
        value: AutomationSettingsView,
    ) -> "AutomationSettingsResponse":
        return cls(
            enabled=value.enabled,
            owner_timezone=value.owner_timezone,
        )


class AutomationDeliveryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    automation_id: str
    run_id: str
    scheduled_for: datetime
    status: Literal["delivered", "missed", "indeterminate"]
    message: str

    @classmethod
    def from_view(
        cls,
        value: AutomationDeliveryView,
    ) -> "AutomationDeliveryResponse":
        return cls(
            automation_id=value.automation_id,
            run_id=value.run_id,
            scheduled_for=value.scheduled_for,
            status=value.status,
            message=value.message,
        )


class AutomationDeliveryListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AutomationDeliveryResponse]


def to_schedule(
    value: AutomationScheduleInput,
) -> OnceAutomationSchedule | DailyAutomationSchedule:
    if isinstance(value, OnceAutomationScheduleInput):
        return OnceAutomationSchedule(run_at=value.run_at)
    if isinstance(value, DailyAutomationScheduleInput):
        return DailyAutomationSchedule(local_time=value.local_time)
    raise TypeError("unsupported automation schedule input")
