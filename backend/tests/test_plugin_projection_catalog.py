import unittest
from dataclasses import FrozenInstanceError

from app.api.dependencies import get_plugin_projection_catalog
from app.contracts.plugin_projection import (
    PLUGIN_PROJECTION_ERROR_INVALID_ADAPTER_ID,
    PLUGIN_PROJECTION_ERROR_INVALID_CAPABILITY_NAME,
    PLUGIN_PROJECTION_ERROR_INVALID_PLUGIN_ID,
    PluginCapabilityProjection,
    PluginProjectionContractError,
)
from app.plugins.echo import EchoPlugin
from app.plugins.in_memory_registry import InMemoryPluginRegistry
from app.services.adapter_registry import AdapterRegistry
from app.services.capability_permission_policy import (
    PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS,
)
from app.services.plugin_projection_catalog import (
    PLUGIN_PROJECTION_ERROR_DUPLICATE,
    PLUGIN_PROJECTION_ERROR_NOT_FOUND,
    PRODUCTION_PLUGIN_CAPABILITY_PROJECTIONS,
    PluginProjectionCatalog,
    PluginProjectionCatalogError,
)


class PluginProjectionCatalogTests(unittest.TestCase):
    @staticmethod
    def projection(
        *,
        plugin_id: str = "echo",
        plugin_version: str = "1.0.0",
        capability_name: str = "echo",
        description: str = "Echo text.",
        module_adapter_id: str = "module.plugin.echo",
        operation: str = "echo",
    ) -> PluginCapabilityProjection:
        return PluginCapabilityProjection(
            plugin_id=plugin_id,
            plugin_version=plugin_version,
            capability_name=capability_name,
            description=description,
            module_adapter_id=module_adapter_id,
            operation=operation,
        )

    def test_production_catalog_contains_fixed_echo_and_d59_connector(self) -> None:
        catalog = get_plugin_projection_catalog()

        self.assertEqual(
            catalog.projections,
            PRODUCTION_PLUGIN_CAPABILITY_PROJECTIONS,
        )
        self.assertEqual(
            catalog.identities,
            (
                ("echo", "echo"),
                ("github_public_repo", "repository_metadata"),
                ("google_calendar", "upcoming_events"),
            ),
        )

        echo = catalog.resolve("echo", "echo")
        self.assertEqual(echo.plugin_version, "1.0.0")
        self.assertEqual(echo.module_adapter_id, "module.plugin.echo")
        self.assertEqual(echo.operation, "echo")

        connector = catalog.resolve(
            "github_public_repo",
            "repository_metadata",
        )
        self.assertEqual(connector.plugin_version, "1.0.0")
        self.assertEqual(
            connector.module_adapter_id,
            "module.plugin.github_public_repo",
        )
        self.assertEqual(
            connector.operation,
            "get_repository_metadata",
        )

        calendar = catalog.resolve(
            "google_calendar",
            "upcoming_events",
        )
        self.assertEqual(calendar.plugin_version, "1.0.0")
        self.assertEqual(
            calendar.module_adapter_id,
            "module.plugin.google_calendar",
        )
        self.assertEqual(
            calendar.operation,
            "list_upcoming_events",
        )

    def test_catalog_returns_deterministic_order(self) -> None:
        catalog = PluginProjectionCatalog(
            (
                self.projection(
                    plugin_id="zeta",
                    capability_name="inspect",
                    module_adapter_id="module.plugin.zeta",
                    operation="inspect",
                ),
                self.projection(),
            )
        )

        self.assertEqual(
            catalog.identities,
            (("echo", "echo"), ("zeta", "inspect")),
        )

    def test_duplicate_plugin_capability_identity_is_rejected(self) -> None:
        first = self.projection()
        duplicate = self.projection(
            module_adapter_id="module.plugin.echo.second",
            operation="echo_second",
        )

        with self.assertRaises(PluginProjectionCatalogError) as caught:
            PluginProjectionCatalog((first, duplicate))

        self.assertEqual(caught.exception.code, PLUGIN_PROJECTION_ERROR_DUPLICATE)

    def test_duplicate_module_operation_target_is_rejected(self) -> None:
        first = self.projection()
        duplicate = self.projection(
            plugin_id="echo-alias",
            capability_name="echo_alias",
        )

        with self.assertRaises(PluginProjectionCatalogError) as caught:
            PluginProjectionCatalog((first, duplicate))

        self.assertEqual(caught.exception.code, PLUGIN_PROJECTION_ERROR_DUPLICATE)

    def test_projection_contract_rejects_invalid_identifiers(self) -> None:
        cases = (
            (
                {"plugin_id": " echo "},
                PLUGIN_PROJECTION_ERROR_INVALID_PLUGIN_ID,
            ),
            (
                {"capability_name": ""},
                PLUGIN_PROJECTION_ERROR_INVALID_CAPABILITY_NAME,
            ),
            (
                {"module_adapter_id": "tool.plugin.echo"},
                PLUGIN_PROJECTION_ERROR_INVALID_ADAPTER_ID,
            ),
        )

        for changes, expected_code in cases:
            with self.subTest(changes=changes):
                with self.assertRaises(PluginProjectionContractError) as caught:
                    self.projection(**changes)
                self.assertEqual(caught.exception.code, expected_code)

    def test_projection_descriptor_is_frozen(self) -> None:
        projection = self.projection()

        with self.assertRaises(FrozenInstanceError):
            projection.plugin_id = "changed"  # type: ignore[misc]

    def test_unknown_projection_fails_closed_with_safe_reason(self) -> None:
        catalog = PluginProjectionCatalog((self.projection(),))

        with self.assertRaises(PluginProjectionCatalogError) as caught:
            catalog.resolve("unknown", "echo")

        self.assertEqual(caught.exception.code, PLUGIN_PROJECTION_ERROR_NOT_FOUND)

    def test_plugin_registry_registration_does_not_create_projection(self) -> None:
        plugin = EchoPlugin()
        registry = InMemoryPluginRegistry()
        registry.register(plugin)
        catalog = PluginProjectionCatalog(())

        self.assertIs(registry.resolve("echo"), plugin)
        self.assertEqual(catalog.projections, ())
        with self.assertRaises(PluginProjectionCatalogError):
            catalog.resolve("echo", "echo")

    def test_projection_catalog_does_not_mutate_adapter_registry(self) -> None:
        registry = AdapterRegistry(())
        catalog = PluginProjectionCatalog((self.projection(),))

        self.assertEqual(catalog.identities, (("echo", "echo"),))
        self.assertEqual(registry.adapter_ids, ())
        self.assertIsNone(registry.resolve_module("module.plugin.echo"))

    def test_projection_metadata_does_not_create_capability_permission(self) -> None:
        catalog = PluginProjectionCatalog(
            (
                self.projection(
                    plugin_id="candidate",
                    capability_name="inspect",
                    module_adapter_id="module.plugin.candidate",
                    operation="inspect",
                ),
            )
        )

        self.assertEqual(
            catalog.resolve("candidate", "inspect").module_adapter_id,
            "module.plugin.candidate",
        )
        self.assertFalse(
            any(
                permission.adapter_id == "module.plugin.candidate"
                for permission in PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS
            )
        )

    def test_catalog_has_no_runtime_or_mutation_surface(self) -> None:
        catalog = PluginProjectionCatalog((self.projection(),))

        self.assertFalse(hasattr(catalog, "execute"))
        self.assertFalse(hasattr(catalog, "register"))
        self.assertFalse(hasattr(catalog, "unregister"))
        self.assertFalse(hasattr(catalog, "runtime"))


if __name__ == "__main__":
    unittest.main()
