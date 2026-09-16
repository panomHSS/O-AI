"""D52 immutable, metadata-only Plugin capability projection catalog."""

from __future__ import annotations

from collections.abc import Iterable

from app.contracts.gmail import (
    GMAIL_ADAPTER_ID,
    GMAIL_OPERATION,
    GMAIL_PLUGIN_ID,
    GMAIL_PLUGIN_VERSION,
    GMAIL_READ_CAPABILITY_NAME,
)
from app.contracts.google_calendar import (
    GOOGLE_CALENDAR_ADAPTER_ID,
    GOOGLE_CALENDAR_CAPABILITY_NAME,
    GOOGLE_CALENDAR_OPERATION,
    GOOGLE_CALENDAR_PLUGIN_ID,
    GOOGLE_CALENDAR_PLUGIN_VERSION,
)
from app.contracts.plugin_projection import (
    PLUGIN_PROJECTION_ERROR_INVALID_CAPABILITY_NAME,
    PLUGIN_PROJECTION_ERROR_INVALID_PLUGIN_ID,
    PluginCapabilityProjection,
    PluginProjectionContractError,
)


PLUGIN_PROJECTION_ERROR_DUPLICATE = "duplicate_plugin_projection"
PLUGIN_PROJECTION_ERROR_NOT_FOUND = "projection_not_found"


class PluginProjectionCatalogError(ValueError):
    """Safe D52 catalog error with a stable reason code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


PRODUCTION_PLUGIN_CAPABILITY_PROJECTIONS = (
    PluginCapabilityProjection(
        plugin_id="echo",
        plugin_version="1.0.0",
        capability_name="echo",
        description="Echo owner-supplied text through the fixed D51 reference bridge.",
        module_adapter_id="module.plugin.echo",
        operation="echo",
    ),
    PluginCapabilityProjection(
        plugin_id="github_public_repo",
        plugin_version="1.0.0",
        capability_name="repository_metadata",
        description="Read bounded metadata for one public GitHub repository.",
        module_adapter_id="module.plugin.github_public_repo",
        operation="get_repository_metadata",
    ),
    PluginCapabilityProjection(
        plugin_id=GMAIL_PLUGIN_ID,
        plugin_version=GMAIL_PLUGIN_VERSION,
        capability_name=GMAIL_READ_CAPABILITY_NAME,
        description="Read up to five bounded messages from the owner's Gmail.",
        module_adapter_id=GMAIL_ADAPTER_ID,
        operation=GMAIL_OPERATION,
    ),
    PluginCapabilityProjection(
        plugin_id=GOOGLE_CALENDAR_PLUGIN_ID,
        plugin_version=GOOGLE_CALENDAR_PLUGIN_VERSION,
        capability_name=GOOGLE_CALENDAR_CAPABILITY_NAME,
        description=(
            "Read the next bounded event window from the owner's primary "
            "Google Calendar."
        ),
        module_adapter_id=GOOGLE_CALENDAR_ADAPTER_ID,
        operation=GOOGLE_CALENDAR_OPERATION,
    ),
)


class PluginProjectionCatalog:
    """Immutable read-only snapshot of explicitly composed projection metadata.

    The catalog does not load Plugins, register ModuleAdapters, create capability
    permissions, approve plans, authorize execution, or invoke PluginRuntime.
    """

    def __init__(
        self,
        projections: Iterable[PluginCapabilityProjection] = (),
    ) -> None:
        by_source: dict[tuple[str, str], PluginCapabilityProjection] = {}
        target_keys: set[tuple[str, str]] = set()

        for projection in projections:
            if not isinstance(projection, PluginCapabilityProjection):
                raise TypeError(
                    "D52 catalog entries must be PluginCapabilityProjection values."
                )

            source_key = (projection.plugin_id, projection.capability_name)
            target_key = (projection.module_adapter_id, projection.operation)
            if source_key in by_source or target_key in target_keys:
                raise PluginProjectionCatalogError(
                    PLUGIN_PROJECTION_ERROR_DUPLICATE
                )

            by_source[source_key] = projection
            target_keys.add(target_key)

        self._by_source = by_source
        self._projections = tuple(
            sorted(
                by_source.values(),
                key=lambda item: (
                    item.plugin_id,
                    item.capability_name,
                    item.module_adapter_id,
                    item.operation,
                ),
            )
        )

    @property
    def projections(self) -> tuple[PluginCapabilityProjection, ...]:
        """Return the immutable projection snapshot in deterministic order."""

        return self._projections

    @property
    def identities(self) -> tuple[tuple[str, str], ...]:
        """Return Plugin/capability identities in deterministic order."""

        return tuple(
            (projection.plugin_id, projection.capability_name)
            for projection in self._projections
        )

    def resolve(
        self,
        plugin_id: str,
        capability_name: str,
    ) -> PluginCapabilityProjection:
        """Resolve metadata only; lookup never loads or executes a Plugin."""

        plugin_id = self._validated_lookup(
            plugin_id,
            code=PLUGIN_PROJECTION_ERROR_INVALID_PLUGIN_ID,
        )
        capability_name = self._validated_lookup(
            capability_name,
            code=PLUGIN_PROJECTION_ERROR_INVALID_CAPABILITY_NAME,
        )
        projection = self._by_source.get((plugin_id, capability_name))
        if projection is None:
            raise PluginProjectionCatalogError(
                PLUGIN_PROJECTION_ERROR_NOT_FOUND
            )
        return projection

    @staticmethod
    def _validated_lookup(value: object, *, code: str) -> str:
        if not isinstance(value, str) or not value or value != value.strip():
            raise PluginProjectionContractError(code)
        return value
