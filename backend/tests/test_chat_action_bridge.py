from tests.workspace_fixture import TEST_WORKSPACE_SCOPE

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

from app.api.v1.chat import send_chat_message
from app.contracts.chat_plugin_action import ChatPluginActionBinding
from app.contracts.execution_approval import (
    ExecutionApprovalProposal,
    ExecutionApprovalProposalOutcome,
)
from app.contracts.gmail import (
    GMAIL_ADAPTER_ID,
    GMAIL_OPERATION,
    GmailReadQuery,
)
from app.schemas.chat import ChatRequest
from app.services.chat_action_bridge import (
    _PLAINTEXT_APPROVAL_PHRASES,
    ChatActionBridge,
    GMAIL_STRUCTURED_APPROVAL_REQUIRED_REPLY,
    INVALID_REPLY,
    PENDING_REPLY,
    PROJECT_REQUIRED_REPLY,
    UNAVAILABLE_REPLY,
)
from app.services.chat_plugin_action import ChatPluginActionBindingStore


CONVERSATION_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = UUID("22222222-2222-2222-2222-222222222222")


class FakeConversationService:
    def __init__(self, *, linked_project_id: str | None = None) -> None:
        self.linked_project_id = linked_project_id
        self.begin_calls: list[tuple[object, ...]] = []
        self.complete_calls: list[tuple[str, str]] = []

    def begin_turn(
        self,
        message,
        conversation_id=None,
        project_id=None,
    ):
        self.begin_calls.append(
            (message, conversation_id, project_id)
        )
        project_value = self.linked_project_id
        if conversation_id is None and project_id is not None:
            project_value = str(project_id)
        return (
            SimpleNamespace(
                id=str(CONVERSATION_ID),
                project_id=project_value,
            ),
            [],
        )

    def complete_turn(self, conversation_id: str, reply: str) -> None:
        self.complete_calls.append((conversation_id, reply))


class FakeApprovalService:
    def __init__(self, *, status: str = "pending") -> None:
        self.status = status
        self.calls: list[dict[str, object]] = []

    def propose(self, **kwargs):
        self.calls.append(kwargs)
        if self.status != "pending":
            return ExecutionApprovalProposalOutcome(
                request_id="execution-request",
                status=self.status,
                target_kind=kwargs["target_kind"],
                reason_code=(
                    "capability_not_permitted"
                    if self.status == "rejected"
                    else "tool_adapter_unavailable"
                ),
            )

        now = datetime(2026, 9, 15, tzinfo=timezone.utc)
        proposal = ExecutionApprovalProposal(
            approval_id="approval-1",
            request_id="execution-request",
            target_kind=kwargs["target_kind"],
            adapter_id=kwargs["adapter_id"],
            operation=kwargs["operation"],
            parameters=kwargs["parameters"],
            capability_id="exec.test",
            effect="read",
            data_class="workspace_metadata",
            owner_approval_required=True,
            plan_digest="a" * 64,
            expires_at=now + timedelta(minutes=10),
        )
        return ExecutionApprovalProposalOutcome(
            request_id="execution-request",
            status="pending",
            target_kind=kwargs["target_kind"],
            reason_code="owner_decision_required",
            proposal=proposal,
        )


