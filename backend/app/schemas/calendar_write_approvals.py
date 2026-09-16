"""D73 API schemas for Calendar write proposal and explicit owner approval."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel

from app.contracts.google_calendar_write import (
    GoogleCalendarCreateEventRequest,
    GoogleCalendarDeleteEventRequest,
    GoogleCalendarEventDraft,
    GoogleCalendarEventPatch,
    GoogleCalendarEventTarget,
    GoogleCalendarUpdateEventRequest,
)
from app.contracts.google_calendar_write_approval import (
    CalendarWriteApprovalDecisionOutcome,
    CalendarWriteApprovalProposalOutcome,
    CalendarWritePreview,
    CalendarWriteRequest,
)


class CalendarEventDraftInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    start: datetime
    end: datetime
    description: str | None = None
    location: str | None = None
    calendar_id: Literal["primary"] = "primary"


class CalendarEventTargetInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    calendar_id: Literal["primary"] = "primary"


class CalendarEventPatchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    description: str | None = None
    location: str | None = None


class CreateCalendarWriteApprovalInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["create_event"]
    event: CalendarEventDraftInput


class UpdateCalendarWriteApprovalInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["update_event"]
    target: CalendarEventTargetInput
    changes: CalendarEventPatchInput


class DeleteCalendarWriteApprovalInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["delete_event"]
    target: CalendarEventTargetInput


CalendarWriteApprovalInput = Annotated[
    CreateCalendarWriteApprovalInput
    | UpdateCalendarWriteApprovalInput
    | DeleteCalendarWriteApprovalInput,
    Field(discriminator="operation"),
]


class CalendarWriteApprovalRequest(RootModel[CalendarWriteApprovalInput]):
    """Flat discriminated D73 request body."""


class CalendarWriteApprovalDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    write_digest: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )


class CalendarWritePreviewResponse(BaseModel):
    contract_version: str
    operation: Literal["create_event", "update_event", "delete_event"]
    calendar_id: Literal["primary"]
    event_id: str | None = None
    summary: str | None = None
    start: str | None = None
    end: str | None = None
    description: str | None = None
    location: str | None = None
    changed_fields: list[str] = Field(default_factory=list)

    @classmethod
    def from_contract(
        cls,
        preview: CalendarWritePreview,
    ) -> "CalendarWritePreviewResponse":
        return cls(
            contract_version=preview.contract_version,
            operation=preview.operation,
            calendar_id=preview.calendar_id,
            event_id=preview.event_id,
            summary=preview.summary,
            start=preview.start,
            end=preview.end,
            description=preview.description,
            location=preview.location,
            changed_fields=list(preview.changed_fields),
        )


class CalendarWriteApprovalProposalResponse(BaseModel):
    status: Literal["pending"]
    reason_code: str
    approval_id: str
    write_digest: str
    preview: CalendarWritePreviewResponse
    expires_at: datetime

    @classmethod
    def from_outcome(
        cls,
        outcome: CalendarWriteApprovalProposalOutcome,
    ) -> "CalendarWriteApprovalProposalResponse":
        proposal = outcome.proposal
        return cls(
            status=outcome.status,
            reason_code=outcome.reason_code,
            approval_id=proposal.approval_id,
            write_digest=proposal.write_digest,
            preview=CalendarWritePreviewResponse.from_contract(
                proposal.preview
            ),
            expires_at=proposal.expires_at,
        )


class CalendarWriteApprovalDecisionResponse(BaseModel):
    status: Literal["approved", "denied"]
    reason_code: str
    approval_id: str
    write_digest: str
    preview: CalendarWritePreviewResponse
    expires_at: datetime

    @classmethod
    def from_outcome(
        cls,
        outcome: CalendarWriteApprovalDecisionOutcome,
    ) -> "CalendarWriteApprovalDecisionResponse":
        return cls(
            status=outcome.decision,
            reason_code=outcome.reason_code,
            approval_id=outcome.approval_id,
            write_digest=outcome.write_digest,
            preview=CalendarWritePreviewResponse.from_contract(
                outcome.preview
            ),
            expires_at=outcome.expires_at,
        )


def to_calendar_write_request(
    payload: CalendarWriteApprovalRequest,
) -> CalendarWriteRequest:
    """Construct the authoritative D72 immutable request from transport input."""
    value = payload.root

    if isinstance(value, CreateCalendarWriteApprovalInput):
        return GoogleCalendarCreateEventRequest(
            event=GoogleCalendarEventDraft(
                summary=value.event.summary,
                start=value.event.start,
                end=value.event.end,
                description=value.event.description,
                location=value.event.location,
                calendar_id=value.event.calendar_id,
            )
        )

    if isinstance(value, UpdateCalendarWriteApprovalInput):
        return GoogleCalendarUpdateEventRequest(
            target=GoogleCalendarEventTarget(
                event_id=value.target.event_id,
                calendar_id=value.target.calendar_id,
            ),
            changes=GoogleCalendarEventPatch(
                summary=value.changes.summary,
                start=value.changes.start,
                end=value.changes.end,
                description=value.changes.description,
                location=value.changes.location,
            ),
        )

    if isinstance(value, DeleteCalendarWriteApprovalInput):
        return GoogleCalendarDeleteEventRequest(
            target=GoogleCalendarEventTarget(
                event_id=value.target.event_id,
                calendar_id=value.target.calendar_id,
            )
        )

    raise TypeError("Unsupported Calendar write approval request.")
