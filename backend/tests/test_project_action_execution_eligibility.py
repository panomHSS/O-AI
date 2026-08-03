import unittest

from app.services.project_action_execution_eligibility import (
    ProjectActionExecutionEligibilityService,
)


class FakeExecutionProposal:
    def __init__(
        self,
        *,
        status: str,
        approved: bool,
        executed: bool,
        project_revision: int = 1,
    ) -> None:
        self.status = status
        self.approved = approved
        self.executed = executed
        self.project_revision = project_revision

class ProjectActionExecutionEligibilityTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.service = (
            ProjectActionExecutionEligibilityService()
        )

    def test_approved_unexecuted_proposal_is_eligible(
        self,
    ) -> None:
        proposal = FakeExecutionProposal(
            status="APPROVED",
            approved=True,
            executed=False,
            project_revision=17,
        )

        self.assertTrue(
            self.service.is_eligible(
                proposal,
                current_project_revision=17,
            )
        )
        
    def test_pending_proposal_is_not_eligible(
        self,
    ) -> None:
        proposal = FakeExecutionProposal(
            status="PENDING",
            approved=False,
            executed=False,
        )

        self.assertFalse(
            self.service.is_eligible(proposal)
        )

    def test_rejected_proposal_is_not_eligible(
        self,
    ) -> None:
        proposal = FakeExecutionProposal(
            status="REJECTED",
            approved=False,
            executed=False,
        )

        self.assertFalse(
            self.service.is_eligible(proposal)
        )

    def test_already_executed_proposal_is_not_eligible(
        self,
    ) -> None:
        proposal = FakeExecutionProposal(
            status="APPROVED",
            approved=True,
            executed=True,
        )

        self.assertFalse(
            self.service.is_eligible(proposal)
        )

    def test_approved_status_without_approval_is_not_eligible(
        self,
    ) -> None:
        proposal = FakeExecutionProposal(
            status="APPROVED",
            approved=False,
            executed=False,
        )

        self.assertFalse(
            self.service.is_eligible(proposal)
        )

    def test_nonapproved_status_with_approval_is_not_eligible(
        self,
    ) -> None:
        proposal = FakeExecutionProposal(
            status="PENDING",
            approved=True,
            executed=False,
        )

        self.assertFalse(
            self.service.is_eligible(proposal)
        )

    def test_matching_project_revision_is_eligible(
        self,
    ) -> None:
        proposal = FakeExecutionProposal(
            status="APPROVED",
            approved=True,
            executed=False,
            project_revision=17,
        )

        self.assertTrue(
            self.service.is_eligible(
                proposal,
                current_project_revision=17,
            )
        )

    def test_stale_project_revision_is_not_eligible(
        self,
    ) -> None:
        proposal = FakeExecutionProposal(
            status="APPROVED",
            approved=True,
            executed=False,
            project_revision=17,
        )

        self.assertFalse(
            self.service.is_eligible(
                proposal,
                current_project_revision=18,
            )
        )

    def test_future_project_revision_is_not_eligible(
        self,
    ) -> None:
        proposal = FakeExecutionProposal(
            status="APPROVED",
            approved=True,
            executed=False,
            project_revision=18,
        )

        self.assertFalse(
            self.service.is_eligible(
                proposal,
                current_project_revision=17,
            )
        )

    def test_invalid_project_revisions_are_not_eligible(
        self,
    ) -> None:
        invalid_cases = (
            (0, 0),
            (-1, -1),
            (True, True),
            ("17", "17"),
            (17, True),
            (True, 1),
        )

        for proposal_revision, current_revision in invalid_cases:
            with self.subTest(
                proposal_revision=proposal_revision,
                current_revision=current_revision,
            ):
                proposal = FakeExecutionProposal(
                    status="APPROVED",
                    approved=True,
                    executed=False,
                    project_revision=proposal_revision,
                )

                self.assertFalse(
                    self.service.is_eligible(
                        proposal,
                        current_project_revision=current_revision,
                    )
                )

    def test_missing_current_project_revision_is_not_eligible(
        self,
    ) -> None:
        proposal = FakeExecutionProposal(
            status="APPROVED",
            approved=True,
            executed=False,
            project_revision=17,
        )

        self.assertFalse(
            self.service.is_eligible(
                proposal,
                current_project_revision=None,
            )
        )

if __name__ == "__main__":
    unittest.main()