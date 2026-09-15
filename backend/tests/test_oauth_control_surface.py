import unittest
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

from pydantic import SecretStr

from app.api.v1.oauth import (
    OAUTH_STATE_COOKIE,
    google_calendar_oauth_callback,
    google_calendar_oauth_status,
)
from app.services.google_oauth_config import GoogleOAuthRuntimeConfig
from app.services.google_oauth_lifecycle import (
    OAUTH_LIFECYCLE_ERROR_CONSENT_DENIED,
    GoogleOAuthLifecycleError,
)
from app.services.owner_ui_redirect import OwnerUIRedirectConfig


class TrapSecretStr(SecretStr):
    def get_secret_value(self):
        raise AssertionError("D66 status must not read secret values.")


class FakeLifecycleService:
    def __init__(self, *, status="active", callback_error=None):
        self.status_value = status
        self.callback_error = callback_error
        self.complete_calls = 0

    def status(self):
        return SimpleNamespace(
            connected=self.status_value == "active",
            status=self.status_value,
            scope=(
                "https://www.googleapis.com/auth/"
                "calendar.events.readonly"
            ),
        )

    def complete_authorization(self, **kwargs):
        self.complete_calls += 1
        self.kwargs = kwargs
        if self.callback_error is not None:
            raise self.callback_error
        return self.status()


class OAuthControlSurfaceTests(unittest.TestCase):
    def runtime_config(self):
        return GoogleOAuthRuntimeConfig(
            client_id="client-id",
            client_secret=TrapSecretStr("do-not-read"),
            redirect_uri=(
                "http://localhost:8000/api/v1/oauth/"
                "google-calendar/callback"
            ),
            token_encryption_key=TrapSecretStr("do-not-read"),
        )

    def settings(self, *, enabled=True):
        return SimpleNamespace(
            oai_google_calendar_connector_enabled=enabled,
            oai_owner_timezone="Asia/Bangkok",
        )

    def test_status_exposes_only_safe_control_surface_metadata(self):
        response = google_calendar_oauth_status(
            service=FakeLifecycleService(status="active"),
            runtime_config=self.runtime_config(),
            settings=self.settings(),
        )
        self.assertTrue(response.data.connector_enabled)
        self.assertTrue(response.data.configuration_present)
        self.assertTrue(response.data.connected)
        self.assertEqual(response.data.status, "active")
        self.assertEqual(response.data.owner_timezone, "Asia/Bangkok")
        serialized = response.data.model_dump()
        for forbidden in (
            "access_token",
            "refresh_token",
            "client_secret",
            "encryption_key",
            "ciphertext",
            "nonce",
            "authorization_code",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_status_can_report_disabled_without_touching_secret_value(self):
        response = google_calendar_oauth_status(
            service=FakeLifecycleService(status="disconnected"),
            runtime_config=self.runtime_config(),
            settings=self.settings(enabled=False),
        )
        self.assertFalse(response.data.connector_enabled)
        self.assertTrue(response.data.configuration_present)
        self.assertFalse(response.data.connected)

    def test_success_callback_redirects_to_fixed_ui_and_clears_cookie(self):
        service = FakeLifecycleService(status="active")
        response = google_calendar_oauth_callback(
            state_value="state-value",
            service=service,
            owner_ui_config=OwnerUIRedirectConfig(
                "http://localhost:3000"
            ),
            code="authorization-code-secret",
            oauth_error=None,
            cookie_state="state-value",
        )
        self.assertEqual(response.status_code, 302)
        parsed = urlsplit(response.headers["location"])
        self.assertEqual(parsed.netloc, "localhost:3000")
        self.assertEqual(parsed.path, "/settings/integrations")
        self.assertEqual(
            parse_qs(parsed.query),
            {"google_calendar": ["connected"]},
        )
        self.assertNotIn("authorization-code-secret", response.headers["location"])
        self.assertIn(
            f"{OAUTH_STATE_COOKIE}=",
            response.headers["set-cookie"],
        )
        self.assertIn("Max-Age=0", response.headers["set-cookie"])

    def test_lifecycle_error_redirects_with_safe_reason_and_clears_cookie(self):
        service = FakeLifecycleService(
            callback_error=GoogleOAuthLifecycleError(
                OAUTH_LIFECYCLE_ERROR_CONSENT_DENIED
            )
        )
        response = google_calendar_oauth_callback(
            state_value="state-value",
            service=service,
            owner_ui_config=OwnerUIRedirectConfig(
                "http://localhost:3000"
            ),
            code="authorization-code-secret",
            oauth_error="provider-detail-that-must-not-return",
            cookie_state="state-value",
        )
        parsed = urlsplit(response.headers["location"])
        query = parse_qs(parsed.query)
        self.assertEqual(query["google_calendar"], ["error"])
        self.assertEqual(
            query["reason"],
            [OAUTH_LIFECYCLE_ERROR_CONSENT_DENIED],
        )
        self.assertNotIn("authorization-code-secret", response.headers["location"])
        self.assertNotIn(
            "provider-detail-that-must-not-return",
            response.headers["location"],
        )
        self.assertIn("Max-Age=0", response.headers["set-cookie"])

    def test_oversized_code_does_zero_exchange_and_clears_cookie(self):
        service = FakeLifecycleService(status="active")
        response = google_calendar_oauth_callback(
            state_value="state-value",
            service=service,
            owner_ui_config=OwnerUIRedirectConfig(
                "http://localhost:3000"
            ),
            code="x" * 8193,
            oauth_error=None,
            cookie_state="state-value",
        )
        self.assertEqual(service.complete_calls, 0)
        parsed = urlsplit(response.headers["location"])
        self.assertEqual(
            parse_qs(parsed.query)["reason"],
            ["oauth_invalid_code"],
        )
        self.assertIn("Max-Age=0", response.headers["set-cookie"])

    def test_missing_state_does_zero_exchange_and_redirects_safe_error(self):
        service = FakeLifecycleService(status="active")
        response = google_calendar_oauth_callback(
            state_value=None,
            service=service,
            owner_ui_config=OwnerUIRedirectConfig(
                "http://localhost:3000"
            ),
            code="authorization-code-secret",
            oauth_error=None,
            cookie_state=None,
        )
        self.assertEqual(service.complete_calls, 0)
        parsed = urlsplit(response.headers["location"])
        self.assertEqual(
            parse_qs(parsed.query)["reason"],
            ["oauth_state_invalid"],
        )


if __name__ == "__main__":
    unittest.main()
