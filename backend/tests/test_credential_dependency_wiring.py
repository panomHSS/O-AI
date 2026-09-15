import unittest

from app.api.dependencies import (
    get_credential_access_broker,
    get_credential_profile_catalog,
    get_credential_secret_source,
)
from app.services.credential_access_broker import (
    CREDENTIAL_ACCESS_ERROR_PROFILE_NOT_FOUND,
    CredentialAccessError,
    EmptyCredentialSecretSource,
)
from app.services.credential_profile_catalog import (
    PRODUCTION_CREDENTIAL_PROFILES,
)


class CredentialDependencyWiringTests(unittest.TestCase):
    def setUp(self) -> None:
        get_credential_access_broker.cache_clear()
        get_credential_profile_catalog.cache_clear()
        get_credential_secret_source.cache_clear()

    def tearDown(self) -> None:
        get_credential_access_broker.cache_clear()
        get_credential_profile_catalog.cache_clear()
        get_credential_secret_source.cache_clear()

    def test_production_catalog_and_source_are_default_deny(self) -> None:
        self.assertEqual(PRODUCTION_CREDENTIAL_PROFILES, ())
        self.assertEqual(
            get_credential_profile_catalog().profiles,
            (),
        )
        self.assertIsInstance(
            get_credential_secret_source(),
            EmptyCredentialSecretSource,
        )

    def test_production_broker_has_no_resolvable_subject(self) -> None:
        with self.assertRaises(CredentialAccessError) as caught:
            get_credential_access_broker().resolve(
                "synthetic",
                "1.0.0",
                "read",
            )
        self.assertEqual(
            caught.exception.code,
            CREDENTIAL_ACCESS_ERROR_PROFILE_NOT_FOUND,
        )


if __name__ == "__main__":
    unittest.main()
