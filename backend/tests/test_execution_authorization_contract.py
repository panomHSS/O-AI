import unittest
from dataclasses import FrozenInstanceError

from app.contracts.command import ExecutionPlan
from app.contracts.execution_authorization import (
    ExecutionAuthorization,
    OwnerApprovalEvidence,
)


class ExecutionAuthorizationContractTests(unittest.TestCase):
    def test_owner_approval_evidence_is_immutable_and_digest_bound(self) -> None:
        evidence = OwnerApprovalEvidence(
            request_id="req-1",
            plan_digest="a" * 64,
            decision="approved",
        )

        self.assertEqual(evidence.plan_digest, "a" * 64)
        with self.assertRaises(FrozenInstanceError):
            evidence.decision = "denied"  # type: ignore[misc]

    def test_evidence_rejects_invalid_digest_or_decision(self) -> None:
        with self.assertRaises(ValueError):
            OwnerApprovalEvidence("req-1", "not-a-digest", "approved")
        with self.assertRaises(ValueError):
            OwnerApprovalEvidence(
                "req-1",
                "a" * 64,
                "maybe",  # type: ignore[arg-type]
            )

    def test_authorized_outcome_requires_execution_ready_plan(self) -> None:
        ready = ExecutionPlan(
            request_id="req-1",
            adapter_id="tool.test",
            owner_approval_required=False,
        )
        authorization = ExecutionAuthorization(
            request_id="req-1",
            status="authorized",
            target_kind="tool",
            source_plan_digest="b" * 64,
            execution_plan=ready,
            reason_code="owner_approval_verified",
        )

        self.assertIs(authorization.execution_plan, ready)

        with self.assertRaises(ValueError):
            ExecutionAuthorization(
                request_id="req-1",
                status="authorized",
                target_kind="tool",
                source_plan_digest="b" * 64,
                execution_plan=ExecutionPlan(
                    "req-1",
                    "tool.test",
                    owner_approval_required=True,
                ),
                reason_code="bad",
            )

    def test_non_authorized_outcome_must_not_carry_execution_plan(self) -> None:
        with self.assertRaises(ValueError):
            ExecutionAuthorization(
                request_id="req-1",
                status="blocked",
                target_kind="tool",
                source_plan_digest="c" * 64,
                execution_plan=ExecutionPlan(
                    "req-1",
                    "tool.test",
                    owner_approval_required=False,
                ),
                reason_code="owner_approval_required",
            )


if __name__ == "__main__":
    unittest.main()
