"""D101 owner-facing exact Calendar Update prepare schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


class CalendarUpdateChanges(BaseModel):
    """Bounded owner-reviewed changes; never contains an event target."""

    model_config = ConfigDict(extra="forbid")

    summary: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    description: str | None = None
    location: str | None = None

    @model_validator(mode="after")
    def validate_change_shape(self) -> "CalendarUpdateChanges":
        supplied = self.model_fields_set
        allowed = {"summary", "start", "end", "description", "location"}
        changed = supplied & allowed
        if not changed:
            raise ValueError("calendar_update_patch_empty")

        if any(getattr(self, field) is None for field in changed):
            raise ValueError("calendar_update_change_null_not_supported")

        if ("start" in changed) != ("end" in changed):
            raise ValueError("calendar_write_time_pair_required")

        return self


class CalendarUpdatePrepareRequest(BaseModel):
    """Client supplies conversation correlation plus bounded changes only."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID
    changes: CalendarUpdateChanges


class CalendarUpdatePrepareResponse(BaseModel):
    """Opaque owner-decision correlation plus sanitized changed-field preview."""

    model_config = ConfigDict(extra="forbid")

    selection_id: str
    approval_id: str
    write_digest: str
    operation: Literal["update_event"]
    status: Literal["pending"]
    expires_at: datetime
    changed_fields: tuple[
        Literal["summary", "start", "end", "description", "location"],
        ...,
    ]
    changes: CalendarUpdateChanges



class CalendarUpdateDecisionRequest(BaseModel):
    """Owner decision correlation only; no target or replacement patch."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID
    write_digest: str


class CalendarUpdateDecisionResponse(BaseModel):
    """Terminal Update decision state with no provider event identity."""

    model_config = ConfigDict(extra="forbid")

    approval_id: str
    decision: Literal["approved", "denied"]
    status: Literal["denied", "succeeded", "failed", "indeterminate"]
    reason_code: str
