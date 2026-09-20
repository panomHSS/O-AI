"""D101 owner-facing exact Calendar Delete prepare schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CalendarDeletePrepareRequest(BaseModel):
    """Client supplies only conversation correlation; never an event target."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID


class CalendarDeletePrepareResponse(BaseModel):
    """Opaque owner decision correlation for one exact server-bound Delete."""

    model_config = ConfigDict(extra="forbid")

    selection_id: str
    approval_id: str
    write_digest: str
    operation: Literal["delete_event"]
    status: Literal["pending"]
    expires_at: datetime



class CalendarDeleteDecisionRequest(BaseModel):
    """Owner decision correlation; no event target is accepted from the client."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID
    write_digest: str


class CalendarDeleteDecisionResponse(BaseModel):
    """Terminal Delete decision state with no provider event identity."""

    model_config = ConfigDict(extra="forbid")

    approval_id: str
    decision: Literal["approved", "denied"]
    status: Literal["denied", "succeeded", "failed", "indeterminate"]
    reason_code: str
