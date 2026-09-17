import unittest
from types import SimpleNamespace

from app.contracts.command import Result
from app.contracts.connector_error_semantics import (
    GITHUB_PUBLIC_REPOSITORY_SAFE_ERROR_CODES,
    GMAIL_READ_SAFE_ERROR_CODES,
    GOOGLE_CALENDAR_READ_SAFE_ERROR_CODES,
)
from app.services.chat_calendar import CalendarChatCompletionComposer
from app.services.chat_gmail import GmailChatCompletionComposer
from app.services.chat_plugin_action import (
    ChatPluginActionCompletionService,
    _GITHUB_ERROR_REPLIES,
    _GITHUB_FAILURE_REPLY,
)


class D82ConnectorErrorChatTests(unittest.TestCase):
    @staticmethod
    def _make_outcome(error: str | None, *, execution_status: str = "completed"):
        result = Result(
            request_id="d82-chat",
            status="failed",
            error=error,
        )
        return SimpleNamespace(
            execution=SimpleNamespace(
                status=execution_status,
                result=result,
            )
        )

    def test_owner_facing_mappings_exactly_cover_safe_contract_sets(self) -> None:
        self.assertEqual(
            frozenset(CalendarChatCompletionComposer._ERROR_REPLIES),
            GOOGLE_CALENDAR_READ_SAFE_ERROR_CODES,
        )
        self.assertEqual(
            frozenset(GmailChatCompletionComposer._ERROR_REPLIES),
            GMAIL_READ_SAFE_ERROR_CODES,
        )
        self.assertEqual(
            frozenset(_GITHUB_ERROR_REPLIES),
            GITHUB_PUBLIC_REPOSITORY_SAFE_ERROR_CODES,
        )

    def test_calendar_known_safe_codes_get_bounded_deterministic_wording(self) -> None:
        composer = CalendarChatCompletionComposer()
        binding = SimpleNamespace(calendar_window="today")
        for code in GOOGLE_CALENDAR_READ_SAFE_ERROR_CODES:
            with self.subTest(code=code):
                reply = composer.reply_for_approved(
                    binding,
                    self._make_outcome(code),
                )
                self.assertEqual(reply, composer._ERROR_REPLIES[code])
                self.assertNotEqual(reply, composer.FAILURE_REPLY)
                self.assertLessEqual(len(reply), 256)

    def test_calendar_unknown_or_noncompleted_failure_stays_generic(self) -> None:
        composer = CalendarChatCompletionComposer()
        binding = SimpleNamespace(calendar_window="today")
        for code, execution_status in (
            ("calendar_secret_debug_failure", "completed"),
            (None, "completed"),
            ("calendar_connector_timeout", "failed"),
        ):
            with self.subTest(code=code, execution_status=execution_status):
                reply = composer.reply_for_approved(
                    binding,
                    self._make_outcome(
                        code,
                        execution_status=execution_status,
                    ),
                )
                self.assertEqual(reply, composer.FAILURE_REPLY)

    def test_gmail_known_safe_codes_keep_existing_bounded_wording(self) -> None:
        composer = GmailChatCompletionComposer()
        binding = SimpleNamespace(gmail_query=object())
        for code in GMAIL_READ_SAFE_ERROR_CODES:
            with self.subTest(code=code):
                reply = composer.reply_for_approved(
                    binding,
                    self._make_outcome(code),
                )
                self.assertEqual(reply, composer._ERROR_REPLIES[code])
                self.assertNotEqual(reply, composer.FAILURE_REPLY)
                self.assertLessEqual(len(reply), 256)

    def test_gmail_unknown_failure_stays_generic(self) -> None:
        composer = GmailChatCompletionComposer()
        binding = SimpleNamespace(gmail_query=object())
        for code in ("gmail_secret_debug_failure", None):
            with self.subTest(code=code):
                reply = composer.reply_for_approved(
                    binding,
                    self._make_outcome(code),
                )
                self.assertEqual(reply, composer.FAILURE_REPLY)

    def test_github_known_safe_codes_get_bounded_deterministic_wording(self) -> None:
        service = ChatPluginActionCompletionService.__new__(
            ChatPluginActionCompletionService
        )
        binding = SimpleNamespace(
            gmail_query=None,
            calendar_window=None,
            repository_reference="openai/openai",
        )
        for code in GITHUB_PUBLIC_REPOSITORY_SAFE_ERROR_CODES:
            with self.subTest(code=code):
                reply = service._reply_for_approved(
                    binding,
                    self._make_outcome(code),
                )
                self.assertEqual(reply, _GITHUB_ERROR_REPLIES[code])
                self.assertNotEqual(reply, _GITHUB_FAILURE_REPLY)
                self.assertLessEqual(len(reply), 256)

    def test_github_unknown_or_noncompleted_failure_stays_generic(self) -> None:
        service = ChatPluginActionCompletionService.__new__(
            ChatPluginActionCompletionService
        )
        binding = SimpleNamespace(
            gmail_query=None,
            calendar_window=None,
            repository_reference="openai/openai",
        )
        for code, execution_status in (
            ("github_secret_debug_failure", "completed"),
            (None, "completed"),
            ("connector_network_error", "failed"),
        ):
            with self.subTest(code=code, execution_status=execution_status):
                reply = service._reply_for_approved(
                    binding,
                    self._make_outcome(
                        code,
                        execution_status=execution_status,
                    ),
                )
                self.assertEqual(reply, _GITHUB_FAILURE_REPLY)

    def test_presenters_never_render_raw_unknown_failure_detail(self) -> None:
        sentinel = (
            "Authorization: Bearer SECRET-DO-NOT-LEAK "
            "provider-body=<html>private</html>"
        )

        calendar = CalendarChatCompletionComposer()
        calendar_reply = calendar.reply_for_approved(
            SimpleNamespace(calendar_window="today"),
            self._make_outcome(sentinel),
        )

        gmail = GmailChatCompletionComposer()
        gmail_reply = gmail.reply_for_approved(
            SimpleNamespace(gmail_query=object()),
            self._make_outcome(sentinel),
        )

        github = ChatPluginActionCompletionService.__new__(
            ChatPluginActionCompletionService
        )
        github_reply = github._reply_for_approved(
            SimpleNamespace(
                gmail_query=None,
                calendar_window=None,
                repository_reference="openai/openai",
            ),
            self._make_outcome(sentinel),
        )

        for reply in (calendar_reply, gmail_reply, github_reply):
            self.assertNotIn("SECRET-DO-NOT-LEAK", reply)
            self.assertNotIn("Authorization", reply)
            self.assertNotIn("provider-body", reply)


if __name__ == "__main__":
    unittest.main()
