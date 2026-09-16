from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict


ExecutionAuditDiagnosticStatus: TypeAlias = Literal["ok", "unavailable"]
GoogleCalendarDiagnosticStatus: TypeAlias = Literal[
    "disabled",
    "not_configured",
    "disconnected",
    "connected",
    "reauthorization_required",
    "unavailable",
]


class ExecutionAuditDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ExecutionAuditDiagnosticStatus


class GoogleCalendarDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: GoogleCalendarDiagnosticStatus
    connector_enabled: bool
    configuration_present: bool


class RuntimeDiagnosticsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["1"] = "1"
    service: str
    environment: str
    database_revision: str
    execution_audit: ExecutionAuditDiagnostics
    google_calendar: GoogleCalendarDiagnostics
