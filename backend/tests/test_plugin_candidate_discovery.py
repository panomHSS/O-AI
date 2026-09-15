import unittest
from dataclasses import FrozenInstanceError

from app.api.dependencies import (
    get_plugin_candidate_discovery,
    get_plugin_discovery,
    get_plugin_projection_catalog,
)
from app.contracts.plugin_candidate import (
    PLUGIN_CANDIDATE_REASON_PROJECTION_MATCH,
    PLUGIN_CANDIDATE_REASON_PROJECTION_MISSING,
    PLUGIN_CANDIDATE_REASON_VERSION_MISMATCH,
    PLUGIN_CANDIDATE_STATUS_PROJECTED_MATCH,
    PLUGIN_CANDIDATE_STATUS_UNPROJECTED,
    PLUGIN_CANDIDATE_STATUS_VERSION_MISMATCH,
)
from app.contracts.plugin_projection import PluginCapabilityProjection
from app.plugins.plugin_manifest import PluginManifest
from app.services.adapter_registry import AdapterRegistry
from app.services.capability_permission_policy import (
    PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS,
)
from app.services.plugin_candidate_discovery import (
    PLUGIN_CANDIDATE_ERROR_DISCOVERY_FAILED,
    PLUGIN_CANDIDATE_ERROR_DUPLICATE_MANIFEST,
    PLUGIN_CANDIDATE_ERROR_INVALID_DISCOVERY_RESULT,
    PLUGIN_CANDIDATE_ERROR_INVALID_MANIFEST,
    PluginCandidateDiscovery,
    PluginCandidateDiscoveryError,
)
from app.services.plugin_projection_catalog import PluginProjectionCatalog


class RecordingDiscovery:
    def __init__(
        self,
        manifests: list[PluginManifest] | None = None,
        *,
        error: Exception | None = None,
        result: object | None = None,
    ) -> None:
        self._manifests = list(manifests or [])
        self._error = error
        self._result = result
        self.calls = 0

    def discover(self):
        self.calls += 1
        if self._error is not None:
            raise self._error
        if self._result is not None:
            return self._result
        return list(self._manifests)


