import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.repositories.project_action_execution_proposals import (
    ProjectActionExecutionProposalRepository,
)


class ProjectActionExecutionProposalRepositoryTests(
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

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_create_and_get_execution_proposal(
        self,
    ) -> None:
        proposal = self.repository.create(
            project_id="11111111-1111-1111-1111-111111111111",
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=7,
            source_action="Run acceptance tests",
            steps=[
                {
                    "sequence": 1,
                    "description": "Run acceptance tests",
                }
            ],
        )

        self.repository.commit()

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(
            loaded.id,
            proposal.id,
        )
        self.assertEqual(
            loaded.project_revision,
            7,
        )
        self.assertEqual(
            loaded.source_action,
            "Run acceptance tests",
        )
        self.assertEqual(
            loaded.status,
            "PENDING",
        )
        self.assertFalse(
            loaded.approved,
        )
        self.assertFalse(
            loaded.executed,
        )

    def test_decide_if_pending_updates_proposal_once(
        self,
    ) -> None:
        proposal = self.repository.create(
            project_id="11111111-1111-1111-1111-111111111111",
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=8,
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

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(
            loaded.status,
            "APPROVED",
        )
        self.assertTrue(
            loaded.approved,
        )
        self.assertFalse(
            loaded.executed,
        )

        decided_again = self.repository.decide_if_pending(
            proposal.id,
            status="REJECTED",
            approved=False,
        )

        self.assertFalse(decided_again)


if __name__ == "__main__":
    unittest.main()