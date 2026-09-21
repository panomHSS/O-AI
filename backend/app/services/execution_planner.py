"""Deterministic, side-effect-free D35 execution planner."""

from __future__ import annotations

from collections.abc import Mapping

from app.contracts.ai_brain_routing import AIMode
from app.contracts.ai_discovery import (
    AI_CAPABILITY_TEXT_GENERATION,
    AI_DISCOVERY_STATUS_AVAILABLE,
)
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep
from app.contracts.execution_planning import ExecutionPlanningOutcome
from app.contracts.task_aware_ai_routing import AITaskKind
from app.services.adapter_registry import AdapterRegistry
from app.services.capability_permission_policy import CapabilityPermissionPolicy
from app.services.ai_capability_model_discovery import AICapabilityModelDiscovery
from app.services.ai_router import AIRouter
from app.services.command_decision_engine import CHAT_MESSAGE_COMMAND, CommandDecisionEngine
from app.services.command_input_pipeline import CommandInputError, CommandInputPipeline
from app.services.execution_audit import ExecutionAuditTrail


TOOL_EXECUTE_COMMAND = "tool.execute"
MODULE_EXECUTE_COMMAND = "module.execute"
_STRUCTURED_EXECUTION_ARGUMENTS = frozenset({"adapter_id", "operation", "parameters"})


