import inspect
import unittest

from app.api.dependencies import (
    get_calendar_write_chat_guard_store,
    get_calendar_write_chat_service,
)
from app.api.v1.chat import send_chat_message
from app.schemas.chat import ChatResponse
from app.services.chat_calendar_write import CalendarWriteChatService


class D83IntegrationSecurityRegressionTests(unittest.TestCase):
    def test_d83_service_has_no_d73_d36_connector_ai_or_automation_authority(self) -> None:
        source = inspect.getsource(CalendarWriteChatService)
        forbidden = (
            "CalendarWriteApprovalService",
            "CalendarWriteApprovalStore",
            "ExecutionApprovalService",
            "ExecutionGuard",
            "CredentialAccessBroker",
            "GoogleCalendarWriteClient",
            "CalendarCreateExecutionService",
            "CalendarUpdateDeleteExecutionService",
            "CrossConnectorContextStore",
            "AutomationApprovalService",
            "AIRuntime",
            ".propose(",
            ".approve(",
            ".authorize(",
            ".claim_approved(",
            ".execute_create(",
            ".execute_update(",
            ".execute_delete(",
            "requests.",
            "httpx.",
            "urllib.",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_d83_dependency_getter_has_no_write_execution_dependency(self) -> None:
        source = inspect.getsource(get_calendar_write_chat_service)
        forbidden = (
            "CalendarWriteApprovalService",
            "get_calendar_write_approval_service",
            "CalendarCreateExecutionService",
            "CalendarUpdateDeleteExecutionService",
            "CredentialAccessBroker",
            "AIRuntime",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

        self.assertIn("settings.oai_owner_timezone", source)
        self.assertIn("conversation_service=conversation_service", source)
        self.assertIn("guard_store=guard_store", source)

    def test_d83_guard_store_is_process_local_only(self) -> None:
        source = inspect.getsource(get_calendar_write_chat_guard_store)
        self.assertIn("@lru_cache", source)
        for token in (
            "Session",
            "Repository",
            "database",
            "CalendarWriteApprovalStore",
            "CredentialAccessBroker",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_d83_route_contains_no_d73_or_write_execution_calls(self) -> None:
        source = inspect.getsource(send_chat_message)
        forbidden = (
            "CalendarWriteApprovalService",
            "CalendarWriteApprovalStore",
            "CalendarCreateExecutionService",
            "CalendarUpdateDeleteExecutionService",
            ".propose(",
            ".approve(",
            ".claim_approved(",
            ".execute_create(",
            ".execute_update(",
            ".execute_delete(",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_d83_route_order_preserves_frozen_read_status_and_generic_boundaries(self) -> None:
        source = inspect.getsource(send_chat_message)
        cross = source.index(
            "if cross_connector_chat_service.is_request(payload.message):"
        )
        clarification = source.index(
            'if clarification_disposition == "handle":'
        )
        status_reservation = source.index("runtime_status_requested = (")
        write_reservation = source.index("calendar_write_requested = (")
        action = source.index(
            "chat_action_bridge.is_action_directive(payload.message)"
        )
        read_guard = source.index(
            "plaintext_calendar_approval_guard = getattr"
        )
        write_guard = source.index(
            "calendar_write_guard_disposition = ("
        )
        write_handle = source.index("if calendar_write_requested:")
        status_handle = source.index("if runtime_status_requested:")
        generic = source.index(
            "command = command_input_pipeline.normalize_chat"
        )

        self.assertLess(cross, clarification)
        self.assertLess(clarification, status_reservation)
        self.assertLess(status_reservation, write_reservation)
        self.assertLess(write_reservation, action)
        self.assertLess(action, read_guard)
        self.assertLess(read_guard, write_guard)
        self.assertLess(write_guard, write_handle)
        self.assertLess(write_handle, status_handle)
        self.assertLess(status_handle, generic)

    def test_chat_response_contract_was_not_repurposed_for_d83_authority(self) -> None:
        fields = ChatResponse.model_fields
        self.assertIn("reply", fields)
        self.assertIn("conversation_id", fields)
        self.assertIn("action", fields)
        # D83 uses the existing response shape and does not add a write
        # approval/execution authority field.
        for forbidden_field in (
            "calendar_write_approval",
            "calendar_write_digest",
            "calendar_write_execution",
            "write_authority",
        ):
            self.assertNotIn(forbidden_field, fields)


if __name__ == "__main__":
    unittest.main()
