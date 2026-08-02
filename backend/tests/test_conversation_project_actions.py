import unittest
from uuid import uuid4

from app.services.chat import ChatService
from app.services.conversations import ConversationService
from app.services.project_actions import ProjectActionService
from app.services.project_context import ProjectContext


class StaticProvider:
    def generate_reply(self, *args, **kwargs) -> str:
        return "Acknowledged."


class FakeConversation:
    def __init__(self, project_id: str) -> None:
        self.id = str(uuid4())
        self.project_id = project_id


class FakeConversationRepository:
    def __init__(self, conversation: FakeConversation) -> None:
        self.conversation = conversation

    def recent_messages(self, conversation_id, limit):
        return []

    def add_message(self, conversation, role, content):
        return None

    def commit(self):
        return None

    def rollback(self):
        return None


class StaticProjectContextResolver:
    def __init__(self, context: ProjectContext) -> None:
        self.context = context

    def resolve(
        self,
        project_id: str | None,
    ) -> ProjectContext | None:
        if project_id is None:
            return None

        return self.context

class StubConversationService(ConversationService):
    def __init__(
        self,
        conversation: FakeConversation,
        project_context: ProjectContext,
    ) -> None:
        super().__init__(
            repository=FakeConversationRepository(conversation),
            chat_service=ChatService(StaticProvider()),
            context_message_limit=20,
            project_context_resolver=StaticProjectContextResolver(
                project_context
            ),
            project_action_service=ProjectActionService(),
        )
        self._conversation = conversation

    def begin_turn(
        self,
        message,
        conversation_id=None,
        project_id=None,
    ):
        return self._conversation, []

    def complete_turn(self, conversation_id, reply):
        return None


class ConversationProjectActionTests(unittest.TestCase):
    def test_project_next_action_is_analyzed_for_chat_turn(
        self,
    ) -> None:
        project_id = uuid4()

        conversation = FakeConversation(str(project_id))

        context = ProjectContext(
            title="Action integration",
            objective="Expose Project actions through conversation.",
            status="ACTIVE",
            current_summary="Core action analysis is complete.",
            next_action="Run integration tests",
            current_revision=9,
        )

        service = StubConversationService(
            conversation,
            context,
        )

        result = service.send_message("What should we do next?")

        self.assertIsNotNone(result.project_action_analysis)
        self.assertEqual(
            result.project_action_analysis.status,
            "suggestion_available",
        )
        self.assertEqual(
            result.project_action_analysis.project_revision,
            9,
        )
        self.assertEqual(
            result.project_action_analysis.suggested_actions[0].description,
            "Run integration tests",
        )
    def test_chat_without_project_has_no_project_action_analysis(
        self,
    ) -> None:
        project_id = uuid4()

        conversation = FakeConversation(str(project_id))

        context = ProjectContext(
            title="Temporary context",
            objective="Context should not be used without a Project.",
            status="ACTIVE",
            current_summary=None,
            next_action="This must not surface",
            current_revision=1,
        )

        service = StubConversationService(
            conversation,
            context,
        )

        conversation.project_id = None

        result = service.send_message("Hello")

        self.assertIsNone(result.project_id)
        self.assertIsNone(result.project_action_analysis)

    def test_paused_project_does_not_surface_action_through_conversation(
        self,
    ) -> None:
        project_id = uuid4()

        conversation = FakeConversation(str(project_id))

        context = ProjectContext(
            title="Paused integration",
            objective="Preserve lifecycle safety through conversation.",
            status="PAUSED",
            current_summary="Work is temporarily paused.",
            next_action="Continue implementation",
            current_revision=10,
        )

        service = StubConversationService(
            conversation,
            context,
        )

        result = service.send_message("What should we do next?")

        self.assertIsNotNone(result.project_action_analysis)
        self.assertEqual(
            result.project_action_analysis.status,
            "no_explicit_action",
        )
        self.assertEqual(
            result.project_action_analysis.project_revision,
            10,
        )
        self.assertFalse(
            result.project_action_analysis.owner_approval_required
        )
        self.assertEqual(
            result.project_action_analysis.suggested_actions,
            [],
        )


if __name__ == "__main__":
    unittest.main()