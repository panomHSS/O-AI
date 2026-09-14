"""D42 bounded read-only system information tool."""

from __future__ import annotations

import os
import platform

from app.contracts.command import CommandRequest, ExecutionPlan, Result
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION


class SystemInfoToolAdapter:
    """Return a small allowlisted set of non-secret runtime facts."""

    adapter_id = "tool.system.info"
    tool_name = "system.info"
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION

    def execute(self, request: CommandRequest, plan: ExecutionPlan) -> Result:
        error = self._validate(request, plan)
        if error is not None:
            return Result(request_id=request.request_id, status="failed", error=error)
        try:
            output = {
                "os": platform.system(),
                "os_release": platform.release(),
                "architecture": platform.machine(),
                "python_version": platform.python_version(),
                "cpu_count": os.cpu_count(),
            }
        except Exception:
            return Result(
                request_id=request.request_id,
                status="failed",
                error="system_info_failed",
            )
        return Result(
            request_id=request.request_id,
            status="succeeded",
            output=output,
        )

    def _validate(
        self,
        request: CommandRequest,
        plan: ExecutionPlan,
    ) -> str | None:
        if request.request_id != plan.request_id:
            return "request_plan_mismatch"
        if plan.adapter_id != self.adapter_id:
            return "adapter_mismatch"
        if plan.owner_approval_required:
            return "owner_approval_required"
        if len(plan.steps) != 1:
            return "invalid_plan_shape"
        step = plan.steps[0]
        if step.sequence != 1 or step.operation != "get_info":
            return "unsupported_operation"
        if set(step.parameters):
            return "invalid_operation_shape"
        return None
