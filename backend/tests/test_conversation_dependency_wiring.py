import unittest
from unittest.mock import Mock

from app.api.dependencies import get_conversation_service
from app.services.chat import ChatService


class ConversationDependencyWiringTests(unittest.TestCase):
    def test_conversation_service_wires_execution_persistence(
        self,
    ) -> None:
        database_session = Mock()
        chat_service = Mock(spec=ChatService)

        service = get_conversation_service(
            database_session=database_session,
            chat_service=chat_service,
        )

        self.assertIsNotNone(
            service._project_action_execution_persistence_service
        )


if __name__ == "__main__":
    unittest.main()