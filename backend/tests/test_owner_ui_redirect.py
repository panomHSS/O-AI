import unittest
from urllib.parse import parse_qs, urlsplit

from app.services.owner_ui_redirect import (
    OWNER_UI_REDIRECT_ERROR_INVALID_BASE_URL,
    OwnerUIRedirectConfig,
    OwnerUIRedirectConfigError,
)


class OwnerUIRedirectConfigTests(unittest.TestCase):
    def test_allows_only_exact_loopback_http_origin(self):
        for base in (
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ):
            with self.subTest(base=base):
                config = OwnerUIRedirectConfig(base)
                parsed = urlsplit(config.google_calendar_connected_url())
                self.assertEqual(parsed.scheme, "http")
                self.assertIn(parsed.hostname, {"localhost", "127.0.0.1"})
                self.assertEqual(parsed.path, "/settings/integrations")
                self.assertEqual(
                    parse_qs(parsed.query),
                    {"google_calendar": ["connected"]},
                )

    def test_rejects_non_loopback_and_open_redirect_shapes(self):
        for base in (
            "https://localhost:3000",
            "http://evil.example:3000",
            "//evil.example",
            "http://user@localhost:3000",
            "http://localhost:3000/other",
            "http://localhost:3000?next=http://evil.example",
            "http://localhost:3000#fragment",
            "http://localhost",
            "http://localhost:notaport",
        ):
            with self.subTest(base=base):
                with self.assertRaises(OwnerUIRedirectConfigError) as caught:
                    OwnerUIRedirectConfig(base)
                self.assertEqual(
                    caught.exception.code,
                    OWNER_UI_REDIRECT_ERROR_INVALID_BASE_URL,
                )

    def test_error_redirect_contains_only_safe_reason_code(self):
        config = OwnerUIRedirectConfig("http://localhost:3000")
        parsed = urlsplit(
            config.google_calendar_error_url(
                "oauth_exchange_failed"
            )
        )
        self.assertEqual(
            parse_qs(parsed.query),
            {
                "google_calendar": ["error"],
                "reason": ["oauth_exchange_failed"],
            },
        )
        self.assertNotIn("code", parsed.query)
        self.assertNotIn("token", parsed.query)

    def test_unsafe_reason_is_replaced(self):
        config = OwnerUIRedirectConfig("http://localhost:3000")
        parsed = urlsplit(
            config.google_calendar_error_url(
                "oauth_exchange_failed&code=secret"
            )
        )
        self.assertEqual(
            parse_qs(parsed.query)["reason"],
            ["oauth_unavailable"],
        )


if __name__ == "__main__":
    unittest.main()