class PluginCandidateDiscoveryTests(unittest.TestCase):
    @staticmethod
    def projection(
        *,
        plugin_id: str = "echo",
        plugin_version: str = "1.0.0",
        capability_name: str = "echo",
        module_adapter_id: str = "module.plugin.echo",
        operation: str = "echo",
    ) -> PluginCapabilityProjection:
        return PluginCapabilityProjection(
            plugin_id=plugin_id,
            plugin_version=plugin_version,
            capability_name=capability_name,
            description=f"{capability_name} capability.",
            module_adapter_id=module_adapter_id,
            operation=operation,
        )

    @classmethod
    def service(
        cls,
        manifests: list[PluginManifest],
        *,
        projections: tuple[PluginCapabilityProjection, ...] | None = None,
    ) -> tuple[PluginCandidateDiscovery, RecordingDiscovery]:
        discovery = RecordingDiscovery(manifests)
        catalog = PluginProjectionCatalog(
            projections if projections is not None else (cls.projection(),)
        )
        return (
            PluginCandidateDiscovery(
                discovery=discovery,
                projection_catalog=catalog,
            ),
            discovery,
        )

    def test_production_composition_discovers_known_connector_candidates(self) -> None:
        service = get_plugin_candidate_discovery()

        self.assertIs(service, get_plugin_candidate_discovery())
        self.assertIs(get_plugin_discovery(), get_plugin_discovery())
        self.assertIs(
            get_plugin_projection_catalog(),
            get_plugin_projection_catalog(),
        )
        candidates = service.discover_candidates()
        self.assertEqual(len(candidates), 2)
        self.assertEqual(
            tuple(candidate.plugin_id for candidate in candidates),
            ("github_public_repo", "google_calendar"),
        )
        expected = {
            "github_public_repo": ("repository_metadata",),
            "google_calendar": ("upcoming_events",),
        }
        for candidate in candidates:
            self.assertEqual(candidate.plugin_version, "1.0.0")
            self.assertEqual(
                candidate.status,
                PLUGIN_CANDIDATE_STATUS_PROJECTED_MATCH,
            )
            self.assertEqual(
                candidate.projected_capability_names,
                expected[candidate.plugin_id],
            )
            self.assertEqual(
                candidate.reason_code,
                PLUGIN_CANDIDATE_REASON_PROJECTION_MATCH,
            )

    def test_exact_projection_version_is_projected_match(self) -> None:
        service, discovery = self.service(
            [PluginManifest(plugin_id="echo", version="1.0.0")]
        )

        candidate = service.discover_candidates()[0]

        self.assertEqual(discovery.calls, 1)
        self.assertEqual(candidate.plugin_id, "echo")
        self.assertEqual(candidate.plugin_version, "1.0.0")
        self.assertEqual(
            candidate.status,
            PLUGIN_CANDIDATE_STATUS_PROJECTED_MATCH,
        )
        self.assertEqual(candidate.projected_capability_names, ("echo",))
        self.assertEqual(
            candidate.reason_code,
            PLUGIN_CANDIDATE_REASON_PROJECTION_MATCH,
        )

    def test_unknown_plugin_is_unprojected(self) -> None:
        service, _ = self.service(
            [PluginManifest(plugin_id="unknown", version="1.0.0")]
        )

        candidate = service.discover_candidates()[0]

        self.assertEqual(candidate.status, PLUGIN_CANDIDATE_STATUS_UNPROJECTED)
        self.assertEqual(candidate.projected_capability_names, ())
        self.assertEqual(
            candidate.reason_code,
            PLUGIN_CANDIDATE_REASON_PROJECTION_MISSING,
        )

    def test_version_mismatch_does_not_fallback(self) -> None:
        service, _ = self.service(
            [PluginManifest(plugin_id="echo", version="2.0.0")]
        )

        candidate = service.discover_candidates()[0]

        self.assertEqual(
            candidate.status,
            PLUGIN_CANDIDATE_STATUS_VERSION_MISMATCH,
        )
        self.assertEqual(candidate.projected_capability_names, ())
        self.assertEqual(
            candidate.reason_code,
            PLUGIN_CANDIDATE_REASON_VERSION_MISMATCH,
        )

    def test_multiple_exact_capabilities_are_sorted_deterministically(self) -> None:
        projections = (
            self.projection(
                capability_name="search",
                module_adapter_id="module.plugin.echo.search",
                operation="search",
            ),
            self.projection(),
            self.projection(
                capability_name="inspect",
                module_adapter_id="module.plugin.echo.inspect",
                operation="inspect",
            ),
        )
        service, _ = self.service(
            [PluginManifest(plugin_id="echo", version="1.0.0")],
            projections=projections,
        )

        candidate = service.discover_candidates()[0]

        self.assertEqual(
            candidate.projected_capability_names,
            ("echo", "inspect", "search"),
        )

    def test_candidates_are_sorted_by_plugin_identity(self) -> None:
        service, _ = self.service(
            [
                PluginManifest(plugin_id="zeta", version="1.0.0"),
                PluginManifest(plugin_id="alpha", version="1.0.0"),
            ],
            projections=(),
        )

        candidates = service.discover_candidates()

        self.assertEqual(
            tuple(candidate.plugin_id for candidate in candidates),
            ("alpha", "zeta"),
        )

    def test_candidate_is_immutable(self) -> None:
        service, _ = self.service(
            [PluginManifest(plugin_id="echo", version="1.0.0")]
        )
        candidate = service.discover_candidates()[0]

        with self.assertRaises(FrozenInstanceError):
            candidate.plugin_id = "changed"  # type: ignore[misc]

    def test_invalid_plugin_id_fails_closed(self) -> None:
        service, _ = self.service(
            [PluginManifest(plugin_id=" echo ", version="1.0.0")]
        )

        with self.assertRaises(PluginCandidateDiscoveryError) as caught:
            service.discover_candidates()

        self.assertEqual(
            caught.exception.code,
            PLUGIN_CANDIDATE_ERROR_INVALID_MANIFEST,
        )

    def test_invalid_plugin_version_fails_closed(self) -> None:
        service, _ = self.service(
            [PluginManifest(plugin_id="echo", version="")]
        )

        with self.assertRaises(PluginCandidateDiscoveryError) as caught:
            service.discover_candidates()

        self.assertEqual(
            caught.exception.code,
            PLUGIN_CANDIDATE_ERROR_INVALID_MANIFEST,
        )

    def test_non_manifest_discovery_item_fails_closed(self) -> None:
        discovery = RecordingDiscovery(result=[object()])
        service = PluginCandidateDiscovery(
            discovery=discovery,
            projection_catalog=PluginProjectionCatalog(()),
        )

        with self.assertRaises(PluginCandidateDiscoveryError) as caught:
            service.discover_candidates()

        self.assertEqual(
            caught.exception.code,
            PLUGIN_CANDIDATE_ERROR_INVALID_MANIFEST,
        )

    def test_duplicate_same_manifest_fails_closed(self) -> None:
        manifest = PluginManifest(plugin_id="echo", version="1.0.0")
        service, _ = self.service([manifest, manifest])

        with self.assertRaises(PluginCandidateDiscoveryError) as caught:
            service.discover_candidates()

        self.assertEqual(
            caught.exception.code,
            PLUGIN_CANDIDATE_ERROR_DUPLICATE_MANIFEST,
        )

    def test_same_plugin_id_with_two_versions_fails_closed(self) -> None:
        service, _ = self.service(
            [
                PluginManifest(plugin_id="echo", version="1.0.0"),
                PluginManifest(plugin_id="echo", version="2.0.0"),
            ]
        )

        with self.assertRaises(PluginCandidateDiscoveryError) as caught:
            service.discover_candidates()

        self.assertEqual(
            caught.exception.code,
            PLUGIN_CANDIDATE_ERROR_DUPLICATE_MANIFEST,
        )

    def test_discovery_failure_is_normalized_without_retry(self) -> None:
        discovery = RecordingDiscovery(
            error=RuntimeError("sensitive discovery failure")
        )
        service = PluginCandidateDiscovery(
            discovery=discovery,
            projection_catalog=PluginProjectionCatalog(()),
        )

        with self.assertRaises(PluginCandidateDiscoveryError) as caught:
            service.discover_candidates()

        self.assertEqual(discovery.calls, 1)
        self.assertEqual(
            caught.exception.code,
            PLUGIN_CANDIDATE_ERROR_DISCOVERY_FAILED,
        )
        self.assertNotIn("sensitive", str(caught.exception))

    def test_invalid_discovery_container_is_normalized(self) -> None:
        discovery = RecordingDiscovery(result=("not", "a", "list"))
        service = PluginCandidateDiscovery(
            discovery=discovery,
            projection_catalog=PluginProjectionCatalog(()),
        )

        with self.assertRaises(PluginCandidateDiscoveryError) as caught:
            service.discover_candidates()

        self.assertEqual(discovery.calls, 1)
        self.assertEqual(
            caught.exception.code,
            PLUGIN_CANDIDATE_ERROR_INVALID_DISCOVERY_RESULT,
        )

    def test_reconciliation_has_no_loader_registry_or_execution_surface(self) -> None:
        service, _ = self.service(
            [PluginManifest(plugin_id="echo", version="1.0.0")]
        )

        self.assertFalse(hasattr(service, "_loader"))
        self.assertFalse(hasattr(service, "_plugin_registry"))
        self.assertFalse(hasattr(service, "_adapter_registry"))
        self.assertFalse(hasattr(service, "execute"))
        self.assertFalse(hasattr(service, "load"))
        self.assertFalse(hasattr(service, "register"))

    def test_projection_match_does_not_mutate_adapter_registry(self) -> None:
        registry = AdapterRegistry(())
        service, _ = self.service(
            [PluginManifest(plugin_id="echo", version="1.0.0")]
        )

        candidate = service.discover_candidates()[0]

        self.assertEqual(
            candidate.status,
            PLUGIN_CANDIDATE_STATUS_PROJECTED_MATCH,
        )
        self.assertEqual(registry.adapter_ids, ())
        self.assertIsNone(registry.resolve_module("module.plugin.echo"))

    def test_candidate_metadata_does_not_create_capability_permission(self) -> None:
        projections = (
            self.projection(
                plugin_id="candidate",
                plugin_version="1.0.0",
                capability_name="inspect",
                module_adapter_id="module.plugin.candidate",
                operation="inspect",
            ),
        )
        service, _ = self.service(
            [PluginManifest(plugin_id="candidate", version="1.0.0")],
            projections=projections,
        )

        candidate = service.discover_candidates()[0]

        self.assertEqual(
            candidate.status,
            PLUGIN_CANDIDATE_STATUS_PROJECTED_MATCH,
        )
        self.assertFalse(
            any(
                permission.adapter_id == "module.plugin.candidate"
                for permission in PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS
            )
        )


if __name__ == "__main__":
    unittest.main()
