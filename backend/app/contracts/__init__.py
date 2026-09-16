"""Stable, provider-neutral contracts for replaceable O-AI adapters."""

from app.contracts.ai import (
    AI_ADAPTER_CONTRACT_VERSION,
    AIAdapter,
    AIRequest,
    AIResult,
)
from app.contracts.command import (
    CommandRequest,
    ExecutionPlan,
    ExecutionStep,
    Response,
    Result,
    ResultStatus,
)
from app.contracts.google_calendar_write import (
    GOOGLE_CALENDAR_CREATE_EVENT_OPERATION,
    GOOGLE_CALENDAR_DELETE_EVENT_OPERATION,
    GOOGLE_CALENDAR_UPDATE_EVENT_OPERATION,
    GOOGLE_CALENDAR_WRITE_CONTRACT_VERSION,
    GoogleCalendarCreateEventRequest,
    GoogleCalendarDeleteEventRequest,
    GoogleCalendarEventDraft,
    GoogleCalendarEventPatch,
    GoogleCalendarEventTarget,
    GoogleCalendarUpdateEventRequest,
)
from app.contracts.tool_module import (
    TOOL_MODULE_ADAPTER_CONTRACT_VERSION,
    ModuleAdapter,
    ToolAdapter,
)
from app.contracts.tool_module_route import ToolModuleRouteDecision, ToolModuleRouteStatus
from app.contracts.response_composition import NormalizedError, SafeErrorCode

__all__ = [
    "AI_ADAPTER_CONTRACT_VERSION",
    "TOOL_MODULE_ADAPTER_CONTRACT_VERSION",
    "GOOGLE_CALENDAR_WRITE_CONTRACT_VERSION",
    "GOOGLE_CALENDAR_CREATE_EVENT_OPERATION",
    "GOOGLE_CALENDAR_UPDATE_EVENT_OPERATION",
    "GOOGLE_CALENDAR_DELETE_EVENT_OPERATION",
    "AIAdapter",
    "AIRequest",
    "AIResult",
    "CommandRequest",
    "ExecutionPlan",
    "ExecutionStep",
    "GoogleCalendarCreateEventRequest",
    "GoogleCalendarDeleteEventRequest",
    "GoogleCalendarEventDraft",
    "GoogleCalendarEventPatch",
    "GoogleCalendarEventTarget",
    "GoogleCalendarUpdateEventRequest",
    "ModuleAdapter",
    "Response",
    "Result",
    "ResultStatus",
    "ToolAdapter",
    "ToolModuleRouteDecision",
    "ToolModuleRouteStatus",
    "NormalizedError",
    "SafeErrorCode",
]
