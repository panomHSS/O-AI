import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.repositories.conversations import ConversationRepository
from app.repositories.project_action_execution_proposals import (
    ProjectActionExecutionProposalRepository,
)
from app.repositories.projects import ProjectRepository
from app.services.chat import ChatService
from app.services.conversations import ConversationService
from app.services.project_action_execution_persistence import (
    ProjectActionExecutionPersistenceService,
)
from app.services.project_context import (
    ProjectContextReader,
    ProjectContextResolver,
)


class StaticProvider:
    def generate_reply(self, *args, **kwargs) -> str:
        return "Acknowledged."


class ConversationProjectActionExecutionDurabilityTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
        )
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

        self.conversation_repository = (
            ConversationRepository(self.session)
        )
        self.project_repository = ProjectRepository(
            self.session
        )
        self.execution_repository = (
            ProjectActionExecutionProposalRepository(
                self.session
            )
        )

        self.service = ConversationService(
            repository=self.conversation_repository,
            chat_service=ChatService(StaticProvider()),
            context_message_limit=20,
            project_context_resolver=ProjectContextResolver(
                ProjectContextReader(self.session)
            ),
            project_action_execution_persistence_service=(
                ProjectActionExecutionPersistenceService(
                    self.execution_repository
                )
            ),
        )

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_project_chat_persists_execution_proposal(
        self,
    ) -> None:
        project = self.project_repository.create(
            title="Durable execution integration",
            objective=(
                "Persist owner-reviewed Project action "
                "execution proposals."
            ),
        )
        project.current_summary = (
            "Project action planning is complete."
        )
        project.next_action = "Run acceptance tests"
        project.current_revision = 17
        self.project_repository.commit()

        result = self.service.send_message(
            "How should we proceed?",
            project_id=project.id,
        )

        self.assertIsNotNone(
            result.project_action_execution_proposal
        )

        records = self.execution_repository.list_for_project(
            project.id
        )

        self.assertEqual(len(records), 1)

        record = records[0]

        self.assertEqual(
            record.project_id,
            project.id,
        )
        self.assertEqual(
            record.conversation_id,
            str(result.conversation_id),
        )
        self.assertEqual(
            record.project_revision,
            17,
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


if __name__ == "__main__":
    unittest.main()