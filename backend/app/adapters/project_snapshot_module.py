"""D43 bounded read-only Project snapshot module."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.contracts.command import CommandRequest, ExecutionPlan, Result
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION
from app.services.project_context import (
    ProjectContext,
    ProjectContextUnavailableError,
)


class ProjectSnapshotResolver(Protocol):
    """Narrow read-only dependency used by the Project snapshot module."""

    def resolve(self, project_id: str | None) -> ProjectContext | None: ...


class ProjectSnapshotModuleAdapter:
    """Expose one bounded current Project projection through ModuleRuntime."""

    adapter_id = "module.project.snapshot"
    module_name = "project.snapshot"
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION

    def __init__(self, resolver: ProjectSnapshotResolver) -> None:
        self._resolver = resolver

    def execute(self, request: CommandRequest, plan: ExecutionPlan) -> Result:
        error, project_id = self._validate(request, plan)
        if error is not None:
            return Result(request_id=request.request_id, status="failed", error=error)

        assert project_id is not None
        try:
            context = self._resolver.resolve(project_id)
        except ProjectContextUnavailableError:
            return Result(
                request_id=request.request_id,
                status="failed",
                error="project_snapshot_unavailable",
            )
        except Exception:
            return Result(
                request_id=request.request_id,
                status="failed",
                error="project_snapshot_unavailable",
            )

        if context is None:
            return Result(
                request_id=request.request_id,
                status="failed",
                error="project_snapshot_unavailable",
            )

        return Result(
            request_id=request.request_id,
            status="succeeded",
            output={
                "project_id": project_id,
                "title": context.title,
                "objective": context.objective,
                "status": context.status,
                "current_summary": context.current_summary,
                "next_action": context.next_action,
                "current_revision": context.current_revision,
            },
        )

    def _validate(
        self,
        request: CommandRequest,
        plan: ExecutionPlan,
    ) -> tuple[str | None, str | None]:
        if request.request_id != plan.request_id:
            return "request_plan_mismatch", None
        if plan.adapter_id != self.adapter_id:
            return "adapter_mismatch", None
        if plan.owner_approval_required:
            return "owner_approval_required", None
        if len(plan.steps) != 1:
            return "invalid_plan_shape", None
        step = plan.steps[0]
        if step.sequence != 1 or step.operation != "get_snapshot":
            return "unsupported_operation", None
        if set(step.parameters) != {"project_id"}:
            return "invalid_operation_shape", None

        project_id = step.parameters["project_id"]
        if not isinstance(project_id, str) or not project_id:
            return "invalid_operation_shape", None
        try:
            parsed = UUID(project_id)
        except (ValueError, AttributeError):
            return "invalid_operation_shape", None
        if str(parsed) != project_id:
            return "invalid_operation_shape", None
        return None, project_id
