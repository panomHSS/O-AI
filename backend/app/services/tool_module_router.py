"""Fail-closed D27 selector backed by the D31 unified adapter registry."""

from __future__ import annotations

from collections.abc import Iterable

from app.contracts.command import CommandRequest, ExecutionPlan
from app.contracts.tool_module import ModuleAdapter, ToolAdapter
from app.contracts.tool_module_route import ToolModuleRouteDecision
from app.services.adapter_registry import AdapterRegistry


class ToolModuleRouter:
    """Select a registered adapter from structured contracts without execution."""

    def __init__(
        self,
        adapters: Iterable[ToolAdapter | ModuleAdapter] | None = None,
        *,
        registry: AdapterRegistry | None = None,
    ) -> None:
        if registry is not None and adapters is not None:
            raise ValueError("Provide adapters or registry, not both.")
        if registry is not None:
            self._registry = registry
            return

        executable_adapters = tuple(adapters or ())
        for adapter in executable_adapters:
            if not isinstance(adapter, (ToolAdapter, ModuleAdapter)):
                raise TypeError("D27 adapters must implement ToolAdapter or ModuleAdapter.")
        self._registry = AdapterRegistry(executable_adapters)

    def route(
        self,
        request: CommandRequest,
        plan: ExecutionPlan,
    ) -> ToolModuleRouteDecision:
        """Return a fail-closed route decision without parsing or executing input."""
        if request.request_id != plan.request_id:
            return ToolModuleRouteDecision(
                request_id=request.request_id,
                status="rejected",
                adapter_id=None,
                reason_code="request_plan_mismatch",
            )

        if self._registry.resolve_executable(plan.adapter_id) is None:
            return ToolModuleRouteDecision(
                request_id=request.request_id,
                status="unavailable",
                adapter_id=plan.adapter_id,
                reason_code="adapter_unavailable",
            )

        if plan.owner_approval_required:
            return ToolModuleRouteDecision(
                request_id=request.request_id,
                status="blocked",
                adapter_id=plan.adapter_id,
                reason_code="owner_approval_required",
            )

        return ToolModuleRouteDecision(
            request_id=request.request_id,
            status="selected",
            adapter_id=plan.adapter_id,
            reason_code="adapter_selected",
        )

    def get_adapter(self, adapter_id: str) -> ToolAdapter | ModuleAdapter | None:
        """Resolve a registered adapter for separately approved orchestration."""
        return self._registry.resolve_executable(adapter_id)
