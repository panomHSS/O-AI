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
from app.contracts.tool_module import (
    TOOL_MODULE_ADAPTER_CONTRACT_VERSION,
    ModuleAdapter,
    ToolAdapter,
)

__all__ = [
    "AI_ADAPTER_CONTRACT_VERSION",
    "TOOL_MODULE_ADAPTER_CONTRACT_VERSION",
    "AIAdapter",
    "AIRequest",
    "AIResult",
    "CommandRequest",
    "ExecutionPlan",
    "ExecutionStep",
    "ModuleAdapter",
    "Response",
    "Result",
    "ResultStatus",
    "ToolAdapter",
]
