from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, StrictBool

from app.contracts.runtime_capability import RuntimeCapabilityConnectionStatus


ExecutionAuditDiagnosticStatus: TypeAlias = Literal["ok", "unavailable"]
GoogleCalendarDiagnosticStatus: TypeAlias = RuntimeCapabilityConnectionStatus
GmailDiagnosticStatus: TypeAlias = RuntimeCapabilityConnectionStatus


class ExecutionAuditDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ExecutionAuditDiagnosticStatus


class RuntimeCapabilityDiagnostics(BaseModel):
    """D81 status-query capability; never an execution grant."""

    model_config = ConfigDict(extra="forbid")

    implemented: Literal[True] = True
    status_chat_routable: StrictBool = False
    execution_authority: Literal[False] = False


class GoogleCalendarDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # D70 compatibility fields.
    status: GoogleCalendarDiagnosticStatus
    connector_enabled: bool
    configuration_present: bool

    # D81 additive truth fields.
    read_implemented: Literal[True] = True
    read_chat_routable: StrictBool = False
    write_backend_implemented: Literal[True] = True
    write_chat_routable: StrictBool = False
    execution_authority: Literal[False] = False


class GmailDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: GmailDiagnosticStatus
    connector_enabled: bool
    configuration_present: bool
    read_implemented: Literal[True] = True
    read_chat_routable: StrictBool = False
    write_implemented: StrictBool = True
    send_enabled: StrictBool = False
    send_configuration_present: StrictBool = False
    send_connected: StrictBool = False
    write_chat_routable: Literal[False] = False
    execution_authority: Literal[False] = False


class CrossConnectorAIDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: StrictBool
    implemented: Literal[True] = True
    chat_routable: StrictBool
    execution_authority: Literal[False] = False


class AutomationDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: StrictBool
    local_reminder_implemented: Literal[True] = True
    local_reminder_delivery_ui_implemented: Literal[True] = True
    local_reminder_chat_routable: Literal[False] = False
    connector_actions_implemented: Literal[False] = False
    ai_actions_implemented: Literal[False] = False
    execution_authority: Literal[False] = False


class RuntimeDiagnosticsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Keep D70 contract version stable: D81 is additive.
    contract_version: Literal["1"] = "1"
    service: str
    environment: str
    database_revision: str
    execution_audit: ExecutionAuditDiagnostics
    runtime: RuntimeCapabilityDiagnostics
    google_calendar: GoogleCalendarDiagnostics
    gmail: GmailDiagnostics
    cross_connector_ai: CrossConnectorAIDiagnostics
    automation: AutomationDiagnostics
