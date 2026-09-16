import base64
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import SecretStr

from app.api import dependencies
from app.contracts.gmail import GMAIL_CREDENTIAL_SECRET_REF
from app.contracts.google_calendar import (
    GOOGLE_CALENDAR_CREDENTIAL_SECRET_REF,
)
from app.services.google_oauth_subjects import (
    GOOGLE_CALENDAR_OAUTH_SUBJECT,
    GOOGLE_GMAIL_OAUTH_SUBJECT,
)
from app.services.oauth_flow_state import OAuthFlowStateError


class FakeTokenManager:
    def __init__(self, value):
        self.value = value
        self.calls = 0

    def resolve_access_token(self):
        self.calls += 1
        return SecretStr(self.value)


class GoogleGmailOAuthDependencyWiringTests(unittest.TestCase):
    def setUp(self):
        for dependency in (
            dependencies.get_google_oauth_client,
            dependencies.get_google_gmail_oauth_client,
            dependencies.get_google_oauth_flow_state_store,
            dependencies.get_google_gmail_oauth_flow_state_store,
            dependencies.get_google_oauth_token_manager,
            dependencies.get_google_gmail_oauth_token_manager,
            dependencies.get_credential_secret_source,
            dependencies.get_credential_access_broker,
        ):
            dependency.cache_clear()

    def tearDown(self):
        self.setUp()

    @staticmethod
    def settings():
        key = base64.b64encode(os.urandom(32)).decode("ascii")
        return SimpleNamespace(
            oai_google_oauth_client_id="client-id",
            oai_google_oauth_client_secret=SecretStr("client-secret"),
            oai_google_oauth_redirect_uri=(
                "http://localhost:8000/api/v1/oauth/"
                "google-calendar/callback"
            ),
            oai_google_gmail_oauth_redirect_uri=(
                "http://localhost:8000/api/v1/oauth/"
                "google-gmail/callback"
            ),
            oai_oauth_token_encryption_key=SecretStr(key),
        )

    def test_calendar_and_gmail_runtime_subjects_are_exact_and_separate(self):
        with patch.object(
            dependencies,
            "get_settings",
            return_value=self.settings(),
        ):
            calendar = dependencies.get_google_oauth_runtime_config()
            gmail = dependencies.get_google_gmail_oauth_runtime_config()

        self.assertEqual(calendar.subject, GOOGLE_CALENDAR_OAUTH_SUBJECT)
        self.assertEqual(gmail.subject, GOOGLE_GMAIL_OAUTH_SUBJECT)
        self.assertNotEqual(calendar.redirect_uri, gmail.redirect_uri)
        calendar.require_ready()
        gmail.require_ready()

    def test_clients_and_flow_state_stores_are_separate(self):
        calendar_client = dependencies.get_google_oauth_client()
        gmail_client = dependencies.get_google_gmail_oauth_client()
        self.assertIsNot(calendar_client, gmail_client)
        self.assertEqual(
            calendar_client._subject,
            GOOGLE_CALENDAR_OAUTH_SUBJECT,
        )
        self.assertEqual(
            gmail_client._subject,
            GOOGLE_GMAIL_OAUTH_SUBJECT,
        )

        calendar_store = dependencies.get_google_oauth_flow_state_store()
        gmail_store = dependencies.get_google_gmail_oauth_flow_state_store()
        self.assertIsNot(calendar_store, gmail_store)
        calendar_state = calendar_store.issue()
        with self.assertRaises(OAuthFlowStateError):
            gmail_store.consume(calendar_state)

    def test_lazy_secret_source_routes_only_exact_refs(self):
        calendar = FakeTokenManager("calendar-access")
        gmail = FakeTokenManager("gmail-access")
        with (
            patch.object(
                dependencies,
                "get_google_oauth_token_manager",
                return_value=calendar,
            ),
            patch.object(
                dependencies,
                "get_google_gmail_oauth_token_manager",
                return_value=gmail,
            ),
        ):
            dependencies.get_credential_secret_source.cache_clear()
            source = dependencies.get_credential_secret_source()
            self.assertEqual(
                source.resolve(
                    GOOGLE_CALENDAR_CREDENTIAL_SECRET_REF
                ).get_secret_value(),
                "calendar-access",
            )
            self.assertEqual(
                source.resolve(
                    GMAIL_CREDENTIAL_SECRET_REF
                ).get_secret_value(),
                "gmail-access",
            )
            self.assertIsNone(source.resolve("unknown.access_token"))

        self.assertEqual(calendar.calls, 1)
        self.assertEqual(gmail.calls, 1)


if __name__ == "__main__":
    unittest.main()
