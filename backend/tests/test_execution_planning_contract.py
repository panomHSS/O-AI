import unittest
from dataclasses import FrozenInstanceError

from app.contracts.command import ExecutionPlan
from app.contracts.execution_planning import ExecutionPlanningOutcome


class ExecutionPlanningContractTests(unittest.TestCase):
    def test_planned_outcome_is_immutable_and_requires_matching_plan(self) -> None:
        plan = ExecutionPlan(request_id="req-1", adapter_id="ai.test", owner_approval_required=False)
        outcome = ExecutionPlanningOutcome("req-1", "planned", "ai", plan, "planned")
        self.assertIs(outcome.plan, plan)
        with self.assertRaises(FrozenInstanceError):
            outcome.status = "rejected"  # type: ignore[misc]

    def test_planned_outcome_requires_plan_and_target_kind(self) -> None:
        with self.assertRaises(ValueError):
            ExecutionPlanningOutcome("req-1", "planned", None, None, "planned")

    def test_non_planned_outcome_rejects_plan_or_target_kind(self) -> None:
        plan = ExecutionPlan(request_id="req-1", adapter_id="ai.test")
        with self.assertRaises(ValueError):
            ExecutionPlanningOutcome("req-1", "rejected", None, plan, "rejected")
        with self.assertRaises(ValueError):
            ExecutionPlanningOutcome("req-1", "unavailable", "tool", None, "unavailable")

    def test_invalid_status_and_request_id_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ExecutionPlanningOutcome("", "rejected", None, None, "bad")
        with self.assertRaises(ValueError):
            ExecutionPlanningOutcome("req-1", "mystery", None, None, "bad")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
