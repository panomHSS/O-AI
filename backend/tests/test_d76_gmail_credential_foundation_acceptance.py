import base64
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.connectors.google_oauth import (
    GOOGLE_OAUTH_ERROR_INVALID_GRANT,
    GoogleOAuthClientError,
    GoogleOAuthTokenResponse,
)
from app.contracts.gmail import (
    GMAIL_CREDENTIAL_PROVIDER_ID,
    GMAIL_CREDENTIAL_SCOPE,
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
from app.services.google_oauth_config import GoogleOAuthRuntimeConfig
from app.services.google_oauth_connection_status import (
    GoogleOAuthConnectionStatusReader,
)
from app.services.google_oauth_lifecycle import GoogleOAuthLifecycleService
from app.services.google_oauth_subjects import (
    GOOGLE_CALENDAR_OAUTH_SUBJECT,
    GOOGLE_GMAIL_OAUTH_SUBJECT,
)
from app.services.google_oauth_token_manager import (
    GOOGLE_OAUTH_TOKEN_ERROR_REAUTHORIZATION_REQUIRED,
    GoogleOAuthTokenManager,
    GoogleOAuthTokenManagerError,
)
from app.services.oauth_flow_state import OAuthFlowStateStore
from app.services.oauth_token_cipher import OAuthTokenCipher


class FakeLifecycleClient:
    def __init__(self):
        self.revoke_calls = 0

    def revoke_refresh_token(self, *, refresh_token):
        self.revoke_calls += 1


class FakeTokenManager:
    def __init__(self):
        self.clear_calls = 0

    def clear_cache(self):
        self.clear_calls += 1


class InvalidGrantClient:
    def __init__(self):
        self.calls = 0

    def refresh_access_token(self, config, *, refresh_token):
        self.calls += 1
        raise GoogleOAuthClientError(GOOGLE_OAUTH_ERROR_INVALID_GRANT)


class WrongScopeRefreshClient:
    def __init__(self):
        self.calls = 0

    def refresh_access_token(self, config, *, refresh_token):
        self.calls += 1
        return GoogleOAuthTokenResponse(
            access_token=SecretStr("gmail-access-secret"),
            expires_in=3600,
            token_type="Bearer",
            scopes=(GOOGLE_CALENDAR_CREDENTIAL_SCOPE,),
        )


class TrapGmailRecord:
    provider_id = GMAIL_CREDENTIAL_PROVIDER_ID
    plugin_id = GMAIL_PLUGIN_ID
    plugin_version = GMAIL_PLUGIN_VERSION
    capability_name = GMAIL_READ_CAPABILITY_NAME
    granted_scopes = GMAIL_CREDENTIAL_SCOPE
    cipher_version = "aesgcm-v1"
    status = "active"

    @property
    def encrypted_refresh_token(self):
        raise AssertionError("status must not read ciphertext")

    @property
    def encryption_nonce(self):
        raise AssertionError("status must not read nonce")


class FakeRepository:
    def __init__(self, record):
        self.record = record
        self.profile_ids = []

    def get(self, profile_id):
        self.profile_ids.append(profile_id)
        return self.record


class D76GmailCredentialFoundationAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 16, tzinfo=timezone.utc)
        self.key = SecretStr(
            base64.b64encode(os.urandom(32)).decode("ascii")
        )
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        OAuthCredentialRecord.__table__.create(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)

    def tearDown(self):
        self.engine.dispose()

    def config(self, subject):
        return GoogleOAuthRuntimeConfig(
            client_id="client-id",
            client_secret=SecretStr("client-secret"),
            redirect_uri=(
                "http://localhost:8000" + subject.callback_path
            ),
            token_encryption_key=self.key,
            subject=subject,
        )

    def save_record(self, subject, refresh_secret):
        session = self.Session()
        repository = OAuthCredentialRepository(session)
        cipher = OAuthTokenCipher.from_base64_key(self.key)
        encrypted = cipher.encrypt(
            SecretStr(refresh_secret),
            aad=subject.aad,
        )
        repository.save_active(
            profile_id=subject.profile_id,
            provider_id=subject.provider_id,
            plugin_id=subject.plugin_id,
            plugin_version=subject.plugin_version,
            capability_name=subject.capability_name,
            encrypted_refresh_token=encrypted.ciphertext,
            encryption_nonce=encrypted.nonce,
            cipher_version=encrypted.cipher_version,
            granted_scopes=subject.scope,
            refresh_token_expires_at=None,
            now=self.now,
        )
        repository.commit()
        session.close()

    def test_disconnects_are_subject_local_in_both_directions(self):
        self.save_record(
            GOOGLE_CALENDAR_OAUTH_SUBJECT,
            "calendar-refresh-secret",
        )
        self.save_record(
            GOOGLE_GMAIL_OAUTH_SUBJECT,
            "gmail-refresh-secret",
        )

        session = self.Session()
        repository = OAuthCredentialRepository(session)
        gmail_client = FakeLifecycleClient()
        gmail_manager = FakeTokenManager()
        gmail_service = GoogleOAuthLifecycleService(
            repository=repository,
            config=self.config(GOOGLE_GMAIL_OAUTH_SUBJECT),
            client=gmail_client,
            flow_state_store=OAuthFlowStateStore(clock=lambda: self.now),
            token_manager=gmail_manager,
            clock=lambda: self.now,
        )
        gmail_service.disconnect()
        self.assertIsNone(
            repository.get(GMAIL_READ_CREDENTIAL_PROFILE_ID)
        )
        self.assertIsNotNone(
            repository.get(GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID)
        )
        self.assertEqual(gmail_client.revoke_calls, 1)
        self.assertEqual(gmail_manager.clear_calls, 1)
        session.close()

        self.save_record(
            GOOGLE_GMAIL_OAUTH_SUBJECT,
            "gmail-refresh-secret-2",
        )
        session = self.Session()
        repository = OAuthCredentialRepository(session)
        calendar_client = FakeLifecycleClient()
        calendar_manager = FakeTokenManager()
        calendar_service = GoogleOAuthLifecycleService(
            repository=repository,
            config=self.config(GOOGLE_CALENDAR_OAUTH_SUBJECT),
            client=calendar_client,
            flow_state_store=OAuthFlowStateStore(clock=lambda: self.now),
            token_manager=calendar_manager,
            clock=lambda: self.now,
        )
        calendar_service.disconnect()
        self.assertIsNone(
            repository.get(GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID)
        )
        self.assertIsNotNone(
            repository.get(GMAIL_READ_CREDENTIAL_PROFILE_ID)
        )
        self.assertEqual(calendar_client.revoke_calls, 1)
        self.assertEqual(calendar_manager.clear_calls, 1)
        session.close()

    def test_gmail_invalid_grant_marks_only_gmail_reauthorization(self):
        self.save_record(
            GOOGLE_CALENDAR_OAUTH_SUBJECT,
            "calendar-refresh-secret",
        )
        self.save_record(
            GOOGLE_GMAIL_OAUTH_SUBJECT,
            "gmail-refresh-secret",
        )
        client = InvalidGrantClient()
        manager = GoogleOAuthTokenManager(
            session_factory=self.Session,
            config=self.config(GOOGLE_GMAIL_OAUTH_SUBJECT),
            client=client,
            clock=lambda: self.now,
        )
        with self.assertRaises(GoogleOAuthTokenManagerError) as caught:
            manager.resolve_access_token()
        self.assertEqual(
            caught.exception.code,
            GOOGLE_OAUTH_TOKEN_ERROR_REAUTHORIZATION_REQUIRED,
        )
        self.assertEqual(client.calls, 1)

        session = self.Session()
        repository = OAuthCredentialRepository(session)
        self.assertEqual(
            repository.get(GMAIL_READ_CREDENTIAL_PROFILE_ID).status,
            "reauthorization_required",
        )
        self.assertEqual(
            repository.get(
                GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID
            ).status,
            "active",
        )
        session.close()

    def test_gmail_refresh_scope_mismatch_fails_closed(self):
        self.save_record(
            GOOGLE_GMAIL_OAUTH_SUBJECT,
            "gmail-refresh-secret",
        )
        client = WrongScopeRefreshClient()
        manager = GoogleOAuthTokenManager(
            session_factory=self.Session,
            config=self.config(GOOGLE_GMAIL_OAUTH_SUBJECT),
            client=client,
            clock=lambda: self.now,
        )
        with self.assertRaises(GoogleOAuthTokenManagerError) as caught:
            manager.resolve_access_token()
        self.assertEqual(
            caught.exception.code,
            GOOGLE_OAUTH_TOKEN_ERROR_REAUTHORIZATION_REQUIRED,
        )
        self.assertEqual(client.calls, 1)

        session = self.Session()
        record = OAuthCredentialRepository(session).get(
            GMAIL_READ_CREDENTIAL_PROFILE_ID
        )
        self.assertEqual(record.status, "reauthorization_required")
        session.close()

    def test_gmail_status_reads_metadata_only(self):
        repository = FakeRepository(TrapGmailRecord())
        reader = GoogleOAuthConnectionStatusReader(
            repository,
            subject=GOOGLE_GMAIL_OAUTH_SUBJECT,
        )
        self.assertEqual(reader.read_status(), "active")
        self.assertEqual(
            repository.profile_ids,
            [GMAIL_READ_CREDENTIAL_PROFILE_ID],
        )

    def test_production_source_has_no_gmail_write_scope(self):
        root = Path(__file__).resolve().parents[2]
        app_root = root / "backend" / "app"
        production = "\n".join(
            path.read_text(encoding="utf-8")
            for path in app_root.rglob("*.py")
        )
        for forbidden in (
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.compose",
            "https://mail.google.com/",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, production)

    def test_no_gmail_static_execution_permission_or_migration_is_added(self):
        root = Path(__file__).resolve().parents[2]
        permission_source = (
            root
            / "backend"
            / "app"
            / "services"
            / "capability_permission_policy.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("gmail", permission_source.lower())

        migration_names = {
            path.name
            for path in (
                root / "backend" / "alembic" / "versions"
            ).glob("*.py")
        }
        self.assertFalse(
            any("gmail" in name.lower() for name in migration_names)
        )

    def test_gmail_control_api_does_not_accept_authority_selection_fields(self):
        root = Path(__file__).resolve().parents[2]
        source = (
            root
            / "backend"
            / "app"
            / "api"
            / "v1"
            / "gmail_oauth.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("profile_id", source)
        self.assertNotIn("secret_ref", source)
        self.assertNotIn("required_scopes", source)
        self.assertNotIn("gmail.modify", source)
        self.assertNotIn("gmail.send", source)
        self.assertNotIn("gmail.compose", source)


if __name__ == "__main__":
    unittest.main()
