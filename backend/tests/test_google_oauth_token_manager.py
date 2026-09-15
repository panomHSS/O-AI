import base64
import os
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone

from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.connectors.google_oauth import (
    GOOGLE_OAUTH_ERROR_INVALID_GRANT,
    GoogleOAuthClientError,
    GoogleOAuthTokenResponse,
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
    GOOGLE_CALENDAR_OAUTH_AAD,
    GoogleOAuthRuntimeConfig,
)
from app.services.google_oauth_token_manager import (
    GOOGLE_OAUTH_TOKEN_ERROR_DECRYPTION_FAILED,
    GOOGLE_OAUTH_TOKEN_ERROR_NOT_CONNECTED,
    GOOGLE_OAUTH_TOKEN_ERROR_REAUTHORIZATION_REQUIRED,
    GoogleOAuthTokenManager,
    GoogleOAuthTokenManagerError,
)
from app.services.oauth_token_cipher import OAuthTokenCipher


class FakeClient:
    def __init__(self, *, delay=0):
        self.calls = 0
        self.delay = delay
        self.error = None

    def refresh_access_token(self, config, *, refresh_token):
        self.calls += 1
        if self.delay:
            time.sleep(self.delay)
        if self.error:
            raise self.error
        return GoogleOAuthTokenResponse(
            access_token=SecretStr("access-secret-never-log"),
            expires_in=3600,
            token_type="Bearer",
            scopes=(),
        )


class GoogleOAuthTokenManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.NamedTemporaryFile(
            suffix=".sqlite3",
            delete=False,
        )
        self.temp.close()
        self.engine = create_engine(
            f"sqlite+pysqlite:///{self.temp.name}",
            connect_args={"check_same_thread": False},
        )
        OAuthCredentialRecord.__table__.create(self.engine)
        self.Session = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
        )
        self.now = datetime(2026, 9, 15, tzinfo=timezone.utc)
        key = base64.b64encode(os.urandom(32)).decode("ascii")
        self.key = SecretStr(key)
        self.config = GoogleOAuthRuntimeConfig(
            client_id="client-id",
            client_secret=SecretStr("client-secret-never-log"),
            redirect_uri=(
                "http://localhost:8000/api/v1/oauth/"
                "google-calendar/callback"
            ),
            token_encryption_key=self.key,
        )
        self.client = FakeClient()
        self._store_refresh("refresh-secret-never-log")

    def tearDown(self):
        self.engine.dispose()
        try:
            os.unlink(self.temp.name)
        except OSError:
            pass

    def _store_refresh(self, value):
        session = self.Session()
        repo = OAuthCredentialRepository(session)
        cipher = OAuthTokenCipher.from_base64_key(self.key)
        encrypted = cipher.encrypt(
            SecretStr(value),
            aad=GOOGLE_CALENDAR_OAUTH_AAD,
        )
        repo.save_active(
            profile_id=GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID,
            provider_id=GOOGLE_CALENDAR_CREDENTIAL_PROVIDER_ID,
            plugin_id=GOOGLE_CALENDAR_PLUGIN_ID,
            plugin_version=GOOGLE_CALENDAR_PLUGIN_VERSION,
            capability_name=GOOGLE_CALENDAR_CAPABILITY_NAME,
            encrypted_refresh_token=encrypted.ciphertext,
            encryption_nonce=encrypted.nonce,
            cipher_version=encrypted.cipher_version,
            granted_scopes=GOOGLE_CALENDAR_CREDENTIAL_SCOPE,
            refresh_token_expires_at=None,
            now=self.now,
        )
        repo.commit()
        session.close()

    def manager(self, client=None, config=None):
        return GoogleOAuthTokenManager(
            session_factory=self.Session,
            config=config or self.config,
            client=client or self.client,
            clock=lambda: self.now,
        )

    def test_refreshes_once_then_uses_memory_cache(self):
        manager = self.manager()
        first = manager.resolve_access_token()
        second = manager.resolve_access_token()
        self.assertEqual(self.client.calls, 1)
        self.assertEqual(
            first.get_secret_value(),
            "access-secret-never-log",
        )
        self.assertEqual(
            second.get_secret_value(),
            "access-secret-never-log",
        )

    def test_invalid_grant_marks_reauthorization_required(self):
        self.client.error = GoogleOAuthClientError(
            GOOGLE_OAUTH_ERROR_INVALID_GRANT
        )
        with self.assertRaises(GoogleOAuthTokenManagerError) as caught:
            self.manager().resolve_access_token()
        self.assertEqual(
            caught.exception.code,
            GOOGLE_OAUTH_TOKEN_ERROR_REAUTHORIZATION_REQUIRED,
        )
        session = self.Session()
        record = OAuthCredentialRepository(session).get(
            GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID
        )
        self.assertEqual(record.status, "reauthorization_required")
        session.close()

    def test_wrong_encryption_key_fails_closed(self):
        wrong_key = SecretStr(
            base64.b64encode(os.urandom(32)).decode("ascii")
        )
        config = GoogleOAuthRuntimeConfig(
            client_id="client-id",
            client_secret=SecretStr("client-secret-never-log"),
            redirect_uri=(
                "http://localhost:8000/api/v1/oauth/"
                "google-calendar/callback"
            ),
            token_encryption_key=wrong_key,
        )
        with self.assertRaises(GoogleOAuthTokenManagerError) as caught:
            self.manager(config=config).resolve_access_token()
        self.assertEqual(
            caught.exception.code,
            GOOGLE_OAUTH_TOKEN_ERROR_DECRYPTION_FAILED,
        )
        self.assertEqual(self.client.calls, 0)

    def test_missing_record_does_zero_network(self):
        session = self.Session()
        OAuthCredentialRepository(session).delete(
            GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID
        )
        session.commit()
        session.close()
        with self.assertRaises(GoogleOAuthTokenManagerError) as caught:
            self.manager().resolve_access_token()
        self.assertEqual(
            caught.exception.code,
            GOOGLE_OAUTH_TOKEN_ERROR_NOT_CONNECTED,
        )
        self.assertEqual(self.client.calls, 0)

    def test_concurrent_resolve_performs_one_refresh(self):
        client = FakeClient(delay=0.05)
        manager = self.manager(client=client)
        results = []
        errors = []

        def worker():
            try:
                results.append(
                    manager.resolve_access_token().get_secret_value()
                )
            except Exception as error:
                errors.append(error)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(errors, [])
        self.assertEqual(len(results), 2)
        self.assertEqual(client.calls, 1)


if __name__ == "__main__":
    unittest.main()
