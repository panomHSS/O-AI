import base64
import os
import unittest
from datetime import datetime, timezone

from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.connectors.google_oauth import (
    GOOGLE_OAUTH_ERROR_HTTP,
    GoogleOAuthClientError,
    GoogleOAuthTokenResponse,
)
from app.contracts.google_calendar import (
    GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID,
    GOOGLE_CALENDAR_CREDENTIAL_SCOPE,
)
from app.db.base import Base
from app.models.oauth_credential import OAuthCredentialRecord
from app.repositories.oauth_credentials import OAuthCredentialRepository
from app.services.google_oauth_config import GoogleOAuthRuntimeConfig
from app.services.google_oauth_lifecycle import (
    OAUTH_LIFECYCLE_ERROR_REFRESH_TOKEN_MISSING,
    OAUTH_LIFECYCLE_ERROR_STATE_MISMATCH,
    GoogleOAuthLifecycleError,
    GoogleOAuthLifecycleService,
)
from app.services.oauth_flow_state import OAuthFlowStateStore


class FakeClient:
    def __init__(self):
        self.exchange_calls = 0
        self.revoke_calls = 0
        self.response = GoogleOAuthTokenResponse(
            access_token=SecretStr("access-secret-never-log"),
            expires_in=3600,
            token_type="Bearer",
            scopes=(GOOGLE_CALENDAR_CREDENTIAL_SCOPE,),
            refresh_token=SecretStr("refresh-secret-never-log"),
        )
        self.revoke_error = None

    def build_authorization_url(self, config, *, state):
        config.require_ready()
        return f"https://accounts.google.com/o/oauth2/v2/auth?state={state}"

    def exchange_authorization_code(self, config, *, code):
        self.exchange_calls += 1
        return self.response

    def revoke_refresh_token(self, *, refresh_token):
        self.revoke_calls += 1
        if self.revoke_error:
            raise self.revoke_error


class FakeTokenManager:
    def __init__(self):
        self.seed_calls = 0
        self.clear_calls = 0

    def seed_access_token(self, token, *, expires_in):
        self.seed_calls += 1

    def clear_cache(self):
        self.clear_calls += 1


class GoogleOAuthLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        OAuthCredentialRecord.__table__.create(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.session = self.Session()
        self.repository = OAuthCredentialRepository(self.session)
        self.now = datetime(2026, 9, 15, tzinfo=timezone.utc)
        key = base64.b64encode(os.urandom(32)).decode("ascii")
        self.config = GoogleOAuthRuntimeConfig(
            client_id="client-id",
            client_secret=SecretStr("client-secret-never-log"),
            redirect_uri=(
                "http://localhost:8000/api/v1/oauth/"
                "google-calendar/callback"
            ),
            token_encryption_key=SecretStr(key),
        )
        self.client = FakeClient()
        self.token_manager = FakeTokenManager()
        self.flow_store = OAuthFlowStateStore(
            clock=lambda: self.now
        )
        self.service = GoogleOAuthLifecycleService(
            repository=self.repository,
            config=self.config,
            client=self.client,
            flow_state_store=self.flow_store,
            token_manager=self.token_manager,
            clock=lambda: self.now,
        )

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_wrong_browser_cookie_does_zero_token_exchange(self):
        _, state = self.service.start_authorization()
        with self.assertRaises(GoogleOAuthLifecycleError) as caught:
            self.service.complete_authorization(
                query_state=state,
                cookie_state="wrong",
                code="code",
                oauth_error=None,
            )
        self.assertEqual(
            caught.exception.code,
            OAUTH_LIFECYCLE_ERROR_STATE_MISMATCH,
        )
        self.assertEqual(self.client.exchange_calls, 0)

    def test_success_persists_ciphertext_not_plaintext_and_seeds_access_only_in_memory(self):
        _, state = self.service.start_authorization()
        result = self.service.complete_authorization(
            query_state=state,
            cookie_state=state,
            code="authorization-code",
            oauth_error=None,
        )
        self.assertTrue(result.connected)
        record = self.repository.get(
            GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID
        )
        self.assertIsNotNone(record)
        self.assertNotIn(
            b"refresh-secret-never-log",
            record.encrypted_refresh_token,
        )
        self.assertFalse(
            hasattr(record, "access_token")
        )
        self.assertEqual(self.token_manager.seed_calls, 1)

    def test_first_connection_requires_refresh_token(self):
        self.client.response = GoogleOAuthTokenResponse(
            access_token=SecretStr("access-secret-never-log"),
            expires_in=3600,
            token_type="Bearer",
            scopes=(GOOGLE_CALENDAR_CREDENTIAL_SCOPE,),
            refresh_token=None,
        )
        _, state = self.service.start_authorization()
        with self.assertRaises(GoogleOAuthLifecycleError) as caught:
            self.service.complete_authorization(
                query_state=state,
                cookie_state=state,
                code="authorization-code",
                oauth_error=None,
            )
        self.assertEqual(
            caught.exception.code,
            OAUTH_LIFECYCLE_ERROR_REFRESH_TOKEN_MISSING,
        )

    def test_reconnect_without_new_refresh_token_preserves_existing_ciphertext(self):
        _, state = self.service.start_authorization()
        self.service.complete_authorization(
            query_state=state,
            cookie_state=state,
            code="authorization-code",
            oauth_error=None,
        )
        original = self.repository.get(
            GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID
        )
        original_ciphertext = bytes(original.encrypted_refresh_token)
        original_nonce = bytes(original.encryption_nonce)

        self.client.response = GoogleOAuthTokenResponse(
            access_token=SecretStr("second-access-secret-never-log"),
            expires_in=3600,
            token_type="Bearer",
            scopes=(GOOGLE_CALENDAR_CREDENTIAL_SCOPE,),
            refresh_token=None,
        )
        _, state = self.service.start_authorization()
        self.service.complete_authorization(
            query_state=state,
            cookie_state=state,
            code="second-authorization-code",
            oauth_error=None,
        )

        current = self.repository.get(
            GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID
        )
        self.assertEqual(
            current.encrypted_refresh_token,
            original_ciphertext,
        )
        self.assertEqual(current.encryption_nonce, original_nonce)

    def test_reauthorization_required_record_cannot_be_reactivated_without_new_refresh(self):
        _, state = self.service.start_authorization()
        self.service.complete_authorization(
            query_state=state,
            cookie_state=state,
            code="authorization-code",
            oauth_error=None,
        )
        self.repository.mark_reauthorization_required(
            GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID,
            now=self.now,
        )
        self.repository.commit()
        self.client.response = GoogleOAuthTokenResponse(
            access_token=SecretStr("second-access-secret-never-log"),
            expires_in=3600,
            token_type="Bearer",
            scopes=(GOOGLE_CALENDAR_CREDENTIAL_SCOPE,),
            refresh_token=None,
        )
        _, state = self.service.start_authorization()
        with self.assertRaises(GoogleOAuthLifecycleError) as caught:
            self.service.complete_authorization(
                query_state=state,
                cookie_state=state,
                code="second-authorization-code",
                oauth_error=None,
            )
        self.assertEqual(
            caught.exception.code,
            OAUTH_LIFECYCLE_ERROR_REFRESH_TOKEN_MISSING,
        )
        record = self.repository.get(
            GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID
        )
        self.assertEqual(record.status, "reauthorization_required")

    def test_revoke_failure_keeps_local_ciphertext(self):
        _, state = self.service.start_authorization()
        self.service.complete_authorization(
            query_state=state,
            cookie_state=state,
            code="authorization-code",
            oauth_error=None,
        )
        self.client.revoke_error = GoogleOAuthClientError(
            GOOGLE_OAUTH_ERROR_HTTP
        )
        with self.assertRaises(GoogleOAuthLifecycleError):
            self.service.disconnect()
        self.assertIsNotNone(
            self.repository.get(
                GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID
            )
        )

    def test_disconnect_revokes_before_local_delete(self):
        _, state = self.service.start_authorization()
        self.service.complete_authorization(
            query_state=state,
            cookie_state=state,
            code="authorization-code",
            oauth_error=None,
        )
        result = self.service.disconnect()
        self.assertFalse(result.connected)
        self.assertEqual(result.status, "disconnected")
        self.assertEqual(self.client.revoke_calls, 1)
        self.assertIsNone(
            self.repository.get(
                GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID
            )
        )
        self.assertEqual(self.token_manager.clear_calls, 1)


if __name__ == "__main__":
    unittest.main()
