import unittest

from app.schemas.project_action_execution import (
    ProjectActionExecutionProposal,
)
from app.schemas.project_action_planning import (
    ProjectActionPlanStep,
)
from app.services.project_action_execution_approval_orchestrator import (
    ProjectActionExecutionApprovalOrchestrator,
)


class ProjectActionExecutionApprovalOrchestratorTests(
    unittest.TestCase
):
    def test_owner_approval_transitions_proposal_without_executing(
        self,
    ) -> None:
        proposal = ProjectActionExecutionProposal(
            status="awaiting_owner_approval",
            project_revision=23,
            source_action="Run acceptance tests",
            owner_approval_required=True,
            approved=False,
            executed=False,
            steps=[
                ProjectActionPlanStep(
                    sequence=1,
                    description="Run acceptance tests",
                )
            ],
        )

        result = (
            ProjectActionExecutionApprovalOrchestrator()
            .approve(proposal)
        )

        self.assertEqual(
            result.status,
            "approved",
        )
        self.assertTrue(result.approved)
        self.assertFalse(result.executed)
        self.assertEqual(
            result.project_revision,
            23,
        )
        self.assertEqual(
            result.source_action,
            "Run acceptance tests",
        )

    def test_owner_rejection_transitions_proposal_without_executing(
        self,
    ) -> None:
        proposal = ProjectActionExecutionProposal(
            status="awaiting_owner_approval",
            project_revision=24,
            source_action="Run acceptance tests",
            owner_approval_required=True,
            approved=False,
            executed=False,
            steps=[
                ProjectActionPlanStep(
                    sequence=1,
                    description="Run acceptance tests",
                )
            ],
        )

        result = (
            ProjectActionExecutionApprovalOrchestrator()
            .reject(proposal)
        )

        self.assertEqual(
            result.status,
            "rejected",
        )
        self.assertFalse(result.approved)
        self.assertFalse(result.executed)
        self.assertEqual(
            result.project_revision,
            24,
        )
        self.assertEqual(
            result.source_action,
            "Run acceptance tests",
        )


if __name__ == "__main__":
    unittest.main()