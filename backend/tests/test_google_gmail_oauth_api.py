import base64
import os
import unittest
from urllib.parse import parse_qs, urlsplit

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api import dependencies
from app.api.v1.gmail_oauth import (
    GMAIL_OAUTH_CALLBACK_PATH,
    GMAIL_OAUTH_STATE_COOKIE,
    router,
)
from app.core.config import Settings, get_settings
from app.contracts.gmail import GMAIL_CREDENTIAL_SCOPE
from app.services.google_oauth_config import GoogleOAuthRuntimeConfig
from app.services.google_oauth_lifecycle import (
    OAUTH_LIFECYCLE_ERROR_STATE_MISMATCH,
    GoogleOAuthLifecycleError,
    GoogleOAuthStatus,
)
from app.services.google_oauth_subjects import GOOGLE_GMAIL_OAUTH_SUBJECT
from app.services.owner_ui_redirect import OwnerUIRedirectConfig


class FakeLifecycle:
    def __init__(self):
        self.completed_cookie = None
        self.disconnect_calls = 0

    def start_authorization(self):
        return (
            "https://accounts.google.com/o/oauth2/v2/auth?state=gmail-state",
            "gmail-state",
        )

    def complete_authorization(
        self,
        *,
        query_state,
        cookie_state,
        code,
        oauth_error,
    ):
        self.completed_cookie = cookie_state
        if cookie_state != "gmail-state":
            raise GoogleOAuthLifecycleError(
                OAUTH_LIFECYCLE_ERROR_STATE_MISMATCH
            )
        return GoogleOAuthStatus(
            connected=True,
            status="active",
            scope=GMAIL_CREDENTIAL_SCOPE,
        )

    def status(self):
        return GoogleOAuthStatus(
            connected=True,
            status="active",
            scope=GMAIL_CREDENTIAL_SCOPE,
        )

    def disconnect(self):
        self.disconnect_calls += 1
        return GoogleOAuthStatus(
            connected=False,
            status="disconnected",
            scope=GMAIL_CREDENTIAL_SCOPE,
        )


class GoogleGmailOAuthApiTests(unittest.TestCase):
    def setUp(self):
        self.service = FakeLifecycle()
        self.settings = Settings(
            _env_file=None,
            oai_gmail_connector_enabled=True,
            oai_owner_timezone="Asia/Bangkok",
        )
        key = base64.b64encode(os.urandom(32)).decode("ascii")
        self.runtime_config = GoogleOAuthRuntimeConfig(
            client_id="client-id",
            client_secret=SecretStr("client-secret"),
            redirect_uri=(
                "http://localhost:8000"
                "/api/v1/oauth/google-gmail/callback"
            ),
            token_encryption_key=SecretStr(key),
            subject=GOOGLE_GMAIL_OAUTH_SUBJECT,
        )
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[
            dependencies.get_google_gmail_oauth_lifecycle_service
        ] = lambda: self.service
        app.dependency_overrides[
            dependencies.get_google_gmail_oauth_runtime_config
        ] = lambda: self.runtime_config
        app.dependency_overrides[
            dependencies.get_owner_ui_redirect_config
        ] = lambda: OwnerUIRedirectConfig("http://localhost:3000")
        app.dependency_overrides[get_settings] = lambda: self.settings
        self.client = TestClient(app)

    def test_start_uses_gmail_cookie_and_exact_callback_path(self):
        response = self.client.get(
            "/api/v1/oauth/google-gmail/start",
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        cookie = response.headers["set-cookie"]
        self.assertIn(
            f"{GMAIL_OAUTH_STATE_COOKIE}=gmail-state",
            cookie,
        )
        self.assertIn(f"Path={GMAIL_OAUTH_CALLBACK_PATH}", cookie)
        self.assertNotIn("oai_google_calendar_oauth_state", cookie)

    def test_calendar_cookie_cannot_complete_gmail_flow(self):
        response = self.client.get(
            "/api/v1/oauth/google-gmail/callback",
            params={"state": "gmail-state", "code": "code"},
            cookies={
                "oai_google_calendar_oauth_state": "gmail-state",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        query = parse_qs(urlsplit(response.headers["location"]).query)
        self.assertEqual(query["gmail"], ["error"])
        self.assertEqual(
            query["reason"],
            [OAUTH_LIFECYCLE_ERROR_STATE_MISMATCH],
        )
        self.assertIsNone(self.service.completed_cookie)

    def test_status_exposes_only_safe_gmail_metadata(self):
        response = self.client.get("/api/v1/oauth/google-gmail/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertTrue(data["connector_enabled"])
        self.assertTrue(data["configuration_present"])
        self.assertTrue(data["connected"])
        self.assertEqual(data["status"], "active")
        self.assertEqual(data["scope"], GMAIL_CREDENTIAL_SCOPE)
        self.assertNotIn("token", str(data).lower())

    def test_disconnect_requires_local_marker(self):
        denied = self.client.post(
            "/api/v1/oauth/google-gmail/disconnect"
        )
        self.assertEqual(denied.status_code, 403)
        allowed = self.client.post(
            "/api/v1/oauth/google-gmail/disconnect",
            headers={"X-OAI-Local-Request": "1"},
        )
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(self.service.disconnect_calls, 1)
        self.assertFalse(allowed.json()["data"]["connected"])


if __name__ == "__main__":
    unittest.main()
