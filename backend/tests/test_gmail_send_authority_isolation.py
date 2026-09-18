from __future__ import annotations

import inspect
import unittest
from pathlib import Path

import app.contracts.gmail_send as gmail_send_module
from app.contracts.gmail import (
    GMAIL_ADAPTER_ID,
    GMAIL_CAPABILITY_ID,
    GMAIL_CREDENTIAL_SCOPE,
    GMAIL_OPERATION,
    GMAIL_READ_CREDENTIAL_PROFILE_ID,
)
from app.contracts.gmail_send import (
    GMAIL_SEND_CONTRACT_VERSION,
    GMAIL_SEND_OPERATION,
    GmailSendDraft,
    GmailSendRequest,
)


BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
APP = BACKEND / "app"
FRONTEND = REPO / "frontend"
SEND_CONTRACT = APP / "contracts" / "gmail_send.py"


def production_python_files() -> tuple[Path, ...]:
    return tuple(
        path
        for path in APP.rglob("*.py")
        if path.resolve() != SEND_CONTRACT.resolve()
    )


class GmailSendAuthorityIsolationTests(unittest.TestCase):
    def test_d86_contract_identity_has_no_execution_identity(self) -> None:
        draft = GmailSendDraft(
            recipient="alice@example.com",
            subject="Subject",
            body="Body",
        )
        request = GmailSendRequest(message=draft)

        self.assertEqual(GMAIL_SEND_CONTRACT_VERSION, "1")
        self.assertEqual(GMAIL_SEND_OPERATION, "send_message")
        self.assertEqual(request.contract_version, "1")
        self.assertEqual(request.operation, "send_message")

        for forbidden in (
            "adapter_id",
            "capability_id",
            "credential_profile",
            "credential",
            "oauth_scope",
            "approval_id",
            "write_digest",
            "execution",
            "retry",
        ):
            self.assertFalse(hasattr(draft, forbidden))
            self.assertFalse(hasattr(request, forbidden))

    def test_existing_gmail_read_identity_remains_exact_and_readonly(self) -> None:
        self.assertEqual(GMAIL_ADAPTER_ID, "module.plugin.gmail")
        self.assertEqual(
            GMAIL_CAPABILITY_ID,
            "exec.plugin.gmail.read_messages",
        )
        self.assertEqual(GMAIL_OPERATION, "read_messages")
        self.assertEqual(
            GMAIL_READ_CREDENTIAL_PROFILE_ID,
            "gmail.messages.readonly",
        )
        self.assertEqual(
            GMAIL_CREDENTIAL_SCOPE,
            "https://www.googleapis.com/auth/gmail.readonly",
        )
        self.assertNotEqual(
            GMAIL_CREDENTIAL_SCOPE,
            "https://www.googleapis.com/auth/gmail.send",
        )

    def test_send_contract_has_no_authority_or_external_dependencies(self) -> None:
        source = inspect.getsource(gmail_send_module)
        forbidden = (
            "CredentialAccessBroker",
            "ExecutionPlanner",
            "ExecutionGuard",
            "CommandExecutionCoordinator",
            "PluginRuntime",
            "ModuleAdapter",
            "ToolAdapter",
            "FastAPI",
            "requests.",
            "httpx.",
            "urllib.",
            "googleapiclient",
            "gmail.send",
            ".execute(",
            "app.services",
            "app.api",
            "app.connectors",
            "app.adapters",
        )
        for marker in forbidden:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_send_contract_is_wired_only_into_d87_d88_boundaries(self) -> None:
        """D86 data may flow only through approved D87/D88 pre-provider layers."""
        send_markers = (
            "GmailSendDraft",
            "GmailSendRequest",
        )
        allowed = {
            "app/contracts/gmail_send_approval.py",
            "app/schemas/gmail_send_approvals.py",
            "app/services/gmail_send_approval.py",
            "app/contracts/gmail_send_execution.py",
            "app/connectors/gmail_send.py",
        }
        consumers: set[str] = set()
        for path in production_python_files():
            source = path.read_text(encoding="utf-8-sig")
            if any(marker in source for marker in send_markers):
                consumers.add(
                    str(path.relative_to(BACKEND)).replace("\\", "/")
                )

        self.assertEqual(consumers, allowed)
        for path in consumers:
            self.assertFalse(path.startswith("app/adapters/"))
            if path.startswith("app/connectors/"):
                self.assertEqual(path, "app/connectors/gmail_send.py")
            self.assertFalse(path.startswith("app/plugins/"))
            self.assertFalse(path.startswith("app/runtime/"))
            self.assertFalse(path.startswith("app/api/v1/chat"))

    def test_gmail_send_oauth_scope_is_isolated_to_d88_contract(self) -> None:
        scope = "https://www.googleapis.com/auth/gmail.send"
        offenders: list[str] = []
        for path in APP.rglob("*.py"):
            source = path.read_text(encoding="utf-8-sig")
            if scope in source:
                offenders.append(
                    str(path.relative_to(BACKEND)).replace("\\", "/")
                )
        self.assertEqual(
            offenders,
            ["app/contracts/gmail_send_execution.py"],
        )

    def test_d88_gmail_status_separates_backend_from_chat_send(self) -> None:
        path = APP / "services" / "chat_runtime_capability.py"
        source = path.read_text(encoding="utf-8-sig")
        self.assertIn("สถานะ Gmail ครับ", source)
        self.assertIn("Write/Send backend", source)
        self.assertIn("Write/Send via Chat", source)
        self.assertIn("ยังไม่รองรับ", source)

    def test_frontend_has_no_gmail_send_authority_surface(self) -> None:
        if not FRONTEND.is_dir():
            self.fail("frontend directory is missing")

        forbidden_markers = (
            "GmailSendRequest",
            "GmailSendDraft",
            "gmail_send",
            "gmail.send",
            "send_message",
        )
        offenders: list[str] = []
        for suffix in ("*.ts", "*.tsx"):
            for path in FRONTEND.rglob(suffix):
                if any(
                    part in {"node_modules", ".next"}
                    for part in path.parts
                ):
                    continue
                source = path.read_text(encoding="utf-8-sig")
                if any(marker in source for marker in forbidden_markers):
                    offenders.append(str(path.relative_to(REPO)))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
