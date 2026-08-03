import unittest

from app.schemas.project_action_planning import (
    ProjectActionPlan,
    ProjectActionPlanStep,
)
from app.schemas.project_action_execution import (
    ProjectActionExecutionProposal,
)
from app.services.project_action_execution import (
    ProjectActionExecutionProposalService,
)


class ProjectActionExecutionProposalTests(unittest.TestCase):
    def test_available_plan_creates_owner_reviewed_execution_proposal(
        self,
    ) -> None:
        plan = ProjectActionPlan(
            status="plan_available",
            project_revision=13,
            source_action="Run acceptance tests",
            owner_approval_required=True,
            steps=[
                ProjectActionPlanStep(
                    sequence=1,
                    description="Run acceptance tests",
                )
            ],
        )

        proposal = ProjectActionExecutionProposalService().propose(
            plan
        )

        self.assertIsInstance(
            proposal,
            ProjectActionExecutionProposal,
        )
        self.assertEqual(
            proposal.status,
            "awaiting_owner_approval",
        )
        self.assertEqual(
            proposal.project_revision,
            13,
        )
        self.assertEqual(
            proposal.source_action,
            "Run acceptance tests",
        )
        self.assertTrue(
            proposal.owner_approval_required
        )
        self.assertFalse(
            proposal.approved
        )
        self.assertFalse(
            proposal.executed
        )
        self.assertEqual(
            proposal.steps,
            plan.steps,
        )

    def test_unavailable_plan_creates_no_execution_proposal(
        self,
    ) -> None:
        plan = ProjectActionPlan(
            status="no_plan_available",
            project_revision=14,
            source_action=None,
            owner_approval_required=False,
            steps=[],
        )

        proposal = ProjectActionExecutionProposalService().propose(
            plan
        )

        self.assertIsNone(proposal)

    def test_plan_without_owner_approval_requirement_creates_no_execution_proposal(
        self,
    ) -> None:
        plan = ProjectActionPlan(
            status="plan_available",
            project_revision=15,
            source_action="Run acceptance tests",
            owner_approval_required=False,
            steps=[
                ProjectActionPlanStep(
                    sequence=1,
                    description="Run acceptance tests",
                )
            ],
        )

        proposal = ProjectActionExecutionProposalService().propose(
            plan
        )

        self.assertIsNone(proposal)


if __name__ == "__main__":
    unittest.main()