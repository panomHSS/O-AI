import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.project import Project
from app.repositories.project_action_execution_proposals import (
    ProjectActionExecutionProposalRepository,
)
from app.services.project_action_execution_claim import (
    ProjectActionExecutionClaimService,
)


class ProjectActionExecutionClaimTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
        )
        Base.metadata.create_all(self.engine)

        self.session = Session(self.engine)

        self.repository = (
            ProjectActionExecutionProposalRepository(
                self.session
            )
        )

        self.service = ProjectActionExecutionClaimService(
            self.repository
        )

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_claim_moves_approved_current_proposal_to_executing(
        self,
    ) -> None:
        project = Project(
            title="Execution claim",
            objective="Claim an approved action safely.",
            status="ACTIVE",
            current_revision=42,
        )

        self.session.add(project)
        self.session.flush()

        proposal = self.repository.create(
            project_id=project.id,
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=42,
            source_action="Run acceptance tests",
            steps=[
                {
                    "sequence": 1,
                    "description": "Run acceptance tests",
                }
            ],
        )

        self.repository.commit()

        decided = self.repository.decide_if_pending(
            proposal.id,
            status="APPROVED",
            approved=True,
        )

        self.assertTrue(decided)
        self.repository.commit()

        result = self.service.claim(proposal.id)

        self.assertEqual(result.status, "EXECUTING")
        self.assertTrue(result.approved)
        self.assertFalse(result.executed)

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.status, "EXECUTING")
        self.assertTrue(loaded.approved)
        self.assertFalse(loaded.executed)

    def test_claimed_proposal_cannot_be_claimed_again(
        self,
    ) -> None:
        project = Project(
            title="Execution claim",
            objective="Prevent duplicate execution claims.",
            status="ACTIVE",
            current_revision=43,
        )

        self.session.add(project)
        self.session.flush()

        proposal = self.repository.create(
            project_id=project.id,
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=43,
            source_action="Run acceptance tests",
            steps=[
                {
                    "sequence": 1,
                    "description": "Run acceptance tests",
                }
            ],
        )

        self.repository.commit()

        decided = self.repository.decide_if_pending(
            proposal.id,
            status="APPROVED",
            approved=True,
        )

        self.assertTrue(decided)
        self.repository.commit()

        first = self.service.claim(proposal.id)

        self.assertEqual(
            first.status,
            "EXECUTING",
        )
        self.assertTrue(first.approved)
        self.assertFalse(first.executed)

        with self.assertRaises(ValueError):
            self.service.claim(proposal.id)

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(
            loaded.status,
            "EXECUTING",
        )
        self.assertTrue(loaded.approved)
        self.assertFalse(loaded.executed)

    def test_approved_proposal_cannot_be_claimed_after_project_changes(
        self,
    ) -> None:
        project = Project(
            title="Execution claim",
            objective="Invalidate stale approvals.",
            status="ACTIVE",
            current_revision=44,
        )

        self.session.add(project)
        self.session.flush()

        proposal = self.repository.create(
            project_id=project.id,
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=44,
            source_action="Run acceptance tests",
            steps=[
                {
                    "sequence": 1,
                    "description": "Run acceptance tests",
                }
            ],
        )

        self.repository.commit()

        decided = self.repository.decide_if_pending(
            proposal.id,
            status="APPROVED",
            approved=True,
        )

        self.assertTrue(decided)
        self.repository.commit()

        project.current_revision = 45
        self.session.commit()

        with self.assertRaises(ValueError):
            self.service.claim(proposal.id)

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(
            loaded.status,
            "APPROVED",
        )
        self.assertTrue(loaded.approved)
        self.assertFalse(loaded.executed)

    def test_missing_proposal_cannot_be_claimed(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            self.service.claim(
                "99999999-9999-9999-9999-999999999999"
            )


    def test_pending_proposal_cannot_be_claimed(
        self,
    ) -> None:
        project = Project(
            title="Execution claim",
            objective="Reject unapproved execution.",
            status="ACTIVE",
            current_revision=46,
        )

        self.session.add(project)
        self.session.flush()

        proposal = self.repository.create(
            project_id=project.id,
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=46,
            source_action="Run acceptance tests",
            steps=[
                {
                    "sequence": 1,
                    "description": "Run acceptance tests",
                }
            ],
        )

        self.repository.commit()

        with self.assertRaises(ValueError):
            self.service.claim(proposal.id)

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.status, "PENDING")
        self.assertFalse(loaded.approved)
        self.assertFalse(loaded.executed)


if __name__ == "__main__":
    unittest.main()