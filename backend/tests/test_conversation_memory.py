import asyncio
import json
import tempfile
import time
import unittest
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session, sessionmaker

from fastapi import Depends

from app.api.dependencies import get_chat_service, get_conversation_service
from app.db.session import create_database_engine, get_db, initialize_database
from app.main import app
from app.models.message import Message
from app.repositories.conversations import ConversationRepository
from app.services.chat import ChatProviderError, ChatService
from app.services.conversations import ConversationService

from test_api_standardization import invoke_app


class RecordingProvider:
    def __init__(self) -> None:
        self.inputs: list[str] = []
        self.should_fail = False

    def generate_reply(self, message: str) -> str:
        self.inputs.append(message)
        if self.should_fail:
            raise ChatProviderError("Chat is temporarily unavailable. Please try again later.")
        return f"Reply: {message.splitlines()[-1]}"


class ConversationMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "oai.db"
        self.engine = create_database_engine(f"sqlite:///{self.database_path.as_posix()}")
        initialize_database(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.provider = RecordingProvider()

        def test_database_session():
            session = self.Session()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = test_database_session
        app.dependency_overrides[get_chat_service] = lambda: ChatService(self.provider)

        def test_conversation_service(database_session: Session = Depends(get_db)) -> ConversationService:
            return ConversationService(ConversationRepository(database_session), ChatService(self.provider), context_message_limit=2)

        app.dependency_overrides[get_conversation_service] = test_conversation_service

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.engine.dispose()
        self.temporary_directory.cleanup()

    def request(self, *args, **kwargs):
        return asyncio.run(invoke_app(*args, **kwargs))

    def send_message(self, message: str, conversation_id: str | None = None):
        body = {"message": message}
        if conversation_id:
            body["conversation_id"] = conversation_id
        return self.request("/api/v1/chat", method="POST", body=body)

    def get_detail(self, conversation_id: str):
        return self.request(f"/api/v1/conversations/{conversation_id}")

    def test_table_initialization(self) -> None:
        self.assertTrue({"conversations", "messages"}.issubset(set(inspect(self.engine).get_table_names())))

    def test_automatic_creation_uses_uuid_and_title(self) -> None:
        status_code, _, body = self.send_message("  A reliable first title  ")
        self.assertEqual(status_code, 200)
        conversation_id = body["data"]["conversation_id"]
        UUID(conversation_id)
        status_code, _, detail = self.get_detail(conversation_id)
        self.assertEqual(status_code, 200)
        self.assertEqual(detail["data"]["title"], "A reliable first title")

    def test_title_is_truncated(self) -> None:
        status_code, _, body = self.send_message("x" * 200)
        self.assertEqual(status_code, 200)
        _, _, detail = self.get_detail(body["data"]["conversation_id"])
        self.assertEqual(len(detail["data"]["title"]), 80)

    def test_user_and_assistant_messages_are_persisted(self) -> None:
        _, _, body = self.send_message("Hello")
        _, _, detail = self.get_detail(body["data"]["conversation_id"])
        self.assertEqual([(item["role"], item["content"]) for item in detail["data"]["messages"]], [("user", "Hello"), ("assistant", "Reply: Hello")])

    def test_context_is_bounded_and_chronological(self) -> None:
        _, _, first = self.send_message("first")
        conversation_id = first["data"]["conversation_id"]
        self.send_message("second", conversation_id)
        self.send_message("third", conversation_id)
        provider_input = self.provider.inputs[-1]
        self.assertIn("user: second", provider_input)
        self.assertIn("assistant: Reply: second", provider_input)
        self.assertNotIn("user: first", provider_input)
        self.assertLess(provider_input.index("user: second"), provider_input.index("assistant: Reply: second"))

    def test_existing_conversation_continues(self) -> None:
        _, _, first = self.send_message("first")
        conversation_id = first["data"]["conversation_id"]
        status_code, _, second = self.send_message("second", conversation_id)
        self.assertEqual(status_code, 200)
        self.assertEqual(second["data"]["conversation_id"], conversation_id)
        _, _, detail = self.get_detail(conversation_id)
        self.assertEqual(len(detail["data"]["messages"]), 4)

    def test_updated_at_changes_when_messages_are_stored(self) -> None:
        _, _, first = self.send_message("first")
        conversation_id = first["data"]["conversation_id"]
        _, _, before = self.get_detail(conversation_id)
        time.sleep(0.002)
        self.send_message("second", conversation_id)
        _, _, after = self.get_detail(conversation_id)
        self.assertGreater(after["data"]["updated_at"], before["data"]["updated_at"])

    def test_listing_is_newest_first(self) -> None:
        _, _, first = self.send_message("first")
        _, _, second = self.send_message("second")
        self.send_message("first again", first["data"]["conversation_id"])
        status_code, _, listing = self.request("/api/v1/conversations")
        self.assertEqual(status_code, 200)
        self.assertEqual(listing["data"][0]["id"], first["data"]["conversation_id"])
        self.assertEqual(listing["data"][1]["id"], second["data"]["conversation_id"])

    def test_detail_retrieval_and_request_id_preservation(self) -> None:
        _, _, body = self.send_message("Hello")
        status_code, headers, detail = self.request(f"/api/v1/conversations/{body['data']['conversation_id']}", headers={"X-Request-ID": "conversation-detail"})
        self.assertEqual(status_code, 200)
        self.assertEqual(headers["x-request-id"], "conversation-detail")
        self.assertTrue(detail["success"])

    def test_deletion_cascades_to_messages(self) -> None:
        _, _, body = self.send_message("Hello")
        conversation_id = body["data"]["conversation_id"]
        status_code, _, deleted = self.request(f"/api/v1/conversations/{conversation_id}", method="DELETE")
        self.assertEqual(status_code, 200)
        self.assertEqual(deleted["data"]["conversation_id"], conversation_id)
        with self.Session() as session:
            self.assertEqual(session.scalar(select(func.count(Message.id))), 0)

    def test_invalid_uuid_uses_standard_error(self) -> None:
        status_code, _, body = self.request("/api/v1/conversations/not-a-uuid")
        self.assertEqual(status_code, 422)
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")

    def test_missing_conversation_uses_standard_error(self) -> None:
        status_code, _, body = self.request(f"/api/v1/conversations/{uuid4()}")
        self.assertEqual(status_code, 404)
        self.assertEqual(body["error"]["code"], "CONVERSATION_NOT_FOUND")

    def test_provider_failure_keeps_only_the_user_message(self) -> None:
        self.provider.should_fail = True
        status_code, _, body = self.send_message("audit this user message")
        self.assertEqual(status_code, 502)
        self.assertEqual(body["error"]["code"], "CHAT_PROVIDER_UNAVAILABLE")
        _, _, listing = self.request("/api/v1/conversations")
        conversation_id = listing["data"][0]["id"]
        _, _, detail = self.get_detail(conversation_id)
        self.assertEqual([(message["role"], message["content"]) for message in detail["data"]["messages"]], [("user", "audit this user message")])
