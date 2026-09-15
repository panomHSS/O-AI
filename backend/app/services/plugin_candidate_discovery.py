"""D53 fail-closed, read-only Plugin discovery candidate reconciliation."""

from __future__ import annotations

from app.contracts.plugin_candidate import (
    PLUGIN_CANDIDATE_REASON_PROJECTION_MATCH,
    PLUGIN_CANDIDATE_REASON_PROJECTION_MISSING,
    PLUGIN_CANDIDATE_REASON_VERSION_MISMATCH,
    PLUGIN_CANDIDATE_STATUS_PROJECTED_MATCH,
    PLUGIN_CANDIDATE_STATUS_UNPROJECTED,
    PLUGIN_CANDIDATE_STATUS_VERSION_MISMATCH,
    PluginDiscoveryCandidate,
)
from app.plugins.plugin_discovery import PluginDiscovery
from app.plugins.plugin_manifest import PluginManifest
from app.services.plugin_projection_catalog import PluginProjectionCatalog


PLUGIN_CANDIDATE_ERROR_DISCOVERY_FAILED = "discovery_failed"
PLUGIN_CANDIDATE_ERROR_INVALID_DISCOVERY_RESULT = "invalid_discovery_result"
PLUGIN_CANDIDATE_ERROR_INVALID_MANIFEST = "invalid_plugin_manifest"
PLUGIN_CANDIDATE_ERROR_DUPLICATE_MANIFEST = "duplicate_plugin_manifest"


class PluginCandidateDiscoveryError(ValueError):
    """Safe D53 discovery/reconciliation error with a stable reason code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class PluginCandidateDiscovery:
    """Validate discovered manifests and reconcile them with D52 metadata only.

    This service does not load Plugins, mutate PluginRegistry or AdapterRegistry,
    create capability permissions, approve or authorize plans, or execute code.
    """

    def __init__(
        self,
        *,
        discovery: PluginDiscovery,
        projection_catalog: PluginProjectionCatalog,
    ) -> None:
        self._discovery = discovery
        self._projection_catalog = projection_catalog

    def discover_candidates(self) -> tuple[PluginDiscoveryCandidate, ...]:
        """Discover exactly once, reconcile deterministically, and return metadata."""

        try:
            manifests = self._discovery.discover()
        except Exception:
            raise PluginCandidateDiscoveryError(
                PLUGIN_CANDIDATE_ERROR_DISCOVERY_FAILED
            ) from None

        if not isinstance(manifests, list):
            raise PluginCandidateDiscoveryError(
                PLUGIN_CANDIDATE_ERROR_INVALID_DISCOVERY_RESULT
            )

        seen_plugin_ids: set[str] = set()
        candidates: list[PluginDiscoveryCandidate] = []
        projections = self._projection_catalog.projections

        for manifest in manifests:
            plugin_id, plugin_version = self._validate_manifest(manifest)
            if plugin_id in seen_plugin_ids:
                raise PluginCandidateDiscoveryError(
                    PLUGIN_CANDIDATE_ERROR_DUPLICATE_MANIFEST
                )
            seen_plugin_ids.add(plugin_id)

            plugin_projections = tuple(
                projection
                for projection in projections
                if projection.plugin_id == plugin_id
            )
            exact_projections = tuple(
                projection
                for projection in plugin_projections
                if projection.plugin_version == plugin_version
            )

            if exact_projections:
                candidates.append(
                    PluginDiscoveryCandidate(
                        plugin_id=plugin_id,
                        plugin_version=plugin_version,
                        status=PLUGIN_CANDIDATE_STATUS_PROJECTED_MATCH,
                        projected_capability_names=tuple(
                            sorted(
                                projection.capability_name
                                for projection in exact_projections
                            )
                        ),
                        reason_code=PLUGIN_CANDIDATE_REASON_PROJECTION_MATCH,
                    )
                )
            elif plugin_projections:
                candidates.append(
                    PluginDiscoveryCandidate(
                        plugin_id=plugin_id,
                        plugin_version=plugin_version,
                        status=PLUGIN_CANDIDATE_STATUS_VERSION_MISMATCH,
                        projected_capability_names=(),
                        reason_code=PLUGIN_CANDIDATE_REASON_VERSION_MISMATCH,
                    )
                )
            else:
                candidates.append(
                    PluginDiscoveryCandidate(
                        plugin_id=plugin_id,
                        plugin_version=plugin_version,
                        status=PLUGIN_CANDIDATE_STATUS_UNPROJECTED,
                        projected_capability_names=(),
                        reason_code=PLUGIN_CANDIDATE_REASON_PROJECTION_MISSING,
                    )
                )

        return tuple(
            sorted(
                candidates,
                key=lambda candidate: (
                    candidate.plugin_id,
                    candidate.plugin_version,
                ),
            )
        )

    @staticmethod
    def _validate_manifest(manifest: object) -> tuple[str, str]:
        if not isinstance(manifest, PluginManifest):
            raise PluginCandidateDiscoveryError(
                PLUGIN_CANDIDATE_ERROR_INVALID_MANIFEST
            )

        plugin_id = manifest.plugin_id
        plugin_version = manifest.version
        if (
            not isinstance(plugin_id, str)
            or not plugin_id
            or plugin_id != plugin_id.strip()
            or not isinstance(plugin_version, str)
            or not plugin_version
            or plugin_version != plugin_version.strip()
        ):
            raise PluginCandidateDiscoveryError(
                PLUGIN_CANDIDATE_ERROR_INVALID_MANIFEST
            )
        return plugin_id, plugin_version
