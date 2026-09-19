from tests.workspace_fixture import TEST_WORKSPACE_SCOPE
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from app.contracts.capability_permission import ExecutableCapabilityPermission
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep, Result
from app.contracts.execution_planning import ExecutionPlanningOutcome
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION
from app.services.adapter_registry import AdapterRegistry
from app.services.capability_permission_policy import CapabilityPermissionPolicy
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.command_execution_coordinator import CommandExecutionCoordinator
from app.services.execution_approval_service import (
    ExecutionApprovalExpiredError,
    ExecutionApprovalNotPendingError,
    ExecutionApprovalPlanMismatchError,
    ExecutionApprovalService,
    ExecutionApprovalStoreFullError,
    PendingExecutionApprovalStore,
)
from app.services.execution_guard import ExecutionGuard, execution_plan_digest
from app.services.execution_planner import ExecutionPlanner
from app.services.module_runtime import ModuleRuntime
from app.services.tool_runtime import ToolRuntime


class MutableClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 9, 14, 15, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.value

    def advance(self, *, seconds: int) -> None:
        self.value += timedelta(seconds=seconds)


class SequenceFactory:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.index = 0

    def __call__(self) -> str:
        self.index += 1
        return f"{self.prefix}-{self.index}"


class StubToolAdapter:
    adapter_id = "tool.stub"
    tool_name = "stub"
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
            output={"value": plan.steps[0].parameters.get("value")},
        )


class StubModuleAdapter:
    adapter_id = "module.stub"
    module_name = "stub"
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
            output={"module": "ok"},
        )


class RejectAfterFirstPlan:
    def __init__(self, delegate: ExecutionPlanner) -> None:
        self.delegate = delegate
        self.calls = 0

    def plan(self, request: CommandRequest) -> ExecutionPlanningOutcome:
        self.calls += 1
        if self.calls == 1:
            return self.delegate.plan(request)
        return ExecutionPlanningOutcome(
            request_id=request.request_id,
            status="rejected",
            target_kind=None,
            plan=None,
            reason_code="capability_not_permitted",
        )


