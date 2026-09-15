"""D55 explicit static Plugin factory loader.

D60 security freeze: factories are trusted in-process O-AI application code.
This exact allowlist is a loading boundary, not a Python or OS sandbox.
Untrusted third-party Plugin code is outside the supported production model.

This loader intentionally does not scan the filesystem, import a manifest-supplied
module path, install packages, use version ranges, or fall back to another Plugin.
"""

from __future__ import annotations

from collections.abc import Callable

from app.plugins.base import Plugin
from app.plugins.echo import EchoPlugin
from app.plugins.github_public_repository import GitHubPublicRepositoryPlugin
from app.plugins.google_calendar import GoogleCalendarPlugin
from app.services.credential_access_broker import (
    CredentialAccessBroker,
    EmptyCredentialSecretSource,
)
from app.services.credential_profile_catalog import (
    PRODUCTION_CREDENTIAL_PROFILES,
    CredentialProfileCatalog,
)
from app.plugins.plugin_loader import PluginLoader
from app.plugins.plugin_manifest import PluginManifest


PLUGIN_FACTORY_LOADER_ERROR_UNSUPPORTED_MANIFEST = (
    "loader_manifest_not_supported"
)


class ExplicitPluginFactoryLoaderError(ValueError):
    """Safe explicit-loader error with a stable reason code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


PluginFactory = Callable[[], Plugin]


def _default_google_calendar_factory() -> Plugin:
    """Safe default factory: known identity, no configured credential."""
    return GoogleCalendarPlugin(
        credential_broker=CredentialAccessBroker(
            profile_catalog=CredentialProfileCatalog(
                PRODUCTION_CREDENTIAL_PROFILES
            ),
            secret_source=EmptyCredentialSecretSource(),
        )
    )


class ExplicitPluginFactoryLoader(PluginLoader):
    """Load only exact id/version pairs from an explicit in-process allowlist."""

    def __init__(
        self,
        factories: dict[tuple[str, str], PluginFactory] | None = None,
        *,
        google_calendar_factory: PluginFactory | None = None,
    ) -> None:
        if factories is not None and google_calendar_factory is not None:
            raise ValueError(
                "Custom factories cannot be combined with the fixed "
                "Google Calendar factory seam."
            )
        if factories is None:
            calendar_factory = (
                _default_google_calendar_factory
                if google_calendar_factory is None
                else google_calendar_factory
            )
            source = {
                ("echo", "1.0.0"): EchoPlugin,
                ("github_public_repo", "1.0.0"): GitHubPublicRepositoryPlugin,
                ("google_calendar", "1.0.0"): calendar_factory,
            }
        else:
            source = dict(factories)
        validated: dict[tuple[str, str], PluginFactory] = {}
        for key, factory in source.items():
            if (
                not isinstance(key, tuple)
                or len(key) != 2
                or not isinstance(key[0], str)
                or not key[0]
                or key[0] != key[0].strip()
                or not isinstance(key[1], str)
                or not key[1]
                or key[1] != key[1].strip()
                or not callable(factory)
            ):
                raise ValueError("Explicit Plugin factory definition is invalid.")
            if key in validated:
                raise ValueError("Duplicate explicit Plugin factory definition.")
            validated[key] = factory
        self._factories = validated

    def load(self, manifest: PluginManifest) -> Plugin:
        """Instantiate exactly one explicitly configured Plugin identity."""

        if not isinstance(manifest, PluginManifest):
            raise ExplicitPluginFactoryLoaderError(
                PLUGIN_FACTORY_LOADER_ERROR_UNSUPPORTED_MANIFEST
            )
        factory = self._factories.get((manifest.plugin_id, manifest.version))
        if factory is None:
            raise ExplicitPluginFactoryLoaderError(
                PLUGIN_FACTORY_LOADER_ERROR_UNSUPPORTED_MANIFEST
            )
        return factory()
