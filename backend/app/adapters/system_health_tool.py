"""D42 bounded read-only O-AI runtime health tool."""

from __future__ import annotations

from pathlib import Path

from app.contracts.command import CommandRequest, ExecutionPlan, Result
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION


class SystemHealthToolAdapter:
    """Check local runtime structure without probing external services."""

    adapter_id = "tool.system.health"
    tool_name = "system.health"
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = Path(workspace_root)

    def execute(self, request: CommandRequest, plan: ExecutionPlan) -> Result:
        error = self._validate(request, plan)
        if error is not None:
            return Result(request_id=request.request_id, status="failed", error=error)
        try:
            root_ok = self._workspace_root.is_dir()
            runtime_ok = (self._workspace_root / "backend" / "app").is_dir()
            healthy = root_ok and runtime_ok
            output = {
                "status": "healthy" if healthy else "degraded",
                "checks": {
                    "runtime": "ok" if runtime_ok else "unavailable",
                    "project_root": "ok" if root_ok else "unavailable",
                },
            }
        except Exception:
            return Result(
                request_id=request.request_id,
                status="failed",
                error="system_health_failed",
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
        if step.sequence != 1 or step.operation != "check":
            return "unsupported_operation"
        if set(step.parameters):
            return "invalid_operation_shape"
        return None