class ExecutionApprovalServiceTests(unittest.TestCase):
    def build(
        self,
        *,
        approval_required: bool = True,
        max_pending: int = 100,
        ttl_seconds: int = 600,
        switch_after_proposal: bool = False,
    ):
        tool = StubToolAdapter()
        module = StubModuleAdapter()
        registry = AdapterRegistry((tool, module))
        policy = CapabilityPermissionPolicy(
            registry=registry,
            permissions=(
                ExecutableCapabilityPermission(
                    "exec.test.tool",
                    "tool",
                    "tool.stub",
                    "echo",
                    "none",
                    "none",
                    approval_required,
                ),
                ExecutableCapabilityPermission(
                    "exec.test.module",
                    "module",
                    "module.stub",
                    "inspect",
                    "read",
                    "workspace_metadata",
                    True,
                ),
            ),
        )
        real_planner = ExecutionPlanner(
            registry=registry,
            decision_engine=CommandDecisionEngine(),
            ai_router=object(),  # type: ignore[arg-type]
            ai_discovery=object(),  # type: ignore[arg-type]
            permission_policy=policy,
        )
        planner = (
            RejectAfterFirstPlan(real_planner)
            if switch_after_proposal
            else real_planner
        )
        guard = ExecutionGuard(
            registry=registry,
            permission_policy=policy,
        )
        coordinator = CommandExecutionCoordinator(
            planner=planner,  # type: ignore[arg-type]
            guard=guard,
            tool_runtime=ToolRuntime(registry=registry),
            module_runtime=ModuleRuntime(registry=registry),
        )
        clock = MutableClock()
        store = PendingExecutionApprovalStore(
            ttl=timedelta(seconds=ttl_seconds),
            max_pending=max_pending,
            clock=clock,
            approval_id_factory=SequenceFactory("approval"),
        )
        service = ExecutionApprovalService(
            workspace_scope=TEST_WORKSPACE_SCOPE,
            planner=planner,  # type: ignore[arg-type]
            permission_policy=policy,
            coordinator=coordinator,
            store=store,
            request_id_factory=SequenceFactory("request"),
        )
        return service, tool, module, store, clock

    @staticmethod
    def propose_tool(service: ExecutionApprovalService):
        return service.propose(
            target_kind="tool",
            adapter_id="tool.stub",
            operation="echo",
            parameters={"value": "hello"},
        )

    def test_proposal_exposes_exact_plan_and_d44_metadata_without_execution(self) -> None:
        service, tool, _, store, _ = self.build()

        outcome = self.propose_tool(service)

        self.assertEqual(outcome.status, "pending")
        proposal = outcome.proposal
        assert proposal is not None
        self.assertEqual(proposal.approval_id, "approval-1")
        self.assertEqual(proposal.request_id, "request-1")
        self.assertEqual(proposal.target_kind, "tool")
        self.assertEqual(proposal.adapter_id, "tool.stub")
        self.assertEqual(proposal.operation, "echo")
        self.assertEqual(dict(proposal.parameters), {"value": "hello"})
        self.assertEqual(proposal.capability_id, "exec.test.tool")
        self.assertEqual(proposal.effect, "none")
        self.assertEqual(proposal.data_class, "none")
        self.assertTrue(proposal.owner_approval_required)
        expected_plan = ExecutionPlan(
            request_id=proposal.request_id,
            adapter_id=proposal.adapter_id,
            steps=(
                ExecutionStep(
                    1,
                    proposal.operation,
                    proposal.parameters,
                ),
            ),
            owner_approval_required=True,
        )
        self.assertEqual(
            proposal.plan_digest,
            execution_plan_digest(expected_plan),
        )
        self.assertEqual(tool.calls, 0)
        self.assertEqual(store.pending_count, 1)

    def test_unpermitted_operation_creates_no_ticket(self) -> None:
        service, tool, _, store, _ = self.build()

        outcome = service.propose(
            target_kind="tool",
            adapter_id="tool.stub",
            operation="delete",
            parameters={},
        )

        self.assertEqual(outcome.status, "rejected")
        self.assertEqual(outcome.reason_code, "capability_not_permitted")
        self.assertIsNone(outcome.proposal)
        self.assertEqual(store.pending_count, 0)
        self.assertEqual(tool.calls, 0)

    def test_module_can_be_proposed_and_approved(self) -> None:
        service, _, module, _, _ = self.build()
        proposal_outcome = service.propose(
            target_kind="module",
            adapter_id="module.stub",
            operation="inspect",
            parameters={},
        )
        proposal = proposal_outcome.proposal
        assert proposal is not None

        decision = service.approve(
            proposal.approval_id,
            proposal.plan_digest,
        )

        self.assertEqual(decision.execution.status, "completed")
        self.assertEqual(module.calls, 1)

    def test_approve_executes_once_and_replay_fails_closed(self) -> None:
        service, tool, _, _, _ = self.build()
        proposal = self.propose_tool(service).proposal
        assert proposal is not None

        first = service.approve(
            proposal.approval_id,
            proposal.plan_digest,
        )

        self.assertEqual(first.execution.status, "completed")
        self.assertEqual(tool.calls, 1)
        with self.assertRaises(ExecutionApprovalNotPendingError):
            service.approve(
                proposal.approval_id,
                proposal.plan_digest,
            )
        self.assertEqual(tool.calls, 1)

    def test_deny_consumes_ticket_and_never_executes(self) -> None:
        service, tool, _, _, _ = self.build()
        proposal = self.propose_tool(service).proposal
        assert proposal is not None

        decision = service.deny(
            proposal.approval_id,
            proposal.plan_digest,
        )

        self.assertEqual(decision.execution.status, "blocked")
        self.assertEqual(
            decision.execution.reason_code,
            "owner_approval_denied",
        )
        self.assertEqual(tool.calls, 0)
        with self.assertRaises(ExecutionApprovalNotPendingError):
            service.deny(
                proposal.approval_id,
                proposal.plan_digest,
            )

    def test_digest_mismatch_invalidates_ticket(self) -> None:
        service, tool, _, _, _ = self.build()
        proposal = self.propose_tool(service).proposal
        assert proposal is not None
        wrong = "0" * 64
        if wrong == proposal.plan_digest:
            wrong = "f" * 64

        with self.assertRaises(ExecutionApprovalPlanMismatchError):
            service.approve(proposal.approval_id, wrong)
        with self.assertRaises(ExecutionApprovalNotPendingError):
            service.approve(
                proposal.approval_id,
                proposal.plan_digest,
            )
        self.assertEqual(tool.calls, 0)

    def test_expired_ticket_cannot_execute(self) -> None:
        service, tool, _, store, clock = self.build(ttl_seconds=10)
        proposal = self.propose_tool(service).proposal
        assert proposal is not None
        clock.advance(seconds=11)

        with self.assertRaises(ExecutionApprovalExpiredError):
            service.approve(
                proposal.approval_id,
                proposal.plan_digest,
            )

        self.assertEqual(tool.calls, 0)
        self.assertEqual(store.pending_count, 0)

    def test_capacity_is_bounded_without_silent_eviction(self) -> None:
        service, tool, _, store, _ = self.build(max_pending=1)
        first = self.propose_tool(service).proposal
        assert first is not None

        with self.assertRaises(ExecutionApprovalStoreFullError):
            self.propose_tool(service)

        self.assertEqual(store.pending_count, 1)
        decision = service.approve(
            first.approval_id,
            first.plan_digest,
        )
        self.assertEqual(decision.execution.status, "completed")
        self.assertEqual(tool.calls, 1)

    def test_public_surface_still_requires_explicit_decision_when_policy_does_not(self) -> None:
        service, tool, _, _, _ = self.build(approval_required=False)

        proposal = self.propose_tool(service).proposal
        assert proposal is not None

        self.assertFalse(proposal.owner_approval_required)
        self.assertEqual(tool.calls, 0)
        decision = service.approve(
            proposal.approval_id,
            proposal.plan_digest,
        )
        self.assertEqual(decision.execution.status, "completed")
        self.assertEqual(tool.calls, 1)

    def test_concurrent_approval_has_one_winner_and_one_execution(self) -> None:
        service, tool, _, _, _ = self.build()
        proposal = self.propose_tool(service).proposal
        assert proposal is not None

        def attempt() -> str:
            try:
                outcome = service.approve(
                    proposal.approval_id,
                    proposal.plan_digest,
                )
                return outcome.execution.status
            except ExecutionApprovalNotPendingError:
                return "not_pending"

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: attempt(), range(2)))

        self.assertEqual(sorted(results), ["completed", "not_pending"])
        self.assertEqual(tool.calls, 1)

    def test_coordinator_replans_after_owner_approval(self) -> None:
        service, tool, _, _, _ = self.build(
            switch_after_proposal=True
        )
        proposal = self.propose_tool(service).proposal
        assert proposal is not None

        decision = service.approve(
            proposal.approval_id,
            proposal.plan_digest,
        )

        self.assertEqual(decision.execution.status, "rejected")
        self.assertEqual(
            decision.execution.reason_code,
            "capability_not_permitted",
        )
        self.assertEqual(tool.calls, 0)


if __name__ == "__main__":
    unittest.main()
