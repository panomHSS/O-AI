import unittest
from dataclasses import FrozenInstanceError

from app.api.dependencies import (
    get_plugin_module_exposure_store,
    get_plugin_permission_binding_service,
    get_plugin_permission_binding_store,
    get_plugin_permission_profile_catalog,
)
from app.contracts.capability_permission import ExecutableCapabilityPermission
from app.contracts.plugin_module_exposure import PluginModuleExposureRecord
from app.contracts.plugin_permission_binding import (
    PluginCapabilityPermissionBinding,
    PluginCapabilityPermissionProfile,
    PluginPermissionBindingContractError,
)
from app.services.adapter_registry import AdapterRegistry
from app.services.capability_permission_policy import PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS
from app.services.execution_approval_service import PendingExecutionApprovalStore
from app.services.plugin_module_exposure import PluginModuleExposureError
from app.services.plugin_permission_binding import (
    PLUGIN_PERMISSION_BINDING_ERROR_CAPABILITY_ID_RESERVED,
    PLUGIN_PERMISSION_BINDING_ERROR_DUPLICATE_CAPABILITY_ID,
    PLUGIN_PERMISSION_BINDING_ERROR_DUPLICATE_ROUTE,
    PLUGIN_PERMISSION_BINDING_ERROR_EXPOSURE_INACTIVE,
    PLUGIN_PERMISSION_BINDING_ERROR_EXPOSURE_NOT_FOUND,
    PLUGIN_PERMISSION_BINDING_ERROR_EXPOSURE_RESOLUTION_FAILED,
    PLUGIN_PERMISSION_BINDING_ERROR_INVALID_CAPABILITY_NAME,
    PLUGIN_PERMISSION_BINDING_ERROR_INVALID_PLUGIN_ID,
    PLUGIN_PERMISSION_BINDING_ERROR_INVALID_PLUGIN_VERSION,
    PLUGIN_PERMISSION_BINDING_ERROR_PROFILE_NOT_FOUND,
    PLUGIN_PERMISSION_BINDING_ERROR_PROFILE_TARGET_MISMATCH,
    PLUGIN_PERMISSION_BINDING_ERROR_ROUTE_RESERVED,
    PLUGIN_PERMISSION_BINDING_ERROR_STORE_FULL,
    PLUGIN_PERMISSION_BINDING_ERROR_SUBJECT_MISMATCH,
    PLUGIN_PERMISSION_PROFILE_ERROR_DUPLICATE_CAPABILITY_ID,
    PLUGIN_PERMISSION_PROFILE_ERROR_DUPLICATE_ROUTE,
    PLUGIN_PERMISSION_PROFILE_ERROR_DUPLICATE_SOURCE,
    PRODUCTION_PLUGIN_CAPABILITY_PERMISSION_PROFILES,
    PluginPermissionBindingError,
    PluginPermissionBindingService,
    PluginPermissionBindingStore,
    PluginPermissionProfileCatalog,
    PluginPermissionProfileCatalogError,
)


class FakeExposureService:
    def __init__(self, record, *, error=None) -> None:
        self.record = record
        self.error = error
        self.calls = 0
        self.execute_calls = 0

    def _resolve_active_record_for_binding(self, plugin_id, plugin_version, capability_name):
        self.calls += 1
        if self.error is not None:
            raise self.error
        if self.record is None:
            return None
        if (self.record.plugin_id, self.record.plugin_version, self.record.capability_name) != (plugin_id, plugin_version, capability_name):
            return None
        return self.record


