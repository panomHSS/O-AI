from __future__ import annotations

import unittest

from app.contracts.capability_permission import ExecutableCapabilityPermission
from app.contracts.command import CommandRequest, ExecutionPlan, Result
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.services.adapter_registry import AdapterRegistry
from app.services.capability_permission_policy import CapabilityPermissionPolicy
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.command_execution_coordinator import CommandExecutionCoordinator
from app.services.execution_approval_service import (
    ExecutionApprovalNotPendingError,
    ExecutionApprovalService,
    PendingExecutionApprovalStore,
)
from app.services.execution_guard import ExecutionGuard
from app.services.execution_planner import ExecutionPlanner
from app.services.module_runtime import ModuleRuntime
from app.services.tool_runtime import ToolRuntime


class _Tool:
    adapter_id = "tool.d93.workspace"
    tool_name = "d93_workspace"
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION

    def __init__(self) -> None:
        self.calls = 0

    def execute(
        self,
        request: CommandRequest,
        plan: ExecutionPlan,
    ) -> Result:
        self.calls += 1
        return Result(
            request_id=request.request_id,
            status="succeeded",
            output={"ok": True},
        )


class D93WorkspaceApprovalIsolationTests(unittest.TestCase):
    def _service(
        self,
        *,
        scope: WorkspaceScope,
        store: PendingExecutionApprovalStore,
        tool: _Tool,
    ) -> ExecutionApprovalService:
        registry = AdapterRegistry((tool,))
        policy = CapabilityPermissionPolicy(
            registry=registry,
            permissions=(
                ExecutableCapabilityPermission(
                    "exec.d93.workspace",
                    "tool",
                    tool.adapter_id,
                    "inspect",
                    "read",
                    "workspace_metadata",
                    True,
                ),
            ),
        )
        planner = ExecutionPlanner(
            registry=registry,
            decision_engine=CommandDecisionEngine(),
            ai_router=object(),  # type: ignore[arg-type]
            ai_discovery=object(),  # type: ignore[arg-type]
            permission_policy=policy,
        )
        guard = ExecutionGuard(
            registry=registry,
            permission_policy=policy,
        )
        coordinator = CommandExecutionCoordinator(
            planner=planner,
            guard=guard,
            tool_runtime=ToolRuntime(registry=registry),
            module_runtime=ModuleRuntime(registry=registry),
        )
        return ExecutionApprovalService(
            planner=planner,
            permission_policy=policy,
            coordinator=coordinator,
            store=store,
            workspace_scope=scope,
        )

    def test_cross_workspace_decision_is_not_pending_and_does_not_consume(self) -> None:
        store = PendingExecutionApprovalStore()
        tool = _Tool()
        personal = self._service(
            scope=WorkspaceScope(WorkspaceId.PERSONAL),
            store=store,
            tool=tool,
        )
        company = self._service(
            scope=WorkspaceScope(WorkspaceId.COMPANY),
            store=store,
            tool=tool,
        )

        outcome = personal.propose(
            target_kind="tool",
            adapter_id=tool.adapter_id,
            operation="inspect",
            parameters={},
        )
        proposal = outcome.proposal
        assert proposal is not None

        with self.assertRaises(ExecutionApprovalNotPendingError):
            company.approve(
                proposal.approval_id,
                proposal.plan_digest,
            )
        self.assertEqual(tool.calls, 0)

        decision = personal.approve(
            proposal.approval_id,
            proposal.plan_digest,
        )
        self.assertEqual(decision.execution.status, "completed")
        self.assertEqual(tool.calls, 1)


if __name__ == "__main__":
    unittest.main()
