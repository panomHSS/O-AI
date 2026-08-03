import unittest

from app.schemas.project_action_execution import (
    ProjectActionExecutionProposal,
)
from app.schemas.project_action_planning import (
    ProjectActionPlanStep,
)
from app.services.project_action_execution_approval import (
    ProjectActionExecutionApprovalService,
)


class ProjectActionExecutionApprovalTests(unittest.TestCase):
    def test_owner_can_approve_execution_proposal_without_executing(
        self,
    ) -> None:
        proposal = ProjectActionExecutionProposal(
            status="awaiting_owner_approval",
            project_revision=17,
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

        approved = ProjectActionExecutionApprovalService().approve(
            proposal
        )

        self.assertEqual(
            approved.status,
            "approved",
        )
        self.assertTrue(approved.approved)
        self.assertFalse(approved.executed)
        self.assertEqual(
            approved.project_revision,
            17,
        )
        self.assertEqual(
            approved.source_action,
            "Run acceptance tests",
        )
        self.assertEqual(
            approved.steps,
            proposal.steps,
        )

    def test_owner_cannot_approve_proposal_that_is_not_awaiting_approval(
        self,
    ) -> None:
        proposal = ProjectActionExecutionProposal(
            status="approved",
            project_revision=18,
            source_action="Run acceptance tests",
            owner_approval_required=True,
            approved=True,
            executed=False,
            steps=[
                ProjectActionPlanStep(
                    sequence=1,
                    description="Run acceptance tests",
                )
            ],
        )

        with self.assertRaises(ValueError):
            ProjectActionExecutionApprovalService().approve(
                proposal
            )

    def test_owner_can_reject_execution_proposal_without_executing(
        self,
    ) -> None:
        proposal = ProjectActionExecutionProposal(
            status="awaiting_owner_approval",
            project_revision=19,
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

        rejected = ProjectActionExecutionApprovalService().reject(
            proposal
        )

        self.assertEqual(
            rejected.status,
            "rejected",
        )
        self.assertFalse(rejected.approved)
        self.assertFalse(rejected.executed)
        self.assertEqual(
            rejected.project_revision,
            19,
        )
        self.assertEqual(
            rejected.source_action,
            "Run acceptance tests",
        )
        self.assertEqual(
            rejected.steps,
            proposal.steps,
        )

    def test_owner_cannot_reject_proposal_that_is_not_awaiting_approval(
        self,
    ) -> None:
        proposal = ProjectActionExecutionProposal(
            status="rejected",
            project_revision=20,
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

        with self.assertRaises(ValueError):
            ProjectActionExecutionApprovalService().reject(
                proposal
            )

    def test_owner_cannot_approve_proposal_without_approval_requirement(
        self,
    ) -> None:
        proposal = ProjectActionExecutionProposal(
            status="awaiting_owner_approval",
            project_revision=21,
            source_action="Run acceptance tests",
            owner_approval_required=False,
            approved=False,
            executed=False,
            steps=[
                ProjectActionPlanStep(
                    sequence=1,
                    description="Run acceptance tests",
                )
            ],
        )

        with self.assertRaises(ValueError):
            ProjectActionExecutionApprovalService().approve(
                proposal
            )

    def test_owner_cannot_reject_proposal_without_approval_requirement(
        self,
    ) -> None:
        proposal = ProjectActionExecutionProposal(
            status="awaiting_owner_approval",
            project_revision=22,
            source_action="Run acceptance tests",
            owner_approval_required=False,
            approved=False,
            executed=False,
            steps=[
                ProjectActionPlanStep(
                    sequence=1,
                    description="Run acceptance tests",
                )
            ],
        )

        with self.assertRaises(ValueError):
            ProjectActionExecutionApprovalService().reject(
                proposal
            )


if __name__ == "__main__":
    unittest.main()