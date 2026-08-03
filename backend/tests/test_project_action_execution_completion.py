import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.project import Project
from app.repositories.project_action_execution_proposals import (
    ProjectActionExecutionProposalRepository,
)
from app.services.project_action_execution_completion import (
    ProjectActionExecutionCompletionService,
)


class ProjectActionExecutionCompletionTests(
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
            ProjectActionExecutionCompletionService(
                self.repository
            )
        )

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_complete_marks_claimed_proposal_executed(
        self,
    ) -> None:
        project = Project(
            title="Execution completion",
            objective="Persist successful execution.",
            status="ACTIVE",
            current_revision=60,
        )

        self.session.add(project)
        self.session.flush()

        proposal = self.repository.create(
            project_id=project.id,
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=60,
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

        result = self.service.complete(
            proposal.id,
        )

        self.assertEqual(
            result.status,
            "EXECUTED",
        )
        self.assertTrue(result.approved)
        self.assertTrue(result.executed)

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(
            loaded.status,
            "EXECUTED",
        )
        self.assertTrue(loaded.approved)
        self.assertTrue(loaded.executed)

    def test_missing_proposal_cannot_be_completed(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            self.service.complete(
                "99999999-9999-9999-9999-999999999999"
            )


    def test_approved_but_unclaimed_proposal_cannot_be_completed(
        self,
    ) -> None:
        project = Project(
            title="Execution completion",
            objective="Prevent completion before claim.",
            status="ACTIVE",
            current_revision=61,
        )

        self.session.add(project)
        self.session.flush()

        proposal = self.repository.create(
            project_id=project.id,
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=61,
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
            self.service.complete(proposal.id)

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.status, "APPROVED")
        self.assertTrue(loaded.approved)
        self.assertFalse(loaded.executed)


    def test_completed_proposal_cannot_be_completed_again(
        self,
    ) -> None:
        project = Project(
            title="Execution completion",
            objective="Prevent duplicate completion.",
            status="ACTIVE",
            current_revision=62,
        )

        self.session.add(project)
        self.session.flush()

        proposal = self.repository.create(
            project_id=project.id,
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=62,
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

        first = self.service.complete(proposal.id)

        self.assertEqual(first.status, "EXECUTED")
        self.assertTrue(first.executed)

        with self.assertRaises(ValueError):
            self.service.complete(proposal.id)

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.status, "EXECUTED")
        self.assertTrue(loaded.approved)
        self.assertTrue(loaded.executed)


if __name__ == "__main__":
    unittest.main()
    