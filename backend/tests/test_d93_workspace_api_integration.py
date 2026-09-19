from __future__ import annotations

import asyncio
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.repositories.conversations import ConversationRepository
from app.schemas.chat import ChatResponse
from app.services.chat import ChatService
from app.services.conversations import (
    ConversationNotFoundError,
    ConversationService,
)
from tests.test_api_standardization import invoke_app


class _StaticProvider:
    def generate_reply(self, *args, **kwargs) -> str:
        return "Scoped reply."


class D93WorkspaceAPIIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

        def override_db():
            session = Session(self.engine)
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = override_db

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.session.close()
        self.engine.dispose()

    def request(self, *args, **kwargs):
        return asyncio.run(invoke_app(*args, **kwargs))

    def test_missing_and_invalid_workspace_fail_closed(self) -> None:
        status_code, _, body = self.request(
            "/api/v1/projects",
            include_workspace=False,
        )
        self.assertEqual(status_code, 400)
        self.assertEqual(body["error"]["code"], "workspace_required")

        status_code, _, body = self.request(
            "/api/v1/projects",
            headers={"X-OAI-Workspace": "Personal"},
        )
        self.assertEqual(status_code, 400)
        self.assertEqual(body["error"]["code"], "workspace_id_invalid")

    def test_project_api_cross_workspace_is_not_found(self) -> None:
        status_code, _, created = self.request(
            "/api/v1/projects",
            method="POST",
            body={
                "title": "Personal API project",
                "objective": "Verify exact D93 API scope.",
            },
            headers={"X-OAI-Workspace": "personal"},
        )
        self.assertEqual(status_code, 201)
        self.assertEqual(created["data"]["workspace_id"], "personal")
        project_id = created["data"]["id"]

        status_code, _, other = self.request(
            f"/api/v1/projects/{project_id}",
            headers={"X-OAI-Workspace": "company"},
        )
        self.assertEqual(status_code, 404)
        self.assertEqual(other["error"]["code"], "PROJECT_NOT_FOUND")

    def test_conversation_service_cannot_continue_other_workspace(self) -> None:
        chat = ChatService(_StaticProvider())
        personal = ConversationService(
            ConversationRepository(
                self.session,
                WorkspaceScope(WorkspaceId.PERSONAL),
            ),
            chat,
            20,
        )
        company = ConversationService(
            ConversationRepository(
                self.session,
                WorkspaceScope(WorkspaceId.COMPANY),
            ),
            chat,
            20,
        )

        personal_result = personal.send_message("Hello personal")
        self.assertEqual(personal.workspace_id, "personal")

        with self.assertRaises(ConversationNotFoundError):
            company.send_message(
                "Cross workspace continuation",
                conversation_id=personal_result.conversation_id,
            )

    def test_chat_response_requires_exact_workspace_truth(self) -> None:
        response = ChatResponse(
            workspace_id="company",
            reply="ok",
            conversation_id="11111111-1111-1111-1111-111111111111",
        )
        self.assertEqual(response.workspace_id, "company")

        with self.assertRaises(Exception):
            ChatResponse(
                workspace_id="Company",
                reply="invalid",
                conversation_id="11111111-1111-1111-1111-111111111111",
            )


if __name__ == "__main__":
    unittest.main()
