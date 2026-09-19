from tests.workspace_fixture import TEST_WORKSPACE_SCOPE, create_project_action_proposal

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.repositories.project_action_execution_proposals import (
    ProjectActionExecutionProposalRepository,
)
from app.services.project_action_execution_durable_approval import (
    ProjectActionExecutionDurableApprovalService,
)


class ProjectActionExecutionDurableApprovalTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
        )
        Base.metadata.create_all(self.engine)

        self.session = Session(self.engine)

        self.repository = (
            ProjectActionExecutionProposalRepository(self.session, TEST_WORKSPACE_SCOPE)
        )

        self.service = (
            ProjectActionExecutionDurableApprovalService(
                self.repository
            )
        )

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_owner_approval_updates_pending_record_without_execution(
        self,
    ) -> None:
        proposal = create_project_action_proposal(self.repository, self.session,
            project_id=(
                "11111111-1111-1111-1111-111111111111"
            ),
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=30,
            source_action="Run acceptance tests",
            steps=[
                {
                    "sequence": 1,
                    "description": "Run acceptance tests",
                }
            ],
        )
        self.repository.commit()

        result = self.service.approve(proposal.id)

        self.assertEqual(
            result.status,
            "APPROVED",
        )
        self.assertTrue(result.approved)
        self.assertFalse(result.executed)

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(
            loaded.status,
            "APPROVED",
        )
        self.assertTrue(loaded.approved)
        self.assertFalse(loaded.executed)

    def test_owner_rejection_updates_pending_record_without_execution(
        self,
    ) -> None:
        proposal = create_project_action_proposal(self.repository, self.session,
            project_id=(
                "11111111-1111-1111-1111-111111111111"
            ),
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=31,
            source_action="Run acceptance tests",
            steps=[
                {
                    "sequence": 1,
                    "description": "Run acceptance tests",
                }
            ],
        )
        self.repository.commit()

        result = self.service.reject(proposal.id)

        self.assertEqual(
            result.status,
            "REJECTED",
        )
        self.assertFalse(result.approved)
        self.assertFalse(result.executed)

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(
            loaded.status,
            "REJECTED",
        )
        self.assertFalse(loaded.approved)
        self.assertFalse(loaded.executed)

    def test_approved_proposal_cannot_be_rejected_later(
        self,
    ) -> None:
        proposal = create_project_action_proposal(self.repository, self.session,
            project_id=(
                "11111111-1111-1111-1111-111111111111"
            ),
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=32,
            source_action="Run acceptance tests",
            steps=[
                {
                    "sequence": 1,
                    "description": "Run acceptance tests",
                }
            ],
        )
        self.repository.commit()

        approved = self.service.approve(proposal.id)

        self.assertEqual(
            approved.status,
            "APPROVED",
        )

        with self.assertRaises(ValueError):
            self.service.reject(proposal.id)

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(
            loaded.status,
            "APPROVED",
        )
        self.assertTrue(loaded.approved)
        self.assertFalse(loaded.executed)

    def test_rejected_proposal_cannot_be_approved_later(
        self,
    ) -> None:
        proposal = create_project_action_proposal(self.repository, self.session,
            project_id=(
                "11111111-1111-1111-1111-111111111111"
            ),
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=33,
            source_action="Run acceptance tests",
            steps=[
                {
                    "sequence": 1,
                    "description": "Run acceptance tests",
                }
            ],
        )
        self.repository.commit()

        rejected = self.service.reject(proposal.id)

        self.assertEqual(
            rejected.status,
            "REJECTED",
        )

        with self.assertRaises(ValueError):
            self.service.approve(proposal.id)

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(
            loaded.status,
            "REJECTED",
        )
        self.assertFalse(loaded.approved)
        self.assertFalse(loaded.executed)


if __name__ == "__main__":
    unittest.main()