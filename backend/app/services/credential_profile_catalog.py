"""D62 immutable exact-match credential profile catalog."""

from __future__ import annotations

from collections.abc import Iterable

from app.contracts.credential import CredentialProfile

CREDENTIAL_PROFILE_ERROR_NOT_FOUND = "credential_profile_not_found"
CREDENTIAL_PROFILE_ERROR_DUPLICATE_PROFILE_ID = (
    "duplicate_credential_profile_id"
)
CREDENTIAL_PROFILE_ERROR_DUPLICATE_SUBJECT = (
    "duplicate_credential_profile_subject"
)


class CredentialProfileCatalogError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


PRODUCTION_CREDENTIAL_PROFILES: tuple[CredentialProfile, ...] = ()


class CredentialProfileCatalog:
    """Immutable O-AI-controlled credential-profile snapshot."""

    def __init__(
        self,
        profiles: Iterable[CredentialProfile] = (),
    ) -> None:
        by_subject: dict[
            tuple[str, str, str],
            CredentialProfile,
        ] = {}
        profile_ids: set[str] = set()

        for profile in profiles:
            if not isinstance(profile, CredentialProfile):
                raise TypeError(
                    "D62 profiles must be CredentialProfile values."
                )
            subject = (
                profile.plugin_id,
                profile.plugin_version,
                profile.capability_name,
            )
            if profile.profile_id in profile_ids:
                raise CredentialProfileCatalogError(
                    CREDENTIAL_PROFILE_ERROR_DUPLICATE_PROFILE_ID
                )
            if subject in by_subject:
                raise CredentialProfileCatalogError(
                    CREDENTIAL_PROFILE_ERROR_DUPLICATE_SUBJECT
                )
            profile_ids.add(profile.profile_id)
            by_subject[subject] = profile

        self._by_subject = by_subject
        self._profiles = tuple(
            sorted(
                by_subject.values(),
                key=lambda item: (
                    item.plugin_id,
                    item.plugin_version,
                    item.capability_name,
                ),
            )
        )

    @property
    def profiles(self) -> tuple[CredentialProfile, ...]:
        return self._profiles

    def resolve(
        self,
        plugin_id: str,
        plugin_version: str,
        capability_name: str,
    ) -> CredentialProfile:
        profile = self._by_subject.get(
            (plugin_id, plugin_version, capability_name)
        )
        if profile is None:
            raise CredentialProfileCatalogError(
                CREDENTIAL_PROFILE_ERROR_NOT_FOUND
            )
        return profile
