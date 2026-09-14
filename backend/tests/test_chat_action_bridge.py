import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

from app.contracts.execution_approval import (
    ExecutionApprovalProposal,
    ExecutionApprovalProposalOutcome,
)
from app.services.chat_action_bridge import (
    ChatActionBridge,
    INVALID_REPLY,
    PENDING_REPLY,
    PROJECT_REQUIRED_REPLY,
    UNAVAILABLE_REPLY,
)


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
    ):
        conversations = FakeConversationService(
            linked_project_id=linked_project_id
        )
        approvals = FakeApprovalService(status=approval_status)
        bridge = ChatActionBridge(
            conversation_service=conversations,  # type: ignore[arg-type]
            approval_service=approvals,  # type: ignore[arg-type]
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


if __name__ == "__main__":
    unittest.main()
