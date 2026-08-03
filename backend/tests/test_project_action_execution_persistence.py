import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.repositories.project_action_execution_proposals import (
    ProjectActionExecutionProposalRepository,
)
from app.schemas.project_action_execution import (
    ProjectActionExecutionProposal,
)
from app.schemas.project_action_planning import (
    ProjectActionPlanStep,
)
from app.services.project_action_execution_persistence import (
    ProjectActionExecutionPersistenceService,
)


class ProjectActionExecutionPersistenceTests(
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
            ProjectActionExecutionPersistenceService(
                self.repository
            )
        )

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_persist_creates_durable_pending_proposal(
        self,
    ) -> None:
        proposal = ProjectActionExecutionProposal(
            status="awaiting_owner_approval",
            project_revision=25,
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

        record = self.service.persist(
            proposal,
            project_id=(
                "11111111-1111-1111-1111-111111111111"
            ),
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
        )

        self.assertIsNotNone(record.id)
        self.assertEqual(
            record.project_revision,
            25,
        )
        self.assertEqual(
            record.source_action,
            "Run acceptance tests",
        )
        self.assertEqual(
            record.status,
            "PENDING",
        )
        self.assertFalse(record.approved)
        self.assertFalse(record.executed)

        loaded = self.repository.get(record.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(
            loaded.id,
            record.id,
        )

    def test_persist_rejects_proposal_not_awaiting_owner_approval(
        self,
    ) -> None:
        proposal = ProjectActionExecutionProposal(
            status="approved",
            project_revision=26,
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
            self.service.persist(
                proposal,
                project_id=(
                    "11111111-1111-1111-1111-111111111111"
                ),
                conversation_id=(
                    "22222222-2222-2222-2222-222222222222"
                ),
            )

    def test_persist_rejects_proposal_without_approval_requirement(
        self,
    ) -> None:
        proposal = ProjectActionExecutionProposal(
            status="awaiting_owner_approval",
            project_revision=27,
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
            self.service.persist(
                proposal,
                project_id=(
                    "11111111-1111-1111-1111-111111111111"
                ),
                conversation_id=(
                    "22222222-2222-2222-2222-222222222222"
                ),
            )

if __name__ == "__main__":
    unittest.main()