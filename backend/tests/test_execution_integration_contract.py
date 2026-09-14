import unittest
from dataclasses import FrozenInstanceError

from app.contracts.command import ExecutionPlan, ExecutionStep, Result
from app.contracts.execution_authorization import ExecutionAuthorization
from app.contracts.execution_integration import ExecutionIntegrationOutcome
from app.contracts.execution_planning import ExecutionPlanningOutcome


class ExecutionIntegrationContractTests(unittest.TestCase):
    @staticmethod
    def planned(
        *,
        request_id: str = "req-1",
        target_kind: str = "tool",
        approval_required: bool = True,
    ) -> ExecutionPlanningOutcome:
        return ExecutionPlanningOutcome(
            request_id=request_id,
            status="planned",
            target_kind=target_kind,  # type: ignore[arg-type]
            plan=ExecutionPlan(
                request_id=request_id,
                adapter_id=f"{target_kind}.stub",
                steps=(ExecutionStep(1, "run", {}),),
                owner_approval_required=approval_required,
            ),
            reason_code=f"{target_kind}_execution_planned",
        )

    @staticmethod
    def authorized(
        planning: ExecutionPlanningOutcome,
    ) -> ExecutionAuthorization:
        assert planning.plan is not None
        ready = ExecutionPlan(
            request_id=planning.plan.request_id,
            adapter_id=planning.plan.adapter_id,
            steps=planning.plan.steps,
            owner_approval_required=False,
        )
        return ExecutionAuthorization(
            request_id=planning.request_id,
            status="authorized",
            target_kind=planning.target_kind,
            source_plan_digest="a" * 64,
            execution_plan=ready,
            reason_code="owner_approval_verified",
        )

    def test_completed_outcome_is_immutable(self) -> None:
        planning = self.planned()
        authorization = self.authorized(planning)
        outcome = ExecutionIntegrationOutcome(
            request_id="req-1",
            status="completed",
            target_kind="tool",
            planning=planning,
            authorization=authorization,
            result=Result("req-1", "succeeded"),
            reason_code="execution_completed",
        )

        with self.assertRaises(FrozenInstanceError):
            outcome.status = "rejected"  # type: ignore[misc]

    def test_completed_requires_authorized_execution_and_result(self) -> None:
        planning = self.planned()

        with self.assertRaises(ValueError):
            ExecutionIntegrationOutcome(
                request_id="req-1",
                status="completed",
                target_kind="tool",
                planning=planning,
                authorization=None,
                result=None,
                reason_code="execution_completed",
            )

    def test_blocked_requires_blocked_authorization(self) -> None:
        planning = self.planned()
        blocked = ExecutionAuthorization(
            request_id="req-1",
            status="blocked",
            target_kind="tool",
            source_plan_digest="b" * 64,
            execution_plan=None,
            reason_code="owner_approval_required",
        )

        outcome = ExecutionIntegrationOutcome(
            request_id="req-1",
            status="blocked",
            target_kind="tool",
            planning=planning,
            authorization=blocked,
            result=None,
            reason_code="owner_approval_required",
        )

        self.assertEqual(outcome.status, "blocked")

    def test_noncompleted_outcome_cannot_carry_result(self) -> None:
        planning = self.planned()

        with self.assertRaises(ValueError):
            ExecutionIntegrationOutcome(
                request_id="req-1",
                status="rejected",
                target_kind="tool",
                planning=planning,
                authorization=None,
                result=Result("req-1", "failed"),
                reason_code="rejected",
            )

    def test_ai_lane_rejection_can_preserve_ai_target(self) -> None:
        planning = self.planned(
            target_kind="ai",
            approval_required=False,
        )

        outcome = ExecutionIntegrationOutcome(
            request_id="req-1",
            status="rejected",
            target_kind="ai",
            planning=planning,
            authorization=None,
            result=None,
            reason_code="ai_execution_uses_chat_lane",
        )

        self.assertEqual(outcome.target_kind, "ai")


if __name__ == "__main__":
    unittest.main()
