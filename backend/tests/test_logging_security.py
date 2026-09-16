import logging
import unittest
from unittest.mock import patch

from app.core.logging import (
    GOOGLE_CALENDAR_OAUTH_CALLBACK_PATH,
    GOOGLE_GMAIL_OAUTH_CALLBACK_PATH,
    OAuthCallbackAccessLogFilter,
    _install_oauth_callback_access_log_filter,
)


class OAuthCallbackAccessLogFilterTests(unittest.TestCase):
    @staticmethod
    def access_record(request_target: str) -> logging.LogRecord:
        return logging.LogRecord(
            name="uvicorn.access",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg='%s - "%s %s HTTP/%s" %d',
            args=(
                "127.0.0.1:12345",
                "GET",
                request_target,
                "1.1",
                302,
            ),
            exc_info=None,
        )

    def test_callback_code_and_state_are_removed_from_access_log(self) -> None:
        record = self.access_record(
            GOOGLE_CALENDAR_OAUTH_CALLBACK_PATH
            + "?code=secret-code&state=secret-state"
        )
        subject = OAuthCallbackAccessLogFilter()

        self.assertTrue(subject.filter(record))

        rendered = record.getMessage()
        self.assertIn(GOOGLE_CALENDAR_OAUTH_CALLBACK_PATH, rendered)
        self.assertNotIn("code=", rendered)
        self.assertNotIn("state=", rendered)
        self.assertNotIn("secret-code", rendered)
        self.assertNotIn("secret-state", rendered)

    def test_gmail_callback_code_and_state_are_removed_from_access_log(self) -> None:
        record = self.access_record(
            GOOGLE_GMAIL_OAUTH_CALLBACK_PATH
            + "?code=gmail-secret-code&state=gmail-secret-state"
        )
        subject = OAuthCallbackAccessLogFilter()

        self.assertTrue(subject.filter(record))

        rendered = record.getMessage()
        self.assertIn(GOOGLE_GMAIL_OAUTH_CALLBACK_PATH, rendered)
        self.assertNotIn("code=", rendered)
        self.assertNotIn("state=", rendered)
        self.assertNotIn("gmail-secret-code", rendered)
        self.assertNotIn("gmail-secret-state", rendered)

    def test_callback_error_query_is_removed_from_access_log(self) -> None:
        record = self.access_record(
            GOOGLE_CALENDAR_OAUTH_CALLBACK_PATH
            + "?error=access_denied&state=secret-state"
        )
        subject = OAuthCallbackAccessLogFilter()

        self.assertTrue(subject.filter(record))

        rendered = record.getMessage()
        self.assertNotIn("error=", rendered)
        self.assertNotIn("state=", rendered)
        self.assertNotIn("access_denied", rendered)

    def test_non_callback_query_is_unchanged(self) -> None:
        target = "/api/v1/health?probe=1"
        record = self.access_record(target)
        subject = OAuthCallbackAccessLogFilter()

        self.assertTrue(subject.filter(record))

        self.assertEqual(record.args[2], target)
        self.assertIn("probe=1", record.getMessage())

    def test_malformed_callback_record_fails_closed(self) -> None:
        record = logging.LogRecord(
            name="uvicorn.access",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="%s %s",
            args=(
                "GET",
                GOOGLE_CALENDAR_OAUTH_CALLBACK_PATH + "?code=secret",
            ),
            exc_info=None,
        )
        subject = OAuthCallbackAccessLogFilter()

        self.assertFalse(subject.filter(record))

    def test_malformed_gmail_callback_record_fails_closed(self) -> None:
        record = logging.LogRecord(
            name="uvicorn.access",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="%s %s",
            args=(
                "GET",
                GOOGLE_GMAIL_OAUTH_CALLBACK_PATH + "?code=secret",
            ),
            exc_info=None,
        )
        subject = OAuthCallbackAccessLogFilter()

        self.assertFalse(subject.filter(record))

    def test_filter_installation_is_idempotent(self) -> None:
        logger = logging.Logger("uvicorn.access.test")

        with patch(
            "app.core.logging.logging.getLogger",
            return_value=logger,
        ):
            _install_oauth_callback_access_log_filter()
            _install_oauth_callback_access_log_filter()

        matching = [
            item
            for item in logger.filters
            if isinstance(item, OAuthCallbackAccessLogFilter)
        ]
        self.assertEqual(len(matching), 1)


if __name__ == "__main__":
    unittest.main()
