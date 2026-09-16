import unittest
from unittest.mock import patch

from pydantic import SecretStr

from app.api import dependencies
from app.services.credential_access_broker import (
    CREDENTIAL_ACCESS_ERROR_PROFILE_NOT_FOUND,
    CredentialAccessError,
    LazyCredentialSecretSource,
)
from app.services.credential_profile_catalog import (
    PRODUCTION_CREDENTIAL_PROFILES,
)


class FakeTokenManager:
    def __init__(self):
        self.calls = 0

    def resolve_access_token(self):
        self.calls += 1
        return SecretStr("managed-access-token-never-log")


class CredentialDependencyWiringTests(unittest.TestCase):
    def setUp(self) -> None:
        dependencies.get_credential_access_broker.cache_clear()
        dependencies.get_credential_profile_catalog.cache_clear()
        dependencies.get_credential_secret_source.cache_clear()
        dependencies.get_google_oauth_token_manager.cache_clear()
        dependencies.get_google_gmail_oauth_token_manager.cache_clear()

    def tearDown(self) -> None:
        dependencies.get_credential_access_broker.cache_clear()
        dependencies.get_credential_profile_catalog.cache_clear()
        dependencies.get_credential_secret_source.cache_clear()
        dependencies.get_google_oauth_token_manager.cache_clear()
        dependencies.get_google_gmail_oauth_token_manager.cache_clear()

    def test_production_catalog_and_source_keep_exact_managed_boundary(self) -> None:
        self.assertEqual(len(PRODUCTION_CREDENTIAL_PROFILES), 5)
        self.assertEqual(
            dependencies.get_credential_profile_catalog().profiles,
            PRODUCTION_CREDENTIAL_PROFILES,
        )
        self.assertIsInstance(
            dependencies.get_credential_secret_source(),
            LazyCredentialSecretSource,
        )

    def test_unknown_subject_does_not_resolve_managed_access_token(self) -> None:
        fake = FakeTokenManager()
        with patch.object(
            dependencies,
            "get_google_oauth_token_manager",
            return_value=fake,
        ):
            with self.assertRaises(CredentialAccessError) as caught:
                dependencies.get_credential_access_broker().resolve(
                    "synthetic",
                    "1.0.0",
                    "read",
                )
        self.assertEqual(
            caught.exception.code,
            CREDENTIAL_ACCESS_ERROR_PROFILE_NOT_FOUND,
        )
        self.assertEqual(fake.calls, 0)

    def test_exact_google_write_subjects_resolve_managed_access_token(self) -> None:
        for capability_name, profile_id in (
            ("create_event", "google_calendar.events.create"),
            ("delete_event", "google_calendar.events.delete"),
            ("update_event", "google_calendar.events.update"),
        ):
            with self.subTest(capability_name=capability_name):
                fake = FakeTokenManager()
                with patch.object(
                    dependencies,
                    "get_google_oauth_token_manager",
                    return_value=fake,
                ):
                    resolved = dependencies.get_credential_access_broker().resolve(
                        "google_calendar",
                        "1.0.0",
                        capability_name,
                    )
                self.assertEqual(fake.calls, 1)
                self.assertEqual(resolved.profile_id, profile_id)
                self.assertEqual(
                    resolved.secret.get_secret_value(),
                    "managed-access-token-never-log",
                )
                self.assertNotIn(
                    "managed-access-token-never-log",
                    repr(resolved),
                )

    def test_exact_google_read_subject_resolves_managed_access_token(self) -> None:
        fake = FakeTokenManager()
        with patch.object(
            dependencies,
            "get_google_oauth_token_manager",
            return_value=fake,
        ):
            resolved = dependencies.get_credential_access_broker().resolve(
                "google_calendar",
                "1.0.0",
                "upcoming_events",
            )
        self.assertEqual(fake.calls, 1)
        self.assertEqual(
            resolved.secret.get_secret_value(),
            "managed-access-token-never-log",
        )
        self.assertNotIn(
            "managed-access-token-never-log",
            repr(resolved),
        )


    def test_exact_gmail_read_subject_resolves_managed_access_token(self) -> None:
        fake = FakeTokenManager()
        with patch.object(
            dependencies,
            "get_google_gmail_oauth_token_manager",
            return_value=fake,
        ):
            dependencies.get_credential_secret_source.cache_clear()
            dependencies.get_credential_access_broker.cache_clear()
            resolved = dependencies.get_credential_access_broker().resolve(
                "gmail",
                "1.0.0",
                "read_messages",
            )
        self.assertEqual(fake.calls, 1)
        self.assertEqual(resolved.profile_id, "gmail.messages.readonly")
        self.assertEqual(
            resolved.secret.get_secret_value(),
            "managed-access-token-never-log",
        )
        self.assertNotIn(
            "managed-access-token-never-log",
            repr(resolved),
        )

if __name__ == "__main__":
    unittest.main()