class PluginPermissionBindingTests(unittest.TestCase):
    @staticmethod
    def exposure(*, plugin_id="synthetic", plugin_version="1.0.0", capability_name="read", capabilities=("read",), adapter_id="module.plugin.synthetic", operation="read"):
        return PluginModuleExposureRecord(
            plugin_id=plugin_id,
            plugin_version=plugin_version,
            capability_name=capability_name,
            projected_capability_names=capabilities,
            module_adapter_id=adapter_id,
            module_name=adapter_id.removeprefix("module."),
            operation=operation,
        )

    @staticmethod
    def profile(*, plugin_id="synthetic", plugin_version="1.0.0", capability_name="read", capability_id="exec.plugin.synthetic.read", adapter_id="module.plugin.synthetic", operation="read"):
        return PluginCapabilityPermissionProfile(
            plugin_id=plugin_id,
            plugin_version=plugin_version,
            capability_name=capability_name,
            capability_id=capability_id,
            module_adapter_id=adapter_id,
            operation=operation,
            effect="read",
            data_class="external_data",
            owner_approval_required=True,
        )

    @staticmethod
    def binding(*, plugin_id="synthetic", capability_name="read", capabilities=("read",), capability_id="exec.plugin.synthetic.read", adapter_id="module.plugin.synthetic", operation="read"):
        return PluginCapabilityPermissionBinding(
            plugin_id=plugin_id,
            plugin_version="1.0.0",
            capability_name=capability_name,
            projected_capability_names=capabilities,
            capability_id=capability_id,
            module_adapter_id=adapter_id,
            operation=operation,
            effect="read",
            data_class="external_data",
            owner_approval_required=True,
        )

    @classmethod
    def service(cls, *, exposure=None, exposure_error=None, profiles=None, store=None, reserved_permissions=()):
        if exposure is None:
            exposure = cls.exposure()
        exposure_service = FakeExposureService(exposure, error=exposure_error)
        catalog = PluginPermissionProfileCatalog(profiles if profiles is not None else (cls.profile(),))
        store = store if store is not None else PluginPermissionBindingStore()
        service = PluginPermissionBindingService(
            exposure_service=exposure_service,
            profile_catalog=catalog,
            store=store,
            reserved_permissions=reserved_permissions,
        )
        return service, exposure_service, catalog, store

    def test_production_d59_profile_is_known_but_binding_remains_default_deny(self):
        get_plugin_permission_binding_store().clear()
        get_plugin_module_exposure_store().clear()
        self.assertEqual(
            get_plugin_permission_profile_catalog().profiles,
            PRODUCTION_PLUGIN_CAPABILITY_PERMISSION_PROFILES,
        )
        self.assertEqual(len(PRODUCTION_PLUGIN_CAPABILITY_PERMISSION_PROFILES), 1)
        profile = PRODUCTION_PLUGIN_CAPABILITY_PERMISSION_PROFILES[0]
        self.assertEqual(profile.plugin_id, "github_public_repo")
        self.assertEqual(profile.plugin_version, "1.0.0")
        self.assertEqual(profile.capability_name, "repository_metadata")
        self.assertEqual(
            profile.capability_id,
            "exec.plugin.github_public_repo.repository_metadata",
        )
        self.assertEqual(
            profile.module_adapter_id,
            "module.plugin.github_public_repo",
        )
        self.assertEqual(profile.operation, "get_repository_metadata")
        self.assertEqual(profile.effect, "read")
        self.assertEqual(profile.data_class, "external_data")
        self.assertTrue(profile.owner_approval_required)
        self.assertEqual(
            get_plugin_permission_binding_service().list_bindings(),
            (),
        )
        with self.assertRaises(PluginPermissionBindingError) as caught:
            get_plugin_permission_binding_service().bind(
                "github_public_repo",
                "1.0.0",
                "repository_metadata",
            )
        self.assertEqual(
            caught.exception.code,
            PLUGIN_PERMISSION_BINDING_ERROR_EXPOSURE_NOT_FOUND,
        )

    def test_exact_active_exposure_and_profile_bind(self):
        service, exposure_service, _, store = self.service()
        binding = service.bind("synthetic", "1.0.0", "read")
        self.assertEqual(exposure_service.calls, 1)
        self.assertEqual(store.count, 1)
        self.assertEqual(binding.capability_id, "exec.plugin.synthetic.read")
        self.assertTrue(binding.owner_approval_required)

    def test_binding_is_immutable_metadata_only(self):
        binding = self.binding()
        self.assertFalse(hasattr(binding, "execute"))
        self.assertFalse(hasattr(binding, "plugin"))
        self.assertFalse(hasattr(binding, "adapter"))
        with self.assertRaises(FrozenInstanceError):
            binding.operation = "changed"

    def test_profile_requires_owner_approval(self):
        with self.assertRaises(PluginPermissionBindingContractError) as caught:
            PluginCapabilityPermissionProfile(
                plugin_id="synthetic", plugin_version="1.0.0", capability_name="read",
                capability_id="exec.synthetic", module_adapter_id="module.synthetic", operation="read",
                effect="read", data_class="external_data", owner_approval_required=False,
            )
        self.assertEqual(caught.exception.code, "binding_owner_approval_must_be_required")

    def test_missing_exposure_cannot_bind(self):
        service, exposure_service, _, store = self.service()
        exposure_service.record = None
        with self.assertRaises(PluginPermissionBindingError) as caught:
            service.bind("synthetic", "1.0.0", "read")
        self.assertEqual(store.count, 0)
        self.assertEqual(caught.exception.code, PLUGIN_PERMISSION_BINDING_ERROR_EXPOSURE_NOT_FOUND)

    def test_inactive_exposure_cannot_bind(self):
        service, _, _, store = self.service(exposure_error=PluginModuleExposureError("exposure_subject_mismatch"))
        with self.assertRaises(PluginPermissionBindingError) as caught:
            service.bind("synthetic", "1.0.0", "read")
        self.assertEqual(store.count, 0)
        self.assertEqual(caught.exception.code, PLUGIN_PERMISSION_BINDING_ERROR_EXPOSURE_INACTIVE)

    def test_unexpected_exposure_failure_is_normalized(self):
        service, _, _, _ = self.service(exposure_error=RuntimeError("sensitive"))
        with self.assertRaises(PluginPermissionBindingError) as caught:
            service.bind("synthetic", "1.0.0", "read")
        self.assertEqual(caught.exception.code, PLUGIN_PERMISSION_BINDING_ERROR_EXPOSURE_RESOLUTION_FAILED)
        self.assertNotIn("sensitive", str(caught.exception))

    def test_missing_profile_cannot_bind(self):
        service, _, _, store = self.service(profiles=())
        with self.assertRaises(PluginPermissionBindingError) as caught:
            service.bind("synthetic", "1.0.0", "read")
        self.assertEqual(store.count, 0)
        self.assertEqual(caught.exception.code, PLUGIN_PERMISSION_BINDING_ERROR_PROFILE_NOT_FOUND)

    def test_profile_target_must_match(self):
        cases = (
            self.profile(adapter_id="module.other"),
            self.profile(operation="other"),
        )
        for profile in cases:
            with self.subTest(profile=profile):
                service, _, _, store = self.service(profiles=(profile,))
                with self.assertRaises(PluginPermissionBindingError) as caught:
                    service.bind("synthetic", "1.0.0", "read")
                self.assertEqual(store.count, 0)
                self.assertEqual(caught.exception.code, PLUGIN_PERMISSION_BINDING_ERROR_PROFILE_TARGET_MISMATCH)

    def test_reserved_d44_capability_id_cannot_bind(self):
        service, _, _, _ = self.service(
            profiles=(self.profile(capability_id="exec.plugin.echo"),),
            reserved_permissions=PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS,
        )
        with self.assertRaises(PluginPermissionBindingError) as caught:
            service.bind("synthetic", "1.0.0", "read")
        self.assertEqual(caught.exception.code, PLUGIN_PERMISSION_BINDING_ERROR_CAPABILITY_ID_RESERVED)

    def test_reserved_d44_module_route_cannot_bind(self):
        exposure = self.exposure(adapter_id="module.plugin.echo", operation="echo")
        profile = self.profile(capability_id="exec.dynamic.echo", adapter_id="module.plugin.echo", operation="echo")
        service, _, _, _ = self.service(exposure=exposure, profiles=(profile,), reserved_permissions=PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS)
        with self.assertRaises(PluginPermissionBindingError) as caught:
            service.bind("synthetic", "1.0.0", "read")
        self.assertEqual(caught.exception.code, PLUGIN_PERMISSION_BINDING_ERROR_ROUTE_RESERVED)

    def test_fixed_d51_echo_permission_not_reused(self):
        exposure = self.exposure(plugin_id="echo", capability_name="echo", capabilities=("echo",), adapter_id="module.plugin.echo", operation="echo")
        profile = self.profile(plugin_id="echo", capability_name="echo", capability_id="exec.plugin.echo", adapter_id="module.plugin.echo", operation="echo")
        service, _, _, _ = self.service(exposure=exposure, profiles=(profile,), reserved_permissions=PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS)
        with self.assertRaises(PluginPermissionBindingError) as caught:
            service.bind("echo", "1.0.0", "echo")
        self.assertEqual(caught.exception.code, PLUGIN_PERMISSION_BINDING_ERROR_CAPABILITY_ID_RESERVED)

    def test_duplicate_exact_binding_idempotent_after_revalidation(self):
        service, exposure_service, _, store = self.service()
        first = service.bind("synthetic", "1.0.0", "read")
        second = service.bind("synthetic", "1.0.0", "read")
        self.assertIs(first, second)
        self.assertEqual(exposure_service.calls, 2)
        self.assertEqual(store.count, 1)

    def test_existing_binding_fails_on_exposure_drift(self):
        service, exposure_service, _, store = self.service()
        service.bind("synthetic", "1.0.0", "read")
        exposure_service.record = self.exposure(capabilities=("other", "read"))
        with self.assertRaises(PluginPermissionBindingError) as caught:
            service.bind("synthetic", "1.0.0", "read")
        self.assertEqual(store.count, 1)
        self.assertEqual(caught.exception.code, PLUGIN_PERMISSION_BINDING_ERROR_SUBJECT_MISMATCH)

    def test_store_rejects_duplicate_capability_id(self):
        store = PluginPermissionBindingStore()
        store.add(self.binding())
        with self.assertRaises(PluginPermissionBindingError) as caught:
            store.add(self.binding(plugin_id="other", capability_name="other", capabilities=("other",), capability_id="exec.plugin.synthetic.read", adapter_id="module.other", operation="other"))
        self.assertEqual(caught.exception.code, PLUGIN_PERMISSION_BINDING_ERROR_DUPLICATE_CAPABILITY_ID)

    def test_store_rejects_duplicate_route(self):
        store = PluginPermissionBindingStore()
        store.add(self.binding())
        with self.assertRaises(PluginPermissionBindingError) as caught:
            store.add(self.binding(plugin_id="other", capability_name="other", capabilities=("other",), capability_id="exec.other", adapter_id="module.plugin.synthetic", operation="read"))
        self.assertEqual(caught.exception.code, PLUGIN_PERMISSION_BINDING_ERROR_DUPLICATE_ROUTE)

    def test_store_bounded_without_eviction(self):
        store = PluginPermissionBindingStore(max_bindings=1)
        store.add(self.binding())
        with self.assertRaises(PluginPermissionBindingError) as caught:
            store.add(self.binding(plugin_id="other", capability_name="other", capabilities=("other",), capability_id="exec.other", adapter_id="module.other", operation="other"))
        self.assertEqual(store.count, 1)
        self.assertEqual(caught.exception.code, PLUGIN_PERMISSION_BINDING_ERROR_STORE_FULL)

    def test_store_listing_deterministic(self):
        store = PluginPermissionBindingStore()
        store.add(self.binding(plugin_id="zeta", capability_name="z", capabilities=("z",), capability_id="exec.z", adapter_id="module.z", operation="z"))
        store.add(self.binding(plugin_id="alpha", capability_name="a", capabilities=("a",), capability_id="exec.a", adapter_id="module.a", operation="a"))
        self.assertEqual(tuple(item.plugin_id for item in store.list_bindings()), ("alpha", "zeta"))

    def test_profile_catalog_uniqueness(self):
        cases = (
            ((self.profile(), self.profile(capability_id="exec.other", adapter_id="module.other", operation="other")), PLUGIN_PERMISSION_PROFILE_ERROR_DUPLICATE_SOURCE),
            ((self.profile(), self.profile(plugin_id="other", capability_name="other", capability_id="exec.plugin.synthetic.read", adapter_id="module.other", operation="other")), PLUGIN_PERMISSION_PROFILE_ERROR_DUPLICATE_CAPABILITY_ID),
            ((self.profile(), self.profile(plugin_id="other", capability_name="other", capability_id="exec.other")), PLUGIN_PERMISSION_PROFILE_ERROR_DUPLICATE_ROUTE),
        )
        for profiles, expected in cases:
            with self.subTest(expected=expected):
                with self.assertRaises(PluginPermissionProfileCatalogError) as caught:
                    PluginPermissionProfileCatalog(profiles)
                self.assertEqual(caught.exception.code, expected)

    def test_invalid_subject_fails_before_exposure_lookup(self):
        service, exposure_service, _, _ = self.service()
        cases = (
            (" synthetic ", "1.0.0", "read", PLUGIN_PERMISSION_BINDING_ERROR_INVALID_PLUGIN_ID),
            ("synthetic", "", "read", PLUGIN_PERMISSION_BINDING_ERROR_INVALID_PLUGIN_VERSION),
            ("synthetic", "1.0.0", " read ", PLUGIN_PERMISSION_BINDING_ERROR_INVALID_CAPABILITY_NAME),
        )
        for plugin_id, version, capability, expected in cases:
            with self.subTest(expected=expected):
                with self.assertRaises(PluginPermissionBindingError) as caught:
                    service.bind(plugin_id, version, capability)
                self.assertEqual(caught.exception.code, expected)
        self.assertEqual(exposure_service.calls, 0)

    def test_binding_does_not_mutate_registry_d44_or_d45(self):
        service, _, _, _ = self.service()
        registry = AdapterRegistry(())
        before = PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS
        approvals = PendingExecutionApprovalStore()
        service.bind("synthetic", "1.0.0", "read")
        self.assertEqual(registry.adapter_ids, ())
        self.assertIs(PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS, before)
        self.assertEqual(approvals.pending_count, 0)

    def test_service_has_no_registration_or_execution_surface(self):
        service, exposure_service, _, _ = self.service()
        binding = service.bind("synthetic", "1.0.0", "read")
        self.assertIsInstance(binding, PluginCapabilityPermissionBinding)
        for name in ("register", "permit", "approve", "authorize", "execute"):
            self.assertFalse(hasattr(service, name))
        self.assertEqual(exposure_service.execute_calls, 0)

    def test_reserved_tool_route_does_not_block_module_binding(self):
        reserved_tool = ExecutableCapabilityPermission(
            capability_id="exec.tool.only", target_kind="tool", adapter_id="tool.same.name",
            operation="read", effect="read", data_class="external_data", owner_approval_required=True,
        )
        service, _, _, _ = self.service(reserved_permissions=(reserved_tool,))
        binding = service.bind("synthetic", "1.0.0", "read")
        self.assertEqual(binding.module_adapter_id, "module.plugin.synthetic")


if __name__ == "__main__":
    unittest.main()
