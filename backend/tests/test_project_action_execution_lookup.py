from tests.workspace_fixture import TEST_WORKSPACE_SCOPE, create_project_action_proposal

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.repositories.project_action_execution_proposals import (
    ProjectActionExecutionProposalRepository,
)
from app.services.project_action_execution_lookup import (
    ProjectActionExecutionLookupService,
)


class ProjectActionExecutionLookupServiceTests(
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

        self.service = ProjectActionExecutionLookupService(
            self.repository
        )

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_get_returns_existing_proposal(
        self,
    ) -> None:
        proposal = create_project_action_proposal(self.repository, self.session,
            project_id=(
                "11111111-1111-1111-1111-111111111111"
            ),
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=1,
            source_action="Run supported action",
            steps=[
                {
                    "sequence": 1,
                    "description": "Run supported action",
                    "capability": "PROJECT_ACTION",
                }
            ],
        )

        self.repository.commit()

        loaded = self.service.get(
            proposal.id,
        )

        self.assertEqual(
            loaded.id,
            proposal.id,
        )