class ExecutionPlanner:
    """Describe one execution step without authorizing or executing it."""

    def __init__(
        self,
        *,
        registry: AdapterRegistry,
        decision_engine: CommandDecisionEngine,
        ai_router: AIRouter,
        ai_discovery: AICapabilityModelDiscovery,
        permission_policy: CapabilityPermissionPolicy,
        audit: ExecutionAuditTrail | None = None,
    ) -> None:
        self._registry = registry
        self._decision_engine = decision_engine
        self._ai_router = ai_router
        self._ai_discovery = ai_discovery
        self._permission_policy = permission_policy
        self._audit = audit

    def plan(
        self,
        request: CommandRequest,
        *,
        task_kind: AITaskKind = AITaskKind.GENERAL_CHAT,
        ai_mode: AIMode | None = None,
    ) -> ExecutionPlanningOutcome:
        """Return a deterministic single-step proposal for one command."""
        if not isinstance(task_kind, AITaskKind):
            outcome = self._rejected(
                "invalid_task_kind",
                getattr(request, "request_id", "invalid"),
            )
        elif ai_mode is not None and not isinstance(ai_mode, AIMode):
            outcome = self._rejected(
                "invalid_ai_mode",
                getattr(request, "request_id", "invalid"),
            )
        elif (
            not isinstance(request.request_id, str)
            or not request.request_id
            or request.request_id != request.request_id.strip()
        ):
            outcome = self._rejected("invalid_request", "invalid")
        elif request.command == CHAT_MESSAGE_COMMAND:
            outcome = self._plan_ai(
                request,
                task_kind=task_kind,
                ai_mode=ai_mode,
            )
        elif ai_mode is not None:
            outcome = self._rejected("invalid_ai_mode", request.request_id)
        elif task_kind is not AITaskKind.GENERAL_CHAT:
            outcome = self._rejected("invalid_task_kind", request.request_id)
        elif request.command == TOOL_EXECUTE_COMMAND:
            outcome = self._plan_structured(request, target_kind="tool")
        elif request.command == MODULE_EXECUTE_COMMAND:
            outcome = self._plan_structured(request, target_kind="module")
        else:
            outcome = self._rejected(
                "unsupported_command",
                request.request_id,
            )

        self._record_planning(outcome)
        return outcome

    def _record_planning(self, outcome: ExecutionPlanningOutcome) -> None:
        if self._audit is None:
            return
        adapter_id = outcome.plan.adapter_id if outcome.plan is not None else None
        try:
            self._audit.try_record(
                request_id=outcome.request_id,
                stage="planning",
                action="completed",
                status=outcome.status,
                target_kind=outcome.target_kind,
                adapter_id=adapter_id,
                reason_code=outcome.reason_code,
            )
        except Exception:
            pass

    def _plan_ai(
        self,
        request: CommandRequest,
        *,
        task_kind: AITaskKind,
        ai_mode: AIMode | None,
    ) -> ExecutionPlanningOutcome:
        try:
            CommandInputPipeline.validated_chat_arguments(request)
        except CommandInputError:
            return self._rejected("invalid_chat_command", request.request_id)

        decision = self._decision_engine.decide(request)
        if decision.disposition != "defer_to_existing_chat":
            return self._rejected("ai_route_rejected", request.request_id)

        if ai_mode is not None:
            route = self._ai_router.route_mode(
                decision,
                task_kind=task_kind,
                requested_mode=ai_mode,
            )
        elif task_kind is AITaskKind.GENERAL_CHAT:
            route = self._ai_router.route(decision)
        else:
            route = self._ai_router.route(decision, task_kind=task_kind)
        if route.status == "unavailable":
            safe_reason = (
                route.reason_code
                if route.reason_code
                in {
                    "local_ai_unavailable",
                    "cloud_ai_unavailable",
                    "default_adapter_unavailable",
                }
                else "ai_route_unavailable"
            )
            return self._unavailable(safe_reason, request.request_id)
        if route.status != "selected" or not route.adapter_id:
            return self._rejected("ai_route_rejected", request.request_id)

        if self._registry.resolve_ai(route.adapter_id) is None:
            return self._unavailable("ai_route_unavailable", request.request_id)

        try:
            discovery = self._ai_discovery.discover(route.adapter_id)
        except (KeyError, ValueError):
            return self._unavailable("ai_discovery_unavailable", request.request_id)

        if discovery.status != AI_DISCOVERY_STATUS_AVAILABLE:
            return self._unavailable("ai_discovery_unavailable", request.request_id)
        if AI_CAPABILITY_TEXT_GENERATION not in discovery.capability_ids:
            return self._unavailable("ai_capability_unavailable", request.request_id)
        if discovery.configured_model_id is None:
            return self._unavailable("ai_discovery_unavailable", request.request_id)

        plan = ExecutionPlan(
            request_id=request.request_id,
            adapter_id=route.adapter_id,
            steps=(
                ExecutionStep(
                    sequence=1,
                    operation="ai.generate_text",
                    parameters={
                        "capability_id": AI_CAPABILITY_TEXT_GENERATION,
                        "model_id": discovery.configured_model_id,
                    },
                ),
            ),
            owner_approval_required=False,
        )
        return ExecutionPlanningOutcome(
            request_id=request.request_id,
            status="planned",
            target_kind="ai",
            plan=plan,
            reason_code="ai_text_generation_planned",
        )

    def _plan_structured(self, request: CommandRequest, *, target_kind: str) -> ExecutionPlanningOutcome:
        reason_prefix = "tool" if target_kind == "tool" else "module"
        parsed = self._validated_structured_arguments(request)
        if parsed is None:
            return self._rejected(f"invalid_{reason_prefix}_command", request.request_id)

        adapter_id, operation, parameters = parsed
        if target_kind == "tool":
            adapter = self._registry.resolve_tool(adapter_id)
            if adapter is None:
                if self._registry.resolve_ai(adapter_id) is not None or self._registry.resolve_module(adapter_id) is not None:
                    return self._rejected("tool_adapter_kind_mismatch", request.request_id)
                return self._unavailable("tool_adapter_unavailable", request.request_id)
        else:
            adapter = self._registry.resolve_module(adapter_id)
            if adapter is None:
                if self._registry.resolve_ai(adapter_id) is not None or self._registry.resolve_tool(adapter_id) is not None:
                    return self._rejected("module_adapter_kind_mismatch", request.request_id)
                return self._unavailable("module_adapter_unavailable", request.request_id)

        permission = self._permission_policy.resolve(
            target_kind,
            adapter_id,
            operation,
        )
        if permission is None:
            return self._rejected(
                "capability_not_permitted",
                request.request_id,
            )

        plan = ExecutionPlan(
            request_id=request.request_id,
            adapter_id=adapter_id,
            steps=(ExecutionStep(sequence=1, operation=operation, parameters=dict(parameters)),),
            owner_approval_required=permission.owner_approval_required,
        )
        return ExecutionPlanningOutcome(
            request_id=request.request_id,
            status="planned",
            target_kind=target_kind,  # type: ignore[arg-type]
            plan=plan,
            reason_code=f"{reason_prefix}_execution_planned",
        )

    @staticmethod
    def _validated_structured_arguments(request: CommandRequest) -> tuple[str, str, Mapping[str, object]] | None:
        arguments = request.arguments
        if set(arguments) != _STRUCTURED_EXECUTION_ARGUMENTS:
            return None
        adapter_id = arguments["adapter_id"]
        operation = arguments["operation"]
        parameters = arguments["parameters"]
        if not isinstance(adapter_id, str) or not adapter_id or adapter_id != adapter_id.strip():
            return None
        if not isinstance(operation, str) or not operation or operation != operation.strip():
            return None
        if not isinstance(parameters, Mapping):
            return None
        return adapter_id, operation, parameters

    @staticmethod
    def _rejected(reason_code: str, request_id: str) -> ExecutionPlanningOutcome:
        return ExecutionPlanningOutcome(request_id, "rejected", None, None, reason_code)

    @staticmethod
    def _unavailable(reason_code: str, request_id: str) -> ExecutionPlanningOutcome:
        return ExecutionPlanningOutcome(request_id, "unavailable", None, None, reason_code)
