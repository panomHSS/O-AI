import inspect
import unittest

from pydantic import SecretStr

from app.contracts.credential import CredentialProfile
from app.services.credential_access_broker import (
    CREDENTIAL_ACCESS_ERROR_INVALID_CAPABILITY_NAME,
    CREDENTIAL_ACCESS_ERROR_INVALID_PLUGIN_ID,
    CREDENTIAL_ACCESS_ERROR_INVALID_PLUGIN_VERSION,
    CREDENTIAL_ACCESS_ERROR_INVALID_SECRET,
    CREDENTIAL_ACCESS_ERROR_PROFILE_NOT_FOUND,
    CREDENTIAL_ACCESS_ERROR_SECRET_NOT_FOUND,
    CREDENTIAL_ACCESS_ERROR_SECRET_RESOLUTION_FAILED,
    CredentialAccessBroker,
    CredentialAccessError,
    EmptyCredentialSecretSource,
    StaticCredentialSecretSource,
)
from app.services.credential_profile_catalog import (
    CredentialProfileCatalog,
)


class TrackingSecretSource:
    def __init__(self, value=None, *, error=None) -> None:
        self.value = value
        self.error = error
        self.calls = []

    def resolve(self, secret_ref):
        self.calls.append(secret_ref)
        if self.error is not None:
            raise self.error
        return self.value


class CredentialAccessBrokerTests(unittest.TestCase):
    SECRET_VALUE = "synthetic-secret-value-never-log"

    @staticmethod
    def profile() -> CredentialProfile:
        return CredentialProfile(
            profile_id="synthetic.read",
            plugin_id="synthetic",
            plugin_version="1.0.0",
            capability_name="read",
            provider_id="synthetic_provider",
            auth_scheme="oauth2_bearer",
            required_scopes=("scope.read",),
            secret_ref="synthetic.read.secret",
        )

    @classmethod
    def broker(cls, *, source=None, profiles=None):
        catalog = CredentialProfileCatalog(
            profiles if profiles is not None else (cls.profile(),)
        )
        source = source if source is not None else StaticCredentialSecretSource(
            {
                "synthetic.read.secret": SecretStr(cls.SECRET_VALUE),
            }
        )
        return CredentialAccessBroker(
            profile_catalog=catalog,
            secret_source=source,
        )

    def test_exact_subject_resolves_masked_secret(self) -> None:
        resolved = self.broker().resolve(
            "synthetic",
            "1.0.0",
            "read",
        )
        self.assertEqual(resolved.profile_id, "synthetic.read")
        self.assertEqual(resolved.plugin_id, "synthetic")
        self.assertEqual(resolved.provider_id, "synthetic_provider")
        self.assertEqual(resolved.auth_scheme, "oauth2_bearer")
        self.assertEqual(resolved.required_scopes, ("scope.read",))
        self.assertFalse(hasattr(resolved, "secret_ref"))
        self.assertEqual(
            resolved.secret.get_secret_value(),
            self.SECRET_VALUE,
        )
        self.assertNotIn(self.SECRET_VALUE, repr(resolved))
        self.assertNotIn(self.SECRET_VALUE, str(resolved))

    def test_broker_surface_has_no_caller_credential_selector(self) -> None:
        parameters = inspect.signature(
            CredentialAccessBroker.resolve
        ).parameters
        self.assertEqual(
            tuple(parameters),
            (
                "self",
                "plugin_id",
                "plugin_version",
                "capability_name",
            ),
        )
        self.assertNotIn("profile_id", parameters)
        self.assertNotIn("secret_ref", parameters)
        self.assertNotIn("token", parameters)

    def test_unknown_subject_does_not_touch_secret_source(self) -> None:
        source = TrackingSecretSource(SecretStr(self.SECRET_VALUE))
        broker = self.broker(source=source)
        with self.assertRaises(CredentialAccessError) as caught:
            broker.resolve("synthetic", "2.0.0", "read")
        self.assertEqual(
            caught.exception.code,
            CREDENTIAL_ACCESS_ERROR_PROFILE_NOT_FOUND,
        )
        self.assertEqual(source.calls, [])

    def test_missing_secret_fails_closed(self) -> None:
        source = TrackingSecretSource(None)
        broker = self.broker(source=source)
        with self.assertRaises(CredentialAccessError) as caught:
            broker.resolve("synthetic", "1.0.0", "read")
        self.assertEqual(
            caught.exception.code,
            CREDENTIAL_ACCESS_ERROR_SECRET_NOT_FOUND,
        )
        self.assertEqual(source.calls, ["synthetic.read.secret"])

    def test_empty_production_style_source_is_default_deny(self) -> None:
        broker = self.broker(source=EmptyCredentialSecretSource())
        with self.assertRaises(CredentialAccessError) as caught:
            broker.resolve("synthetic", "1.0.0", "read")
        self.assertEqual(
            caught.exception.code,
            CREDENTIAL_ACCESS_ERROR_SECRET_NOT_FOUND,
        )

    def test_secret_source_failure_is_normalized_without_leak(self) -> None:
        source = TrackingSecretSource(
            error=RuntimeError(self.SECRET_VALUE)
        )
        broker = self.broker(source=source)
        with self.assertRaises(CredentialAccessError) as caught:
            broker.resolve("synthetic", "1.0.0", "read")
        self.assertEqual(
            caught.exception.code,
            CREDENTIAL_ACCESS_ERROR_SECRET_RESOLUTION_FAILED,
        )
        self.assertNotIn(self.SECRET_VALUE, str(caught.exception))
        self.assertNotIn(self.SECRET_VALUE, repr(caught.exception))

    def test_non_secretstr_and_empty_secret_are_rejected(self) -> None:
        for value in ("plain-text-secret", SecretStr("")):
            with self.subTest(value_type=type(value).__name__):
                source = TrackingSecretSource(value)
                broker = self.broker(source=source)
                with self.assertRaises(CredentialAccessError) as caught:
                    broker.resolve("synthetic", "1.0.0", "read")
                self.assertEqual(
                    caught.exception.code,
                    CREDENTIAL_ACCESS_ERROR_INVALID_SECRET,
                )

    def test_invalid_subject_values_fail_before_source_access(self) -> None:
        cases = (
            (
                ("", "1.0.0", "read"),
                CREDENTIAL_ACCESS_ERROR_INVALID_PLUGIN_ID,
            ),
            (
                ("synthetic", " 1.0.0", "read"),
                CREDENTIAL_ACCESS_ERROR_INVALID_PLUGIN_VERSION,
            ),
            (
                ("synthetic", "1.0.0", " read"),
                CREDENTIAL_ACCESS_ERROR_INVALID_CAPABILITY_NAME,
            ),
        )
        for subject, expected_code in cases:
            with self.subTest(subject=subject):
                source = TrackingSecretSource(
                    SecretStr(self.SECRET_VALUE)
                )
                broker = self.broker(source=source)
                with self.assertRaises(CredentialAccessError) as caught:
                    broker.resolve(*subject)
                self.assertEqual(caught.exception.code, expected_code)
                self.assertEqual(source.calls, [])

    def test_static_source_requires_secretstr_values(self) -> None:
        with self.assertRaises(TypeError):
            StaticCredentialSecretSource(
                {"synthetic.read.secret": self.SECRET_VALUE}
            )


if __name__ == "__main__":
    unittest.main()
