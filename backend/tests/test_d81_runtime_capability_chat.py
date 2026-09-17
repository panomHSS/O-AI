import inspect
import unittest

from app.schemas.diagnostics import (
    AutomationDiagnostics,
    CrossConnectorAIDiagnostics,
    ExecutionAuditDiagnostics,
    GmailDiagnostics,
    GoogleCalendarDiagnostics,
    RuntimeCapabilityDiagnostics,
    RuntimeDiagnosticsResponse,
)
from app.services.chat_runtime_capability import (
    RuntimeCapabilityResponseComposer,
    RuntimeCapabilityStatusIntent,
    RuntimeCapabilityStatusIntentRouter,
)


def snapshot() -> RuntimeDiagnosticsResponse:
    return RuntimeDiagnosticsResponse(
        service="O-AI",
        environment="test",
        database_revision="0011_test",
        execution_audit=ExecutionAuditDiagnostics(status="ok"),
        runtime=RuntimeCapabilityDiagnostics(
            implemented=True,
            status_chat_routable=False,
            execution_authority=False,
        ),
        google_calendar=GoogleCalendarDiagnostics(
            status="connected",
            connector_enabled=True,
            configuration_present=True,
            read_implemented=True,
            read_chat_routable=True,
            write_backend_implemented=True,
            write_chat_routable=False,
            execution_authority=False,
        ),
        gmail=GmailDiagnostics(
            status="connected",
            connector_enabled=True,
            configuration_present=True,
            read_implemented=True,
            read_chat_routable=True,
            write_implemented=False,
            write_chat_routable=False,
            execution_authority=False,
        ),
        cross_connector_ai=CrossConnectorAIDiagnostics(
            enabled=True,
            implemented=True,
            chat_routable=True,
            execution_authority=False,
        ),
        automation=AutomationDiagnostics(
            enabled=True,
            local_reminder_implemented=True,
            local_reminder_chat_routable=False,
            connector_actions_implemented=False,
            ai_actions_implemented=False,
            execution_authority=False,
        ),
    )


class D81RuntimeCapabilityStatusIntentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.router = RuntimeCapabilityStatusIntentRouter()

    def test_required_thai_status_phrases(self) -> None:
        cases = {
            "/status": "system",
            "สถานะระบบ": "system",
            "ระบบพร้อมไหม": "system",
            "สถานะ O-AI": "system",
            "ตอนนี้ O-AI ทำอะไรได้บ้าง": "system",
            "O-AI รองรับอะไรบ้างตอนนี้": "system",
            "สถานะ Calendar": "calendar",
            "สถานะ Google Calendar": "calendar",
            "สถานะ Gmail": "gmail",
            "สถานะ Automation": "automation",
        }
        for message, target in cases.items():
            with self.subTest(message=message):
                intent = self.router.classify(message)
                self.assertIsNotNone(intent)
                assert intent is not None
                self.assertEqual(intent.target, target)
                self.assertEqual(intent.language, "th")

    def test_required_english_status_phrases(self) -> None:
        cases = {
            "what is the system status": "system",
            "calendar status": "calendar",
            "gmail status": "gmail",
            "automation status": "automation",
            "what can O-AI do now": "system",
        }
        for message, target in cases.items():
            with self.subTest(message=message):
                intent = self.router.classify(message)
                self.assertIsNotNone(intent)
                assert intent is not None
                self.assertEqual(intent.target, target)
                self.assertEqual(intent.language, "en")

    def test_whitespace_and_case_normalization_remain_bounded(self) -> None:
        intent = self.router.classify("  GMAIL   STATUS  ")
        self.assertEqual(
            intent,
            RuntimeCapabilityStatusIntent(target="gmail", language="en"),
        )

    def test_quoted_example_and_prefixed_text_are_rejected(self) -> None:
        for message in (
            '"สถานะระบบ"',
            "'gmail status'",
            "ตัวอย่าง: สถานะระบบ",
            "example: calendar status",
            "ช่วยตอบว่า สถานะ Gmail",
            "ข้อความนี้คือ /status",
        ):
            with self.subTest(message=message):
                self.assertIsNone(self.router.classify(message))

    def test_existing_action_and_content_requests_are_not_hijacked(self) -> None:
        for message in (
            "/action system health",
            "พรุ่งนี้มีนัดอะไรบ้าง",
            "พรุ่งนี้ผมมีนัดอะไรบ้าง",
            "วันที่ 13/09/2026 มีนัดอะไรบ้าง",
            "อีเมลล่าสุดมีอะไรบ้าง",
            "อีเมลที่ยังไม่ได้อ่านมีอะไรบ้าง",
            "สรุป gmail กับ calendar ที่เพิ่งอ่าน",
            "เปรียบเทียบอีเมลกับปฏิทินที่เพิ่งอ่าน",
        ):
            with self.subTest(message=message):
                self.assertIsNone(self.router.classify(message))

    def test_ordinary_self_reflection_chat_falls_through(self) -> None:
        for message in (
            "คุณคิดว่าระบบของคุณเป็นอย่างไร",
            "Calendar ทำงานยังไง",
            "Gmail คืออะไร",
            "Automation มีประโยชน์ยังไง",
            "คุณทำอะไรได้บ้างในอนาคต",
        ):
            with self.subTest(message=message):
                self.assertIsNone(self.router.classify(message))


class D81RuntimeCapabilityResponseComposerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.composer = RuntimeCapabilityResponseComposer()
        self.snapshot = snapshot()

    def test_calendar_response_states_backend_and_chat_write_separately(self) -> None:
        response = self.composer.compose(
            RuntimeCapabilityStatusIntent(
                target="calendar",
                language="th",
            ),
            self.snapshot,
        )
        self.assertIn("Read via Chat: พร้อม", response)
        self.assertIn("Write backend: มี", response)
        self.assertIn("Write via Chat: ยังไม่รองรับ", response)
        self.assertNotIn("execution_authority", response)

    def test_gmail_response_never_claims_write_or_send(self) -> None:
        response = self.composer.compose(
            RuntimeCapabilityStatusIntent(target="gmail", language="th"),
            self.snapshot,
        )
        self.assertIn("Read via Chat: พร้อม", response)
        self.assertIn("Write/Send: ยังไม่รองรับ", response)

    def test_automation_response_does_not_claim_connector_or_ai_authority(self) -> None:
        response = self.composer.compose(
            RuntimeCapabilityStatusIntent(
                target="automation",
                language="th",
            ),
            self.snapshot,
        )
        self.assertIn("Connector actions: ยังไม่รองรับ", response)
        self.assertIn("AI actions: ยังไม่รองรับ", response)

    def test_system_response_uses_snapshot_facts(self) -> None:
        response = self.composer.compose(
            RuntimeCapabilityStatusIntent(target="system", language="th"),
            self.snapshot,
        )
        for expected in (
            "Service: O-AI",
            "Environment: test",
            "Database revision: 0011_test",
            "Execution audit: ok",
            "Write via Chat: ยังไม่รองรับ",
            "Write/Send: ยังไม่รองรับ",
            "Gmail + Calendar context: เปิดใช้งาน",
            "Connector execution: ยังไม่รองรับ",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, response)

    def test_fail_closed_snapshot_wording_is_bounded(self) -> None:
        data = self.snapshot.model_copy(
            update={
                "google_calendar": GoogleCalendarDiagnostics(
                    status="unavailable",
                    connector_enabled=True,
                    configuration_present=True,
                    read_implemented=True,
                    read_chat_routable=False,
                    write_backend_implemented=True,
                    write_chat_routable=False,
                    execution_authority=False,
                )
            }
        )
        response = self.composer.compose(
            RuntimeCapabilityStatusIntent(
                target="calendar",
                language="th",
            ),
            data,
        )
        self.assertIn("ตรวจสอบสถานะไม่ได้", response)
        self.assertIn("Read via Chat: ยังไม่พร้อม", response)

    def test_english_composer_is_deterministic(self) -> None:
        response = self.composer.compose(
            RuntimeCapabilityStatusIntent(target="calendar", language="en"),
            self.snapshot,
        )
        self.assertEqual(
            response,
            "\n".join(
                (
                    "Google Calendar status",
                    "- Connection: connected",
                    "- Read via Chat: ready",
                    "- Write backend: implemented",
                    "- Write via Chat: not supported",
                )
            ),
        )

    def test_source_has_no_ai_connector_or_authority_runtime_dependency(self) -> None:
        module = __import__(
            "app.services.chat_runtime_capability",
            fromlist=["RuntimeCapabilityResponseComposer"],
        )
        source = inspect.getsource(module)
        for forbidden in (
            "OpenAI",
            "AIRuntime",
            "ExecutionApprovalService",
            "ExecutionGuard",
            "ExecutionPlanner",
            "CredentialAccessBroker",
            "GoogleOAuthClient",
            "GoogleOAuthTokenManager",
            "ModuleRuntime",
            "ToolRuntime",
            "AutomationApprovalService",
            "requests.",
            "httpx.",
            "urllib.request",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
