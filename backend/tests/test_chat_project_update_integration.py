import asyncio
import os
import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.orm import sessionmaker
from uuid import UUID

from app.api.dependencies import (
    get_conversation_service,
    get_project_update_turn_orchestrator,
)
from app.core.config import get_settings
from app.db.session import create_database_engine
from app.main import app
from app.repositories.conversations import ConversationRepository
from app.repositories.project_update_proposals import (
    ProjectUpdateProposalRepository,
)
from app.repositories.projects import ProjectRepository
from app.schemas.projects import CreateProjectRequest
from app.services.chat import ChatService
from app.services.conversations import ConversationService
from app.services.project_context import (
    ProjectContextReader,
    ProjectContextResolver,
)
from app.services.project_update_generation import (
    ProjectUpdateProposalGenerator,
)
from app.services.project_update_orchestrator import (
    ProjectUpdateTurnOrchestrator,
)
from app.services.project_update_proposals import (
    ProjectUpdateProposalService,
)
from app.services.projects import ProjectService
from tests.test_api_standardization import invoke_app
from app.api.dependencies import (
    get_conversation_service,
    get_project_update_proposal_service,
    get_project_update_turn_orchestrator,
)

class StaticProvider:
    def generate_reply(self, *args, **kwargs) -> str:
        return "Acknowledged."


class ChatProjectUpdateIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = (
            Path(self.temporary_directory.name) / "chat-project-update.db"
        )

        self.previous_url = os.environ.get("OAI_DATABASE_URL")
        os.environ["OAI_DATABASE_URL"] = (
            f"sqlite:///{self.database_path.as_posix()}"
        )
        get_settings.cache_clear()

        command.upgrade(
            Config(
                str(
                    Path(__file__).resolve().parents[2]
                    / "alembic.ini"
                )
            ),
            "head",
        )

        self.engine = create_database_engine(
            os.environ["OAI_DATABASE_URL"]
        )
        self.Session = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
        )
        self.session = self.Session()

        self.projects = ProjectService(
            ProjectRepository(self.session)
        )

        self.conversations = ConversationService(
            repository=ConversationRepository(self.session),
            chat_service=ChatService(StaticProvider()),
            context_message_limit=20,
            project_context_resolver=ProjectContextResolver(
                ProjectContextReader(self.session)
            ),
        )

        self.proposals = ProjectUpdateProposalService(
            repository=ProjectUpdateProposalRepository(self.session),
            conversation_repository=ConversationRepository(self.session),
            project_service=self.projects,
        )

        self.orchestrator = ProjectUpdateTurnOrchestrator(
            generator=ProjectUpdateProposalGenerator(),
            proposal_service=self.proposals,
        )

        app.dependency_overrides[
            get_conversation_service
        ] = lambda: self.conversations

        app.dependency_overrides[
            get_project_update_turn_orchestrator
        ] = lambda: self.orchestrator

        app.dependency_overrides[
            get_project_update_proposal_service
        ] = lambda: self.proposals

    def test_chat_surfaces_project_action_plan(
        self,
    ) -> None:
        project = self.projects.create(
            CreateProjectRequest(
                title="Project action planning API",
                objective="Surface owner-controlled Project action plans.",
            )
        )

        self.projects.apply_progress_update(
            project.id,
            expected_revision=1,
            current_summary="Project Action Planning is ready.",
            next_action="Run acceptance tests",
            change_note="Prepare Project Action Planning API test.",
        )

        status_code, _, response = asyncio.run(
            invoke_app(
                "/api/v1/chat",
                method="POST",
                body={
                    "message": "How should we proceed?",
                    "project_id": str(project.id),
                },
            )
        )

        self.assertEqual(status_code, 200)

        action_plan = response["data"]["project_action_plan"]

        self.assertIsNotNone(action_plan)
        self.assertEqual(
            action_plan["status"],
            "plan_available",
        )
        self.assertEqual(
            action_plan["project_revision"],
            2,
        )
        self.assertEqual(
            action_plan["source_action"],
            "Run acceptance tests",
        )
        self.assertTrue(
            action_plan["owner_approval_required"]
        )
        self.assertGreaterEqual(
            len(action_plan["steps"]),
            1,
        )
        self.assertEqual(
            action_plan["steps"][0]["sequence"],
            1,
        )

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.session.close()
        self.engine.dispose()

        if self.previous_url is None:
            os.environ.pop("OAI_DATABASE_URL", None)
        else:
            os.environ["OAI_DATABASE_URL"] = self.previous_url

        get_settings.cache_clear()
        self.temporary_directory.cleanup()

    def test_explicit_progress_chat_creates_pending_proposal_without_mutating_project(
        self,
    ) -> None:
        project = self.projects.create(
            CreateProjectRequest(
                title="Chat integration",
                objective="Generate reviewed Project updates.",
            )
        )

        status_code, _, response = asyncio.run(
            invoke_app(
                "/api/v1/chat",
                method="POST",
                body={
                    "message": "Progress: Chat proposal integration completed.",
                    "project_id": str(project.id),
                },
            )
        )

        self.assertEqual(status_code, 200)
        surfaced = response["data"]["project_update_proposal"]

        self.assertIsNotNone(surfaced)
        self.assertEqual(surfaced["status"], "PENDING")
        self.assertEqual(
            surfaced["project_id"],
            str(project.id),
        )
        self.assertEqual(
            surfaced["conversation_id"],
            response["data"]["conversation_id"],
        )
        self.assertEqual(surfaced["base_revision"], 1)
        self.assertEqual(
            surfaced["proposed_summary"],
            "Chat proposal integration completed.",
        )

        conversation_id = UUID(response["data"]["conversation_id"])

        proposals = self.proposals.list_for_project(
            project.id,
            status="PENDING",
        )

        self.assertEqual(len(proposals.items), 1)

        proposal = proposals.items[0]

        self.assertEqual(
            proposal.conversation_id,
            conversation_id,
        )
        self.assertEqual(proposal.project_id, project.id)
        self.assertEqual(proposal.base_revision, 1)
        self.assertEqual(
            proposal.proposed_summary,
            "Chat proposal integration completed.",
        )
        self.assertEqual(proposal.status, "PENDING")

        current = self.projects.get(project.id)

        self.assertEqual(current.current_revision, 1)
        self.assertIsNone(current.current_summary)
    def test_chat_without_project_does_not_create_proposal(self) -> None:
        status_code, _, response = asyncio.run(
            invoke_app(
                "/api/v1/chat",
                method="POST",
                body={
                    "message": "Progress: This conversation has no Project.",
                },
            )
        )

        self.assertEqual(status_code, 200)
        self.assertIn("conversation_id", response["data"])
        self.assertIsNone(
    response["data"]["project_action_analysis"]
)
    def test_ordinary_project_chat_does_not_create_proposal(self) -> None:
        project = self.projects.create(
            CreateProjectRequest(
                title="Ordinary chat",
                objective="Do not infer progress from ordinary conversation.",
            )
        )

        status_code, _, response = asyncio.run(
            invoke_app(
                "/api/v1/chat",
                method="POST",
                body={
                    "message": "What should we work on next?",
                    "project_id": str(project.id),
                },
            )
        )

        self.assertEqual(status_code, 200)
        self.assertIsNone(
            response["data"]["project_update_proposal"]
        )

        proposals = self.proposals.list_for_project(
            project.id,
            status="PENDING",
        )

        self.assertEqual(len(proposals.items), 0)

    def test_existing_project_conversation_can_create_proposal_without_resending_project_id(
        self,
    ) -> None:
        project = self.projects.create(
            CreateProjectRequest(
                title="Existing conversation",
                objective="Preserve immutable Project association.",
            )
        )

        status_code, _, first = asyncio.run(
            invoke_app(
                "/api/v1/chat",
                method="POST",
                body={
                    "message": "Start the Project discussion.",
                    "project_id": str(project.id),
                },
            )
        )

        self.assertEqual(status_code, 200)

        conversation_id = first["data"]["conversation_id"]

        status_code, _, response = asyncio.run(
            invoke_app(
                "/api/v1/chat",
                method="POST",
                body={
                    "message": "Progress: Existing conversation wiring completed.",
                    "conversation_id": conversation_id,
                },
            )
        )

        self.assertEqual(status_code, 200)

        surfaced = response["data"]["project_update_proposal"]

        self.assertIsNotNone(surfaced)
        self.assertEqual(surfaced["status"], "PENDING")
        self.assertEqual(
            surfaced["project_id"],
            str(project.id),
        )
        self.assertEqual(
            surfaced["conversation_id"],
            conversation_id,
        )
        self.assertEqual(surfaced["base_revision"], 1)
        self.assertEqual(
            surfaced["proposed_summary"],
            "Existing conversation wiring completed.",
        )
        proposals = self.proposals.list_for_project(
            project.id,
            status="PENDING",
        )

        self.assertEqual(len(proposals.items), 1)

        proposal = proposals.items[0]

        self.assertEqual(proposal.project_id, project.id)
        self.assertEqual(
            proposal.conversation_id,
            UUID(conversation_id),
        )
        self.assertEqual(proposal.base_revision, 1)
        self.assertEqual(
            proposal.proposed_summary,
            "Existing conversation wiring completed.",
        )

        current = self.projects.get(project.id)

        self.assertEqual(current.current_revision, 1)
        self.assertIsNone(current.current_summary)
    def test_surfaced_chat_proposal_can_be_approved_by_owner(self) -> None:
        project = self.projects.create(
            CreateProjectRequest(
                title="Owner approval",
                objective="Approve a surfaced chat proposal.",
            )
        )

        status_code, _, chat_response = asyncio.run(
            invoke_app(
                "/api/v1/chat",
                method="POST",
                body={
                    "message": "Progress: Owner-approved integration completed.",
                    "project_id": str(project.id),
                },
            )
        )

        self.assertEqual(status_code, 200)

        surfaced = chat_response["data"]["project_update_proposal"]

        self.assertIsNotNone(surfaced)
        self.assertEqual(surfaced["status"], "PENDING")

        proposal_id = surfaced["id"]

        current = self.projects.get(project.id)

        self.assertEqual(current.current_revision, 1)
        self.assertIsNone(current.current_summary)

        status_code, _, approved = asyncio.run(
            invoke_app(
                f"/api/v1/project-update-proposals/{proposal_id}/approve",
                method="POST",
            )
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(approved["data"]["id"], proposal_id)
        self.assertEqual(approved["data"]["status"], "APPLIED")
        self.assertEqual(approved["data"]["applied_revision"], 2)

        current = self.projects.get(project.id)

        self.assertEqual(current.current_revision, 2)
        self.assertEqual(
            current.current_summary,
            "Owner-approved integration completed.",
      )

    def test_surfaced_chat_proposal_can_be_rejected_without_mutating_project(
        self,
    ) -> None:
        project = self.projects.create(
            CreateProjectRequest(
                title="Owner rejection",
                objective="Reject a surfaced chat proposal safely.",
            )
        )

        status_code, _, chat_response = asyncio.run(
            invoke_app(
                "/api/v1/chat",
                method="POST",
                body={
                    "message": "Progress: This proposal should be rejected.",
                    "project_id": str(project.id),
                },
            )
        )

        self.assertEqual(status_code, 200)

        surfaced = chat_response["data"]["project_update_proposal"]

        self.assertIsNotNone(surfaced)
        self.assertEqual(surfaced["status"], "PENDING")

        proposal_id = surfaced["id"]

        current = self.projects.get(project.id)

        self.assertEqual(current.current_revision, 1)
        self.assertIsNone(current.current_summary)

        status_code, _, rejected = asyncio.run(
            invoke_app(
                f"/api/v1/project-update-proposals/{proposal_id}/reject",
                method="POST",
            )
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(rejected["data"]["id"], proposal_id)
        self.assertEqual(rejected["data"]["status"], "REJECTED")
        self.assertIsNone(rejected["data"]["applied_revision"])

        current = self.projects.get(project.id)

        self.assertEqual(current.current_revision, 1)
        self.assertIsNone(current.current_summary)
        self.assertIsNone(current.next_action)
    def test_chat_surfaces_project_action_analysis(
        self,
    ) -> None:
        project = self.projects.create(
            CreateProjectRequest(
                title="Project action API",
                objective="Surface owner-controlled Project actions.",
            )
        )

        self.projects.apply_progress_update(
    project.id,
    expected_revision=1,
    current_summary="Project Action Intelligence is ready.",
    next_action="Run acceptance tests",
    change_note="Prepare Project Action Intelligence API test.",
)

        status_code, _, response = asyncio.run(
            invoke_app(
                "/api/v1/chat",
                method="POST",
                body={
                    "message": "What should we do next?",
                    "project_id": str(project.id),
                },
            )
        )

        self.assertEqual(status_code, 200)

        action_analysis = response["data"]["project_action_analysis"]

        self.assertIsNotNone(action_analysis)
        self.assertEqual(
            action_analysis["status"],
            "suggestion_available",
        )
        self.assertTrue(
            action_analysis["owner_approval_required"]
        )
        self.assertEqual(
            action_analysis["suggested_actions"][0]["description"],
            "Run acceptance tests",
        )

if __name__ == "__main__":
    unittest.main()