class ChatActionBridgeTests(unittest.TestCase):
    def build(
        self,
        *,
        linked_project_id: str | None = None,
        approval_status: str = "pending",
        plugin_binding_store: ChatPluginActionBindingStore | None = None,
        gmail_connector_enabled: bool = False,
    ):
        conversations = FakeConversationService(
            linked_project_id=linked_project_id
        )
        approvals = FakeApprovalService(status=approval_status)
        bridge = ChatActionBridge(
            conversation_service=conversations,  # type: ignore[arg-type]
            approval_service=approvals,  # type: ignore[arg-type]
            plugin_binding_store=plugin_binding_store,
            gmail_connector_enabled=gmail_connector_enabled,
        )
        return bridge, conversations, approvals

    def test_detection_requires_exact_action_token_at_start(self) -> None:
        for message in (
            "/action system info",
            "  /action read docs/ARCHITECTURE.md  ",
            "/action",
            "/action\tstat docs",
        ):
            self.assertTrue(
                ChatActionBridge.is_action_directive(message),
                message,
            )

        for message in (
            "please /action system info",
            "example: /action read docs/file.md",
            "/actionable system info",
            "action system info",
            "",
        ):
            self.assertFalse(
                ChatActionBridge.is_action_directive(message),
                message,
            )

    def test_all_v1_directives_map_deterministically(self) -> None:
        bridge, _, approvals = self.build(
            linked_project_id=str(PROJECT_ID)
        )
        cases = (
            (
                "/action echo hello world",
                ("tool", "tool.standard.echo", "echo", {"value": "hello world"}),
            ),
            (
                "/action system info",
                ("tool", "tool.system.info", "get_info", {}),
            ),
            (
                "/action system health",
                ("tool", "tool.system.health", "check", {}),
            ),
            (
                "/action list docs",
                ("tool", "tool.filesystem.list", "list", {"path": "docs"}),
            ),
            (
                "/action stat docs/ARCHITECTURE.md",
                (
                    "tool",
                    "tool.filesystem.stat",
                    "stat",
                    {"path": "docs/ARCHITECTURE.md"},
                ),
            ),
            (
                "/action read docs/ARCHITECTURE.md",
                (
                    "tool",
                    "tool.filesystem.read_text",
                    "read_text",
                    {"path": "docs/ARCHITECTURE.md"},
                ),
            ),
            (
                "/action workspace overview",
                (
                    "module",
                    "module.workspace.overview",
                    "inspect",
                    {},
                ),
            ),
            (
                "/action project snapshot",
                (
                    "module",
                    "module.project.snapshot",
                    "get_snapshot",
                    {"project_id": str(PROJECT_ID)},
                ),
            ),
        )

        for message, expected in cases:
            outcome = bridge.process(message=message)
            call = approvals.calls[-1]
            self.assertEqual(
                (
                    call["target_kind"],
                    call["adapter_id"],
                    call["operation"],
                    call["parameters"],
                ),
                expected,
                message,
            )
            self.assertEqual(outcome.status, "pending_approval")
            self.assertEqual(outcome.reply, PENDING_REPLY)

    def test_filesystem_path_is_forwarded_without_hidden_rewrite(self) -> None:
        bridge, _, approvals = self.build()

        bridge.process(
            message="/action read docs/My File.md"
        )

        self.assertEqual(
            approvals.calls[-1]["parameters"],
            {"path": "docs/My File.md"},
        )

    def test_invalid_directive_persists_deterministic_reply_without_ticket(self) -> None:
        bridge, conversations, approvals = self.build()

        outcome = bridge.process(message="/action launch something")

        self.assertEqual(outcome.status, "rejected")
        self.assertEqual(
            outcome.reason_code,
            "invalid_action_directive",
        )
        self.assertEqual(outcome.reply, INVALID_REPLY)
        self.assertEqual(approvals.calls, [])
        self.assertEqual(
            conversations.complete_calls,
            [(str(CONVERSATION_ID), INVALID_REPLY)],
        )

    def test_project_snapshot_requires_linked_project(self) -> None:
        bridge, conversations, approvals = self.build()

        outcome = bridge.process(
            message="/action project snapshot"
        )

        self.assertEqual(outcome.status, "rejected")
        self.assertEqual(
            outcome.reason_code,
            "project_context_required",
        )
        self.assertEqual(outcome.reply, PROJECT_REQUIRED_REPLY)
        self.assertEqual(approvals.calls, [])
        self.assertEqual(len(conversations.begin_calls), 1)

    def test_new_project_conversation_binds_snapshot_to_selected_project(self) -> None:
        bridge, _, approvals = self.build()

        bridge.process(
            message="/action project snapshot",
            project_id=PROJECT_ID,
        )

        self.assertEqual(
            approvals.calls[-1]["parameters"],
            {"project_id": str(PROJECT_ID)},
        )

    def test_d45_rejection_is_returned_without_execution_semantics(self) -> None:
        bridge, conversations, approvals = self.build(
            approval_status="rejected"
        )

        outcome = bridge.process(
            message="/action system info"
        )

        self.assertEqual(outcome.status, "rejected")
        self.assertEqual(
            outcome.reason_code,
            "capability_not_permitted",
        )
        self.assertEqual(outcome.reply, UNAVAILABLE_REPLY)
        self.assertEqual(len(approvals.calls), 1)
        self.assertEqual(len(conversations.complete_calls), 1)

    def test_d85_natural_gmail_read_maps_to_exact_existing_d77_proposal(self) -> None:
        bridge, _, approvals = self.build(
            gmail_connector_enabled=True,
        )

        outcome = bridge.process(
            message="มีอีเมลล่าสุดอะไรบ้าง"
        )

        self.assertEqual(outcome.status, "pending_approval")
        self.assertEqual(len(approvals.calls), 1)
        call = approvals.calls[0]
        self.assertEqual(call["target_kind"], "module")
        self.assertEqual(call["adapter_id"], GMAIL_ADAPTER_ID)
        self.assertEqual(call["operation"], GMAIL_OPERATION)
        self.assertEqual(call["parameters"], {"mode": "recent"})

    def test_d85_plaintext_gmail_approval_is_non_authoritative_and_binding_stays_pending(self) -> None:
        store = ChatPluginActionBindingStore()
        store.add(
            ChatPluginActionBinding(
                approval_id="gmail-approval",
                conversation_id=CONVERSATION_ID,
                repository_reference=None,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
                gmail_query=GmailReadQuery(mode="recent"),
            )
        )
        bridge, conversations, approvals = self.build(
            plugin_binding_store=store,
            gmail_connector_enabled=True,
        )

        self.assertTrue(
            bridge.is_pending_gmail_plaintext_approval(
                CONVERSATION_ID,
                "อนุมัติครับ",
            )
        )
        outcome = bridge.process_pending_gmail_plaintext_approval(
            message="อนุมัติครับ",
            conversation_id=CONVERSATION_ID,
        )

        self.assertEqual(outcome.status, "rejected")
        self.assertEqual(
            outcome.reason_code,
            "gmail_approval_requires_structured_action",
        )
        self.assertEqual(
            outcome.reply,
            GMAIL_STRUCTURED_APPROVAL_REQUIRED_REPLY,
        )
        self.assertEqual(approvals.calls, [])
        self.assertIsNotNone(store.resolve("gmail-approval"))
        self.assertEqual(
            conversations.complete_calls[-1],
            (
                str(CONVERSATION_ID),
                GMAIL_STRUCTURED_APPROVAL_REQUIRED_REPLY,
            ),
        )

    def test_d85_plaintext_gmail_guard_does_not_match_without_pending_binding(self) -> None:
        bridge, _, _ = self.build(
            plugin_binding_store=ChatPluginActionBindingStore(),
            gmail_connector_enabled=True,
        )
        self.assertFalse(
            bridge.is_pending_gmail_plaintext_approval(
                CONVERSATION_ID,
                "อนุมัติครับ",
            )
        )

    def test_d85_chat_route_stops_plaintext_gmail_approval_before_other_lanes(self) -> None:
        class RouteBridge:
            def __init__(self):
                self.gmail_guard_calls = 0

            def calendar_clarification_disposition(self, *_args):
                return "none"

            def is_action_directive(self, _message):
                return False

            def is_plugin_action_request(self, _message):
                return False

            def is_pending_calendar_plaintext_approval(self, *_args):
                return False

            def is_pending_gmail_plaintext_approval(self, conversation_id, message):
                return (
                    conversation_id == CONVERSATION_ID
                    and message == "อนุมัติครับ"
                )

            def process_pending_gmail_plaintext_approval(self, **_kwargs):
                self.gmail_guard_calls += 1
                return SimpleNamespace(
                    reply=GMAIL_STRUCTURED_APPROVAL_REQUIRED_REPLY,
                    conversation_id=CONVERSATION_ID,
                    status="rejected",
                    reason_code="gmail_approval_requires_structured_action",
                )

        route_bridge = RouteBridge()
        response = send_chat_message(
            workspace_scope=TEST_WORKSPACE_SCOPE,
            request=SimpleNamespace(
                state=SimpleNamespace(request_id="request-1"),
                app=SimpleNamespace(state=SimpleNamespace()),
            ),
            payload=ChatRequest(
                message="อนุมัติครับ",
                conversation_id=CONVERSATION_ID,
            ),
            command_input_pipeline=SimpleNamespace(),
            command_orchestrator=SimpleNamespace(),
            project_update_orchestrator=SimpleNamespace(),
            chat_action_bridge=route_bridge,  # type: ignore[arg-type]
            cross_connector_chat_service=SimpleNamespace(
                is_request=lambda _message: False,
            ),
            calendar_write_chat_service=SimpleNamespace(
                is_request=lambda _message: False,
            ),
            calendar_write_chat_ux_service=SimpleNamespace(),
            conversation_service=SimpleNamespace(),
            runtime_capability_chat_service=SimpleNamespace(
                is_request=lambda _message: False,
            ),
            x_oai_local_request="1",
        )

        self.assertEqual(route_bridge.gmail_guard_calls, 1)
        self.assertEqual(
            response.data.action.reason_code,
            "gmail_approval_requires_structured_action",
        )
        self.assertIsNone(response.data.action.approval)
        self.assertEqual(
            response.data.reply,
            GMAIL_STRUCTURED_APPROVAL_REQUIRED_REPLY,
        )


    def test_d85_plaintext_approval_catalog_includes_spec_phrases(self) -> None:
        self.assertTrue(
            {
                "อนุมัติครับ",
                "approve",
                "approved",
                "ตกลง",
            }.issubset(_PLAINTEXT_APPROVAL_PHRASES)
        )


if __name__ == "__main__":
    unittest.main()
