import unittest
from unittest.mock import patch

from pydantic import SecretStr

from app.api import dependencies
from app.services.credential_access_broker import (
    CREDENTIAL_ACCESS_ERROR_PROFILE_NOT_FOUND,
    CREDENTIAL_ACCESS_ERROR_SECRET_NOT_FOUND,
    CredentialAccessError,
    LazyCredentialSecretSource,
)
from app.services.credential_profile_catalog import (
    PRODUCTION_CREDENTIAL_PROFILES,
)


class CredentialDependencyWiringTests(unittest.TestCase):
    def setUp(self) -> None:
        dependencies.get_credential_access_broker.cache_clear()
        dependencies.get_credential_profile_catalog.cache_clear()
        dependencies.get_credential_secret_source.cache_clear()

    def tearDown(self) -> None:
        dependencies.get_credential_access_broker.cache_clear()
        dependencies.get_credential_profile_catalog.cache_clear()
        dependencies.get_credential_secret_source.cache_clear()

    def test_production_catalog_contains_only_exact_d63_profile(self) -> None:
        self.assertEqual(len(PRODUCTION_CREDENTIAL_PROFILES), 1)
        self.assertEqual(
            dependencies.get_credential_profile_catalog().profiles,
            PRODUCTION_CREDENTIAL_PROFILES,
        )
        self.assertIsInstance(
            dependencies.get_credential_secret_source(),
            LazyCredentialSecretSource,
        )

    def test_unknown_subject_still_fails_before_secret_lookup(self) -> None:
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

    def test_google_secret_is_lazy_and_missing_token_fails_closed(self) -> None:
        class Settings:
            oai_google_calendar_access_token = None

        with patch.object(
            dependencies,
            "get_settings",
            return_value=Settings(),
        ):
            broker = dependencies.get_credential_access_broker()
            with self.assertRaises(CredentialAccessError) as caught:
                broker.resolve(
                    "google_calendar",
                    "1.0.0",
                    "upcoming_events",
                )
        self.assertEqual(
            caught.exception.code,
            CREDENTIAL_ACCESS_ERROR_SECRET_NOT_FOUND,
        )

    def test_google_secret_resolves_only_through_exact_profile(self) -> None:
        token = SecretStr("dependency-secret-never-log")

        class Settings:
            oai_google_calendar_access_token = token

        with patch.object(
            dependencies,
            "get_settings",
            return_value=Settings(),
        ):
            resolved = dependencies.get_credential_access_broker().resolve(
                "google_calendar",
                "1.0.0",
                "upcoming_events",
            )
        self.assertEqual(
            resolved.secret.get_secret_value(),
            "dependency-secret-never-log",
        )
        self.assertNotIn(
            "dependency-secret-never-log",
            repr(resolved),
        )


if __name__ == "__main__":
    unittest.main()
