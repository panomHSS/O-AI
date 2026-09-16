"""D74 transport schemas for local Calendar create execution."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from app.contracts.google_calendar_create_execution import CalendarCreateExecutionOutcome
from app.contracts.google_calendar_update_delete_execution import (
    CalendarDeleteExecutionOutcome,
    CalendarUpdateExecutionOutcome,
)


class CalendarCreateExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approval_id: str = Field(min_length=1, max_length=128)
    write_digest: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")


class CalendarCreateExecutionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approval_id: str
    write_digest: str
    status: Literal["succeeded", "failed", "indeterminate"]
    reason_code: str
    event_id: str | None = None

    @classmethod
    def from_outcome(cls, outcome: CalendarCreateExecutionOutcome) -> "CalendarCreateExecutionResponse":
        return cls(
            approval_id=outcome.approval_id,
            write_digest=outcome.write_digest,
            status=outcome.status,
            reason_code=outcome.reason_code,
            event_id=outcome.event_id,
        )


class CalendarUpdateExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approval_id: str = Field(min_length=1, max_length=128)
    write_digest: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )


class CalendarUpdateExecutionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approval_id: str
    write_digest: str
    status: Literal["succeeded", "failed", "indeterminate"]
    reason_code: str
    event_id: str | None = None

    @classmethod
    def from_outcome(
        cls,
        outcome: CalendarUpdateExecutionOutcome,
    ) -> "CalendarUpdateExecutionResponse":
        return cls(
            approval_id=outcome.approval_id,
            write_digest=outcome.write_digest,
            status=outcome.status,
            reason_code=outcome.reason_code,
            event_id=outcome.event_id,
        )


class CalendarDeleteExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approval_id: str = Field(min_length=1, max_length=128)
    write_digest: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )


class CalendarDeleteExecutionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approval_id: str
    write_digest: str
    status: Literal["succeeded", "failed", "indeterminate"]
    reason_code: str

    @classmethod
    def from_outcome(
        cls,
        outcome: CalendarDeleteExecutionOutcome,
    ) -> "CalendarDeleteExecutionResponse":
        return cls(
            approval_id=outcome.approval_id,
            write_digest=outcome.write_digest,
            status=outcome.status,
            reason_code=outcome.reason_code,
        )
