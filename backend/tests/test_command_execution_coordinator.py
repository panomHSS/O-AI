import unittest

from app.contracts.command import (
    CommandRequest,
    ExecutionPlan,
    ExecutionStep,
    Result,
)
from app.contracts.execution_authorization import ExecutionAuthorization
from app.contracts.execution_planning import ExecutionPlanningOutcome
from app.services.command_execution_coordinator import (
    CommandExecutionCoordinator,
)


class FakePlanner:
    def __init__(self, outcome: ExecutionPlanningOutcome) -> None:
        self.outcome = outcome
        self.calls = 0

    def plan(self, request: CommandRequest) -> ExecutionPlanningOutcome:
        self.calls += 1
        return self.outcome


class FakeGuard:
    def __init__(self, authorization: ExecutionAuthorization) -> None:
        self.authorization = authorization
        self.calls = 0

    def authorize(self, request, planning, approval=None):
        self.calls += 1
        return self.authorization


class FakeRuntime:
    def __init__(self, result: Result) -> None:
        self.result = result
        self.calls = 0

    def execute(self, request, authorization) -> Result:
        self.calls += 1
        return self.result


class CommandExecutionCoordinatorTests(unittest.TestCase):
    @staticmethod
    def plan(
        target_kind: str = "tool",
        *,
        request_id: str = "req-1",
        approval_required: bool = True,
    ) -> ExecutionPlan:
        return ExecutionPlan(
            request_id=request_id,
            adapter_id=f"{target_kind}.stub",
            steps=(ExecutionStep(1, "run", {}),),
            owner_approval_required=approval_required,
        )

    @classmethod
    def planning(
        cls,
        target_kind: str = "tool",
        *,
        request_id: str = "req-1",
    ) -> ExecutionPlanningOutcome:
        return ExecutionPlanningOutcome(
            request_id=request_id,
            status="planned",
            target_kind=target_kind,  # type: ignore[arg-type]
            plan=cls.plan(target_kind, request_id=request_id),
            reason_code=f"{target_kind}_execution_planned",
        )

    @classmethod
    def authorization(
        cls,
        target_kind: str = "tool",
        *,
        request_id: str = "req-1",
        status: str = "authorized",
        reason_code: str = "owner_approval_verified",
    ) -> ExecutionAuthorization:
        ready = cls.plan(
            target_kind,
            request_id=request_id,
            approval_required=False,
        )
        return ExecutionAuthorization(
            request_id=request_id,
            status=status,  # type: ignore[arg-type]
            target_kind=target_kind,  # type: ignore[arg-type]
            source_plan_digest="c" * 64,
            execution_plan=ready if status == "authorized" else None,
            reason_code=reason_code,
        )

    def coordinator(
        self,
        planning: ExecutionPlanningOutcome,
        authorization: ExecutionAuthorization,
    ):
        self.tool = FakeRuntime(Result("req-1", "succeeded"))
        self.module = FakeRuntime(Result("req-1", "succeeded"))
        self.guard = FakeGuard(authorization)
        return CommandExecutionCoordinator(
            planner=FakePlanner(planning),  # type: ignore[arg-type]
            guard=self.guard,  # type: ignore[arg-type]
            tool_runtime=self.tool,  # type: ignore[arg-type]
            module_runtime=self.module,  # type: ignore[arg-type]
        )

    def test_authorized_tool_dispatches_only_tool_runtime(self) -> None:
        coordinator = self.coordinator(
            self.planning("tool"),
            self.authorization("tool"),
        )

        outcome = coordinator.execute(
            CommandRequest("req-1", "tool.execute")
        )

        self.assertEqual(outcome.status, "completed")
        self.assertEqual(self.tool.calls, 1)
        self.assertEqual(self.module.calls, 0)

    def test_authorized_module_dispatches_only_module_runtime(self) -> None:
        coordinator = self.coordinator(
            self.planning("module"),
            self.authorization("module"),
        )

        outcome = coordinator.execute(
            CommandRequest("req-1", "module.execute")
        )

        self.assertEqual(outcome.status, "completed")
        self.assertEqual(self.tool.calls, 0)
        self.assertEqual(self.module.calls, 1)

    def test_blocked_authorization_never_executes(self) -> None:
        coordinator = self.coordinator(
            self.planning("tool"),
            self.authorization(
                "tool",
                status="blocked",
                reason_code="owner_approval_required",
            ),
        )

        outcome = coordinator.execute(
            CommandRequest("req-1", "tool.execute")
        )

        self.assertEqual(outcome.status, "blocked")
        self.assertEqual(self.tool.calls, 0)
        self.assertEqual(self.module.calls, 0)

    def test_rejected_authorization_never_executes(self) -> None:
        coordinator = self.coordinator(
            self.planning("tool"),
            self.authorization(
                "tool",
                status="rejected",
                reason_code="approval_plan_mismatch",
            ),
        )

        outcome = coordinator.execute(
            CommandRequest("req-1", "tool.execute")
        )

        self.assertEqual(outcome.status, "rejected")
        self.assertEqual(self.tool.calls, 0)
        self.assertEqual(self.module.calls, 0)

    def test_unavailable_planning_never_calls_guard_or_runtime(self) -> None:
        planning = ExecutionPlanningOutcome(
            "req-1",
            "unavailable",
            None,
            None,
            "tool_adapter_unavailable",
        )
        coordinator = self.coordinator(
            planning,
            self.authorization("tool"),
        )

        outcome = coordinator.execute(
            CommandRequest("req-1", "tool.execute")
        )

        self.assertEqual(outcome.status, "unavailable")
        self.assertEqual(self.guard.calls, 0)
        self.assertEqual(self.tool.calls, 0)

    def test_ai_target_is_rejected_to_compatibility_lane(self) -> None:
        planning = ExecutionPlanningOutcome(
            request_id="req-1",
            status="planned",
            target_kind="ai",
            plan=self.plan("ai", approval_required=False),
            reason_code="ai_execution_planned",
        )
        coordinator = self.coordinator(
            planning,
            self.authorization("tool"),
        )

        outcome = coordinator.execute(
            CommandRequest("req-1", "chat.message")
        )

        self.assertEqual(outcome.status, "rejected")
        self.assertEqual(
            outcome.reason_code,
            "ai_execution_uses_chat_lane",
        )
        self.assertEqual(self.guard.calls, 0)
        self.assertEqual(self.tool.calls, 0)
        self.assertEqual(self.module.calls, 0)


if __name__ == "__main__":
    unittest.main()
