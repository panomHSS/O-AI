"""D43 bounded read-only workspace overview module."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from app.contracts.command import CommandRequest, ExecutionPlan, Result
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION


class WorkspaceBoundaryError(ValueError):
    """Stable workspace-boundary failure without path disclosure."""


class WorkspaceOverviewModuleAdapter:
    """Inspect a fixed O-AI workspace shape without arbitrary path access."""

    adapter_id = "module.workspace.overview"
    module_name = "workspace.overview"
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION

    _AREA_PATHS = {
        "backend": "backend/app",
        "frontend": "frontend/app",
        "docs": "docs",
        "scripts": "scripts",
    }
    _MARKER_PATHS = {
        "backend_app": "backend/app",
        "backend_requirements": "backend/requirements.txt",
        "frontend_app": "frontend/app",
        "frontend_package": "frontend/package.json",
        "architecture": "docs/ARCHITECTURE.md",
    }

    def __init__(
        self,
        workspace_root: Path,
        *,
        resolver: Callable[[Path], Path] | None = None,
    ) -> None:
        root = Path(workspace_root).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("D43 workspace root must be an existing directory.")
        self._root = root
        self._resolver = resolver or (lambda path: path.resolve(strict=False))

    def execute(self, request: CommandRequest, plan: ExecutionPlan) -> Result:
        error = self._validate(request, plan)
        if error is not None:
            return Result(request_id=request.request_id, status="failed", error=error)

        try:
            areas = {
                name: self._presence(relative_path)
                for name, relative_path in self._AREA_PATHS.items()
            }
            markers = {
                name: self._presence(relative_path)
                for name, relative_path in self._MARKER_PATHS.items()
            }
        except WorkspaceBoundaryError:
            return Result(
                request_id=request.request_id,
                status="failed",
                error="workspace_boundary_violation",
            )
        except Exception:
            return Result(
                request_id=request.request_id,
                status="failed",
                error="workspace_inspection_failed",
            )

        return Result(
            request_id=request.request_id,
            status="succeeded",
            output={
                "status": "complete",
                "areas": areas,
                "markers": markers,
            },
        )

    def _presence(self, relative_path: str) -> str:
        candidate = self._root.joinpath(*relative_path.split("/"))
        try:
            resolved = Path(self._resolver(candidate))
        except (OSError, RuntimeError, ValueError):
            raise WorkspaceBoundaryError from None

        if not resolved.is_absolute() or not self._within_root(resolved):
            raise WorkspaceBoundaryError

        if not candidate.exists():
            return "missing"

        if not resolved.exists():
            return "missing"

        return "present"

    def _within_root(self, path: Path) -> bool:
        try:
            root_text = os.path.normcase(str(self._root))
            path_text = os.path.normcase(str(path))
            return os.path.commonpath((root_text, path_text)) == root_text
        except ValueError:
            return False

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
        if step.sequence != 1 or step.operation != "inspect":
            return "unsupported_operation"
        if set(step.parameters):
            return "invalid_operation_shape"
        return None
