import unittest
from dataclasses import FrozenInstanceError

from app.contracts.credential import (
    CredentialContractError,
    CredentialProfile,
)
from app.services.credential_profile_catalog import (
    CREDENTIAL_PROFILE_ERROR_DUPLICATE_PROFILE_ID,
    CREDENTIAL_PROFILE_ERROR_DUPLICATE_SUBJECT,
    CREDENTIAL_PROFILE_ERROR_NOT_FOUND,
    PRODUCTION_CREDENTIAL_PROFILES,
    CredentialProfileCatalog,
    CredentialProfileCatalogError,
)


class CredentialProfileCatalogTests(unittest.TestCase):
    @staticmethod
    def profile(
        *,
        profile_id="synthetic.read",
        plugin_id="synthetic",
        plugin_version="1.0.0",
        capability_name="read",
        secret_ref="synthetic.read.secret",
    ) -> CredentialProfile:
        return CredentialProfile(
            profile_id=profile_id,
            plugin_id=plugin_id,
            plugin_version=plugin_version,
            capability_name=capability_name,
            provider_id="synthetic_provider",
            auth_scheme="oauth2_bearer",
            required_scopes=("scope.read",),
            secret_ref=secret_ref,
        )

    def test_production_catalog_is_empty_default_deny(self) -> None:
        self.assertEqual(PRODUCTION_CREDENTIAL_PROFILES, ())
        self.assertEqual(
            CredentialProfileCatalog(
                PRODUCTION_CREDENTIAL_PROFILES
            ).profiles,
            (),
        )

    def test_exact_subject_resolves_profile(self) -> None:
        profile = self.profile()
        catalog = CredentialProfileCatalog((profile,))
        self.assertIs(
            catalog.resolve("synthetic", "1.0.0", "read"),
            profile,
        )

    def test_unknown_or_mismatched_subject_fails_closed(self) -> None:
        catalog = CredentialProfileCatalog((self.profile(),))
        for subject in (
            ("other", "1.0.0", "read"),
            ("synthetic", "2.0.0", "read"),
            ("synthetic", "1.0.0", "write"),
        ):
            with self.subTest(subject=subject):
                with self.assertRaises(
                    CredentialProfileCatalogError
                ) as caught:
                    catalog.resolve(*subject)
                self.assertEqual(
                    caught.exception.code,
                    CREDENTIAL_PROFILE_ERROR_NOT_FOUND,
                )

    def test_duplicate_profile_id_is_rejected(self) -> None:
        with self.assertRaises(
            CredentialProfileCatalogError
        ) as caught:
            CredentialProfileCatalog(
                (
                    self.profile(),
                    self.profile(
                        plugin_id="other",
                        capability_name="other",
                    ),
                )
            )
        self.assertEqual(
            caught.exception.code,
            CREDENTIAL_PROFILE_ERROR_DUPLICATE_PROFILE_ID,
        )

    def test_duplicate_subject_is_rejected(self) -> None:
        with self.assertRaises(
            CredentialProfileCatalogError
        ) as caught:
            CredentialProfileCatalog(
                (
                    self.profile(),
                    self.profile(
                        profile_id="synthetic.read.other",
                        secret_ref="other.secret",
                    ),
                )
            )
        self.assertEqual(
            caught.exception.code,
            CREDENTIAL_PROFILE_ERROR_DUPLICATE_SUBJECT,
        )

    def test_profile_is_immutable_and_scopes_are_deterministic(self) -> None:
        profile = CredentialProfile(
            profile_id="synthetic.read",
            plugin_id="synthetic",
            plugin_version="1.0.0",
            capability_name="read",
            provider_id="synthetic_provider",
            auth_scheme="oauth2_bearer",
            required_scopes=("scope.z", "scope.a"),
            secret_ref="synthetic.read.secret",
        )
        self.assertEqual(
            profile.required_scopes,
            ("scope.a", "scope.z"),
        )
        with self.assertRaises(FrozenInstanceError):
            profile.provider_id = "changed"  # type: ignore[misc]

    def test_duplicate_scopes_are_rejected(self) -> None:
        with self.assertRaises(CredentialContractError) as caught:
            CredentialProfile(
                profile_id="synthetic.read",
                plugin_id="synthetic",
                plugin_version="1.0.0",
                capability_name="read",
                provider_id="synthetic_provider",
                auth_scheme="oauth2_bearer",
                required_scopes=("scope.read", "scope.read"),
                secret_ref="synthetic.read.secret",
            )
        self.assertEqual(
            caught.exception.code,
            "invalid_credential_required_scopes",
        )


if __name__ == "__main__":
    unittest.main()
