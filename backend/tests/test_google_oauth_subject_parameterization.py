import base64
import os
import unittest
import urllib.parse
from datetime import datetime, timezone

from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.connectors.google_oauth import GoogleOAuthClient, GoogleOAuthTokenResponse
from app.contracts.gmail import (
    GMAIL_CREDENTIAL_SCOPE,
    GMAIL_CREDENTIAL_SECRET_REF,
    GMAIL_PLUGIN_ID,
    GMAIL_PLUGIN_VERSION,
    GMAIL_READ_CAPABILITY_NAME,
    GMAIL_READ_CREDENTIAL_PROFILE_ID,
)
from app.contracts.google_calendar import (
    GOOGLE_CALENDAR_CAPABILITY_NAME,
    GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID,
    GOOGLE_CALENDAR_CREDENTIAL_PROVIDER_ID,
    GOOGLE_CALENDAR_CREDENTIAL_SCOPE,
    GOOGLE_CALENDAR_PLUGIN_ID,
    GOOGLE_CALENDAR_PLUGIN_VERSION,
)
from app.models.oauth_credential import OAuthCredentialRecord
from app.repositories.oauth_credentials import OAuthCredentialRepository
from app.services.google_oauth_config import (
    GoogleOAuthConfigError,
    GoogleOAuthRuntimeConfig,
)
from app.services.google_oauth_connection_status import (
    GoogleOAuthConnectionStatusReader,
)
from app.services.google_oauth_lifecycle import GoogleOAuthLifecycleService
from app.services.google_oauth_subjects import (
    GOOGLE_CALENDAR_OAUTH_AAD,
    GOOGLE_CALENDAR_OAUTH_SUBJECT,
    GOOGLE_GMAIL_OAUTH_AAD,
    GOOGLE_GMAIL_OAUTH_SUBJECT,
)
from app.services.google_oauth_token_manager import (
    GOOGLE_OAUTH_TOKEN_ERROR_NOT_CONNECTED,
    GoogleOAuthTokenManager,
    GoogleOAuthTokenManagerError,
)
from app.services.oauth_flow_state import OAuthFlowStateStore
from app.services.oauth_token_cipher import OAuthTokenCipher, OAuthTokenCipherError


class FakeResponse:
    def __init__(self, payload):
        import json
        self.status = 200
        self.body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, limit):
        return self.body[:limit]


class RecordingTransport:
    def __init__(self, payload):
        self.payload = payload
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append(request)
        return FakeResponse(self.payload)


class FakeLifecycleClient:
    def __init__(self):
        self.revoke_calls = 0
        self.response = GoogleOAuthTokenResponse(
            access_token=SecretStr("gmail-access-secret"),
            expires_in=3600,
            token_type="Bearer",
            scopes=(GMAIL_CREDENTIAL_SCOPE,),
            refresh_token=SecretStr("gmail-refresh-secret"),
        )

    def build_authorization_url(self, config, *, state):
        config.require_ready()
        return f"https://accounts.google.com/o/oauth2/v2/auth?state={state}"

    def exchange_authorization_code(self, config, *, code):
        return self.response

    def revoke_refresh_token(self, *, refresh_token):
        self.revoke_calls += 1


class FakeTokenManager:
    def __init__(self):
        self.seed_calls = 0
        self.clear_calls = 0

    def seed_access_token(self, token, *, expires_in):
        self.seed_calls += 1

    def clear_cache(self):
        self.clear_calls += 1


class FakeRefreshClient:
    def __init__(self):
        self.calls = 0

    def refresh_access_token(self, config, *, refresh_token):
        self.calls += 1
        return GoogleOAuthTokenResponse(
            access_token=SecretStr("gmail-access-secret"),
            expires_in=3600,
            token_type="Bearer",
            scopes=(),
        )


class FakeStatusRepository:
    def __init__(self, record):
        self.record = record
        self.profile_ids = []

    def get(self, profile_id):
        self.profile_ids.append(profile_id)
        return self.record


class GoogleOAuthSubjectParameterizationTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 16, tzinfo=timezone.utc)
        self.key = SecretStr(
            base64.b64encode(os.urandom(32)).decode("ascii")
        )

    def gmail_config(self):
        return GoogleOAuthRuntimeConfig(
            client_id="client-id",
            client_secret=SecretStr("client-secret-never-log"),
            redirect_uri=(
                "http://localhost:8000/api/v1/oauth/"
                "google-gmail/callback"
            ),
            token_encryption_key=self.key,
            subject=GOOGLE_GMAIL_OAUTH_SUBJECT,
        )

    def test_exact_gmail_subject_and_calendar_subject_are_distinct(self):
        self.assertEqual(GOOGLE_GMAIL_OAUTH_SUBJECT.plugin_id, GMAIL_PLUGIN_ID)
        self.assertEqual(
            GOOGLE_GMAIL_OAUTH_SUBJECT.plugin_version,
            GMAIL_PLUGIN_VERSION,
        )
        self.assertEqual(
            GOOGLE_GMAIL_OAUTH_SUBJECT.capability_name,
            GMAIL_READ_CAPABILITY_NAME,
        )
        self.assertEqual(
            GOOGLE_GMAIL_OAUTH_SUBJECT.profile_id,
            GMAIL_READ_CREDENTIAL_PROFILE_ID,
        )
        self.assertEqual(
            GOOGLE_GMAIL_OAUTH_SUBJECT.scope,
            GMAIL_CREDENTIAL_SCOPE,
        )
        self.assertEqual(
            GOOGLE_GMAIL_OAUTH_SUBJECT.secret_ref,
            GMAIL_CREDENTIAL_SECRET_REF,
        )
        self.assertNotEqual(
            GOOGLE_GMAIL_OAUTH_SUBJECT,
            GOOGLE_CALENDAR_OAUTH_SUBJECT,
        )
        self.assertNotEqual(
            GOOGLE_GMAIL_OAUTH_AAD,
            GOOGLE_CALENDAR_OAUTH_AAD,
        )

    def test_gmail_config_accepts_only_gmail_callback_for_gmail_subject(self):
        self.gmail_config().require_ready()
        with self.assertRaises(GoogleOAuthConfigError):
            GoogleOAuthRuntimeConfig(
                client_id="client-id",
                client_secret=SecretStr("client-secret-never-log"),
                redirect_uri=(
                    "http://localhost:8000/api/v1/oauth/"
                    "google-calendar/callback"
                ),
                token_encryption_key=self.key,
                subject=GOOGLE_GMAIL_OAUTH_SUBJECT,
            )

    def test_gmail_authorization_url_requests_only_gmail_readonly_scope(self):
        transport = RecordingTransport(
            {
                "access_token": "gmail-access-secret",
                "expires_in": 3600,
                "refresh_token": "gmail-refresh-secret",
                "scope": GMAIL_CREDENTIAL_SCOPE,
                "token_type": "Bearer",
            }
        )
        client = GoogleOAuthClient(
            subject=GOOGLE_GMAIL_OAUTH_SUBJECT,
            transport=transport,
        )
        url = client.build_authorization_url(
            self.gmail_config(),
            state="gmail-state",
        )
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        self.assertEqual(query["scope"], [GMAIL_CREDENTIAL_SCOPE])
        self.assertNotIn(GOOGLE_CALENDAR_CREDENTIAL_SCOPE, query["scope"])
        self.assertNotIn("include_granted_scopes", query)

    def test_gmail_ciphertext_is_bound_to_gmail_aad_only(self):
        cipher = OAuthTokenCipher.from_base64_key(self.key)
        encrypted = cipher.encrypt(
            SecretStr("gmail-refresh-secret"),
            aad=GOOGLE_GMAIL_OAUTH_AAD,
        )
        self.assertEqual(
            cipher.decrypt(
                encrypted.ciphertext,
                encrypted.nonce,
                aad=GOOGLE_GMAIL_OAUTH_AAD,
            ).get_secret_value(),
            "gmail-refresh-secret",
        )
        with self.assertRaises(OAuthTokenCipherError):
            cipher.decrypt(
                encrypted.ciphertext,
                encrypted.nonce,
                aad=GOOGLE_CALENDAR_OAUTH_AAD,
            )

    def test_status_reader_uses_only_selected_gmail_profile(self):
        record = type(
            "Record",
            (),
            {
                "provider_id": "google",
                "plugin_id": GMAIL_PLUGIN_ID,
                "plugin_version": GMAIL_PLUGIN_VERSION,
                "capability_name": GMAIL_READ_CAPABILITY_NAME,
                "granted_scopes": GMAIL_CREDENTIAL_SCOPE,
                "cipher_version": "aesgcm-v1",
                "status": "active",
            },
        )()
        repository = FakeStatusRepository(record)
        reader = GoogleOAuthConnectionStatusReader(
            repository,
            subject=GOOGLE_GMAIL_OAUTH_SUBJECT,
        )
        self.assertEqual(reader.read_status(), "active")
        self.assertEqual(
            repository.profile_ids,
            [GMAIL_READ_CREDENTIAL_PROFILE_ID],
        )

    def test_gmail_lifecycle_persists_and_disconnects_only_gmail_record(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        OAuthCredentialRecord.__table__.create(engine)
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        session = Session()
        repository = OAuthCredentialRepository(session)
        repository.save_active(
            profile_id=GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID,
            provider_id=GOOGLE_CALENDAR_CREDENTIAL_PROVIDER_ID,
            plugin_id=GOOGLE_CALENDAR_PLUGIN_ID,
            plugin_version=GOOGLE_CALENDAR_PLUGIN_VERSION,
            capability_name=GOOGLE_CALENDAR_CAPABILITY_NAME,
            encrypted_refresh_token=b"calendar-ciphertext",
            encryption_nonce=b"calendar-nonce",
            cipher_version="aesgcm-v1",
            granted_scopes=GOOGLE_CALENDAR_CREDENTIAL_SCOPE,
            refresh_token_expires_at=None,
            now=self.now,
        )
        repository.commit()

        client = FakeLifecycleClient()
        token_manager = FakeTokenManager()
        service = GoogleOAuthLifecycleService(
            repository=repository,
            config=self.gmail_config(),
            client=client,
            flow_state_store=OAuthFlowStateStore(clock=lambda: self.now),
            token_manager=token_manager,
            clock=lambda: self.now,
        )
        _, state = service.start_authorization()
        result = service.complete_authorization(
            query_state=state,
            cookie_state=state,
            code="gmail-authorization-code",
            oauth_error=None,
        )
        self.assertTrue(result.connected)
        gmail_record = repository.get(GMAIL_READ_CREDENTIAL_PROFILE_ID)
        self.assertIsNotNone(gmail_record)
        self.assertEqual(gmail_record.plugin_id, GMAIL_PLUGIN_ID)
        self.assertIsNotNone(
            repository.get(GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID)
        )

        disconnected = service.disconnect()
        self.assertFalse(disconnected.connected)
        self.assertIsNone(repository.get(GMAIL_READ_CREDENTIAL_PROFILE_ID))
        self.assertIsNotNone(
            repository.get(GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID)
        )
        self.assertEqual(client.revoke_calls, 1)
        self.assertEqual(token_manager.seed_calls, 1)
        self.assertEqual(token_manager.clear_calls, 1)
        session.close()
        engine.dispose()

    def test_gmail_token_manager_does_not_read_calendar_record_as_gmail(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        OAuthCredentialRecord.__table__.create(engine)
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        session = Session()
        repository = OAuthCredentialRepository(session)
        repository.save_active(
            profile_id=GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID,
            provider_id=GOOGLE_CALENDAR_CREDENTIAL_PROVIDER_ID,
            plugin_id=GOOGLE_CALENDAR_PLUGIN_ID,
            plugin_version=GOOGLE_CALENDAR_PLUGIN_VERSION,
            capability_name=GOOGLE_CALENDAR_CAPABILITY_NAME,
            encrypted_refresh_token=b"calendar-ciphertext",
            encryption_nonce=b"calendar-nonce",
            cipher_version="aesgcm-v1",
            granted_scopes=GOOGLE_CALENDAR_CREDENTIAL_SCOPE,
            refresh_token_expires_at=None,
            now=self.now,
        )
        repository.commit()
        session.close()

        client = FakeRefreshClient()
        manager = GoogleOAuthTokenManager(
            session_factory=Session,
            config=self.gmail_config(),
            client=client,
            clock=lambda: self.now,
        )
        with self.assertRaises(GoogleOAuthTokenManagerError) as caught:
            manager.resolve_access_token()
        self.assertEqual(
            caught.exception.code,
            GOOGLE_OAUTH_TOKEN_ERROR_NOT_CONNECTED,
        )
        self.assertEqual(client.calls, 0)
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
