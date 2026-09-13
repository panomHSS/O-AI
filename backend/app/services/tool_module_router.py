"""Fail-closed D27 selector for structured Tool/Module execution plans."""

from __future__ import annotations

from collections.abc import Iterable

from app.contracts.command import CommandRequest, ExecutionPlan
from app.contracts.tool_module import (
    TOOL_MODULE_ADAPTER_CONTRACT_VERSION,
    ModuleAdapter,
    ToolAdapter,
)
from app.contracts.tool_module_route import ToolModuleRouteDecision


class ToolModuleRouter:
    """Select a registered adapter from structured contracts without execution."""

    def __init__(self, adapters: Iterable[ToolAdapter | ModuleAdapter]) -> None:
        self._adapters: dict[str, ToolAdapter | ModuleAdapter] = {}
        for adapter in adapters:
            if not isinstance(adapter, (ToolAdapter, ModuleAdapter)):
                raise TypeError("D27 adapters must implement ToolAdapter or ModuleAdapter.")
            if adapter.contract_version != TOOL_MODULE_ADAPTER_CONTRACT_VERSION:
                raise ValueError("D27 adapters must implement Tool/Module Adapter Contract v1.")
            if adapter.adapter_id in self._adapters:
                raise ValueError("D27 adapter IDs must be unique.")
            self._adapters[adapter.adapter_id] = adapter

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

        if plan.adapter_id not in self._adapters:
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
