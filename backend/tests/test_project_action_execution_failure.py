import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.project import Project
from app.repositories.project_action_execution_proposals import (
    ProjectActionExecutionProposalRepository,
)
from app.services.project_action_execution_failure import (
    ProjectActionExecutionFailureService,
)


class ProjectActionExecutionFailureTests(
    unittest.TestCase
):
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

        self.service = (
            ProjectActionExecutionFailureService(
                self.repository
            )
        )

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_fail_marks_claimed_proposal_failed(
        self,
    ) -> None:
        project = Project(
            title="Execution failure",
            objective="Persist failed execution.",
            status="ACTIVE",
            current_revision=72,
        )

        self.session.add(project)
        self.session.flush()

        proposal = self.repository.create(
            project_id=project.id,
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=72,
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

        claimed = self.repository.claim_if_executable(
            proposal.id,
        )

        self.assertTrue(claimed)
        self.repository.commit()

        result = self.service.fail(
            proposal.id,
        )

        self.assertEqual(result.status, "FAILED")
        self.assertTrue(result.approved)
        self.assertFalse(result.executed)

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.status, "FAILED")
        self.assertTrue(loaded.approved)
        self.assertFalse(loaded.executed)

    def test_missing_proposal_cannot_be_failed(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            self.service.fail(
                "99999999-9999-9999-9999-999999999999"
            )


    def test_approved_but_unclaimed_proposal_cannot_be_failed(
        self,
    ) -> None:
        project = Project(
            title="Execution failure",
            objective="Prevent failure before claim.",
            status="ACTIVE",
            current_revision=73,
        )

        self.session.add(project)
        self.session.flush()

        proposal = self.repository.create(
            project_id=project.id,
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=73,
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

        with self.assertRaises(ValueError):
            self.service.fail(proposal.id)

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.status, "APPROVED")
        self.assertTrue(loaded.approved)
        self.assertFalse(loaded.executed)


    def test_failed_proposal_cannot_be_failed_again(
        self,
    ) -> None:
        project = Project(
            title="Execution failure",
            objective="Prevent duplicate failure transition.",
            status="ACTIVE",
            current_revision=74,
        )

        self.session.add(project)
        self.session.flush()

        proposal = self.repository.create(
            project_id=project.id,
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=74,
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

        claimed = self.repository.claim_if_executable(
            proposal.id,
        )

        self.assertTrue(claimed)
        self.repository.commit()

        first = self.service.fail(proposal.id)

        self.assertEqual(first.status, "FAILED")
        self.assertTrue(first.approved)
        self.assertFalse(first.executed)

        with self.assertRaises(ValueError):
            self.service.fail(proposal.id)

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.status, "FAILED")
        self.assertTrue(loaded.approved)
        self.assertFalse(loaded.executed)


if __name__ == "__main__":
    unittest.main()