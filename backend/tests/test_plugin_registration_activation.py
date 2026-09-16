import unittest
from dataclasses import FrozenInstanceError
from types import SimpleNamespace
from unittest.mock import patch

from app.adapters.activated_plugin_module import PLUGIN_REGISTRATION_INACTIVE
from app.api.dependencies import (
    get_plugin_permission_binding_store,
    get_plugin_registration_activation_service,
    get_plugin_registration_activation_store,
    get_plugin_runtime_activation_snapshot,
)
from app.contracts.capability_permission import ExecutableCapabilityPermission
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep, Result
from app.contracts.plugin_permission_binding import PluginCapabilityPermissionBinding
from app.contracts.plugin_registration_activation import PluginRegistrationActivationRecord
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION
from app.services.adapter_registry import AdapterRegistry
from app.services.capability_permission_policy import (
    CapabilityPermissionPolicy,
    PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS,
)
from app.services.execution_approval_service import PendingExecutionApprovalStore
from app.services.plugin_module_exposure import PluginModuleExposureError
from app.services.plugin_permission_binding import PluginPermissionBindingError
from app.services.plugin_registration_activation import (
    PLUGIN_REGISTRATION_ACTIVATION_ERROR_ADAPTER_ID_RESERVED,
    PLUGIN_REGISTRATION_ACTIVATION_ERROR_ADAPTER_RESOLUTION_FAILED,
    PLUGIN_REGISTRATION_ACTIVATION_ERROR_BINDING_INACTIVE,
    PLUGIN_REGISTRATION_ACTIVATION_ERROR_BINDING_NOT_FOUND,
    PLUGIN_REGISTRATION_ACTIVATION_ERROR_BINDING_RESOLUTION_FAILED,
    PLUGIN_REGISTRATION_ACTIVATION_ERROR_CAPABILITY_ID_RESERVED,
    PLUGIN_REGISTRATION_ACTIVATION_ERROR_DUPLICATE_ADAPTER_ID,
    PLUGIN_REGISTRATION_ACTIVATION_ERROR_DUPLICATE_CAPABILITY_ID,
    PLUGIN_REGISTRATION_ACTIVATION_ERROR_EXPOSURE_INACTIVE,
    PLUGIN_REGISTRATION_ACTIVATION_ERROR_EXPOSURE_NOT_FOUND,
    PLUGIN_REGISTRATION_ACTIVATION_ERROR_INVALID_CAPABILITY_NAME,
    PLUGIN_REGISTRATION_ACTIVATION_ERROR_INVALID_PLUGIN_ID,
    PLUGIN_REGISTRATION_ACTIVATION_ERROR_INVALID_PLUGIN_VERSION,
    PLUGIN_REGISTRATION_ACTIVATION_ERROR_ROUTE_RESERVED,
    PLUGIN_REGISTRATION_ACTIVATION_ERROR_STORE_FULL,
    PLUGIN_REGISTRATION_ACTIVATION_ERROR_SUBJECT_MISMATCH,
    PluginRegistrationActivationError,
    PluginRegistrationActivationService,
    PluginRegistrationActivationStore,
)


class FakeModuleAdapter:
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION

    def __init__(self, adapter_id="module.plugin.synthetic", module_name="plugin.synthetic") -> None:
        self._adapter_id = adapter_id
        self._module_name = module_name
        self.execute_calls = 0

    @property
    def adapter_id(self):
        return self._adapter_id

    @property
    def module_name(self):
        return self._module_name

    def execute(self, request, plan):
        self.execute_calls += 1
        return Result(request_id=request.request_id, status="succeeded", output={"ok": True})


class FakeBindingService:
    def __init__(self, binding, error=None) -> None:
        self.binding = binding
        self.error = error
        self.calls = 0

    def _resolve_active_binding_for_activation(self, plugin_id, plugin_version, capability_name):
        self.calls += 1
        if self.error is not None:
            raise self.error
        if self.binding is None:
            return None
        if (self.binding.plugin_id, self.binding.plugin_version, self.binding.capability_name) != (plugin_id, plugin_version, capability_name):
            return None
        return self.binding


class FakeExposureService:
    def __init__(self, adapter, error=None) -> None:
        self.adapter = adapter
        self.error = error
        self.calls = 0

    def _resolve_active_adapter_for_registration(self, plugin_id, plugin_version, capability_name):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.adapter


class PluginRegistrationActivationTests(unittest.TestCase):
    @staticmethod
    def binding(
        *,
        plugin_id="synthetic",
        plugin_version="1.0.0",
        capability_name="read",
        capabilities=("read",),
        capability_id="exec.plugin.synthetic.read",
        adapter_id="module.plugin.synthetic",
        operation="read",
        effect="read",
        data_class="external_data",
    ):
        return PluginCapabilityPermissionBinding(
            plugin_id=plugin_id,
            plugin_version=plugin_version,
            capability_name=capability_name,
            projected_capability_names=capabilities,
            capability_id=capability_id,
            module_adapter_id=adapter_id,
            operation=operation,
            effect=effect,
            data_class=data_class,
            owner_approval_required=True,
        )

    @classmethod
    def service(
        cls,
        *,
        binding_marker="default",
        binding_error=None,
        adapter_marker="default",
        exposure_error=None,
        store=None,
        reserved_adapter_ids=(),
        reserved_permissions=(),
    ):
        binding = cls.binding() if binding_marker == "default" else binding_marker
        adapter = FakeModuleAdapter() if adapter_marker == "default" else adapter_marker
        binding_service = FakeBindingService(binding, error=binding_error)
        exposure_service = FakeExposureService(adapter, error=exposure_error)
        store = PluginRegistrationActivationStore() if store is None else store
        service = PluginRegistrationActivationService(
            binding_service=binding_service,  # type: ignore[arg-type]
            exposure_service=exposure_service,  # type: ignore[arg-type]
            store=store,
            reserved_adapter_ids=reserved_adapter_ids,
            reserved_permissions=reserved_permissions,
        )
        return service, binding_service, exposure_service, store, adapter

    @staticmethod
    def request_plan():
        request = CommandRequest(request_id="req-1", command="module.execute")
        plan = ExecutionPlan(
            request_id="req-1",
            adapter_id="module.plugin.synthetic",
            steps=(ExecutionStep(sequence=1, operation="read", parameters={"content": "hello"}),),
            owner_approval_required=False,
        )
        return request, plan

    def test_production_defaults_to_no_dynamic_activation(self):
        get_plugin_registration_activation_store().clear()
        get_plugin_permission_binding_store().clear()
        settings = SimpleNamespace(
            oai_github_public_repo_connector_enabled=False,
            oai_google_calendar_connector_enabled=False,
        )
        with patch(
            "app.api.dependencies.get_settings",
            return_value=settings,
        ):
            snapshot = get_plugin_runtime_activation_snapshot()

        self.assertEqual(snapshot.adapters, ())
        self.assertEqual(snapshot.permissions, ())
        with self.assertRaises(PluginRegistrationActivationError) as caught:
            get_plugin_registration_activation_service().activate(
                "echo",
                "1.0.0",
                "echo",
            )
        self.assertEqual(
            caught.exception.code,
            PLUGIN_REGISTRATION_ACTIVATION_ERROR_BINDING_NOT_FOUND,
        )

    def test_exact_current_binding_and_adapter_activate(self):
        service, bs, es, store, adapter = self.service()
        record = service.activate("synthetic", "1.0.0", "read")
        self.assertEqual((bs.calls, es.calls, store.count), (1, 1, 1))
        self.assertEqual(record.module_adapter_id, adapter.adapter_id)
        self.assertEqual(adapter.execute_calls, 0)

    def test_activation_record_is_immutable_metadata_only(self):
        service, _, _, _, _ = self.service()
        record = service.activate("synthetic", "1.0.0", "read")
        self.assertFalse(hasattr(record, "adapter"))
        self.assertFalse(hasattr(record, "plugin"))
        with self.assertRaises(FrozenInstanceError):
            record.operation = "other"  # type: ignore[misc]

    def test_missing_binding_cannot_activate(self):
        service, _, es, store, _ = self.service(binding_marker=None)
        with self.assertRaises(PluginRegistrationActivationError) as caught:
            service.activate("synthetic", "1.0.0", "read")
        self.assertEqual(caught.exception.code, PLUGIN_REGISTRATION_ACTIVATION_ERROR_BINDING_NOT_FOUND)
        self.assertEqual(es.calls, 0)
        self.assertEqual(store.count, 0)

    def test_inactive_binding_cannot_activate(self):
        service, _, es, _, _ = self.service(binding_error=PluginPermissionBindingError("binding_subject_mismatch"))
        with self.assertRaises(PluginRegistrationActivationError) as caught:
            service.activate("synthetic", "1.0.0", "read")
        self.assertEqual(caught.exception.code, PLUGIN_REGISTRATION_ACTIVATION_ERROR_BINDING_INACTIVE)
        self.assertEqual(es.calls, 0)

    def test_unexpected_binding_failure_is_normalized(self):
        service, _, _, _, _ = self.service(binding_error=RuntimeError("sensitive"))
        with self.assertRaises(PluginRegistrationActivationError) as caught:
            service.activate("synthetic", "1.0.0", "read")
        self.assertEqual(caught.exception.code, PLUGIN_REGISTRATION_ACTIVATION_ERROR_BINDING_RESOLUTION_FAILED)
        self.assertNotIn("sensitive", str(caught.exception))

    def test_missing_exposure_adapter_cannot_activate(self):
        service, _, _, store, _ = self.service(adapter_marker=None)
        with self.assertRaises(PluginRegistrationActivationError) as caught:
            service.activate("synthetic", "1.0.0", "read")
        self.assertEqual(caught.exception.code, PLUGIN_REGISTRATION_ACTIVATION_ERROR_EXPOSURE_NOT_FOUND)
        self.assertEqual(store.count, 0)

    def test_inactive_exposure_cannot_activate(self):
        service, _, _, _, _ = self.service(exposure_error=PluginModuleExposureError("exposure_subject_mismatch"))
        with self.assertRaises(PluginRegistrationActivationError) as caught:
            service.activate("synthetic", "1.0.0", "read")
        self.assertEqual(caught.exception.code, PLUGIN_REGISTRATION_ACTIVATION_ERROR_EXPOSURE_INACTIVE)

    def test_unexpected_adapter_failure_is_normalized(self):
        service, _, _, _, _ = self.service(exposure_error=RuntimeError("sensitive"))
        with self.assertRaises(PluginRegistrationActivationError) as caught:
            service.activate("synthetic", "1.0.0", "read")
        self.assertEqual(caught.exception.code, PLUGIN_REGISTRATION_ACTIVATION_ERROR_ADAPTER_RESOLUTION_FAILED)

    def test_binding_and_adapter_id_must_match(self):
        service, _, _, _, _ = self.service(adapter_marker=FakeModuleAdapter(adapter_id="module.other", module_name="other"))
        with self.assertRaises(PluginRegistrationActivationError) as caught:
            service.activate("synthetic", "1.0.0", "read")
        self.assertEqual(caught.exception.code, PLUGIN_REGISTRATION_ACTIVATION_ERROR_SUBJECT_MISMATCH)

    def test_reserved_static_adapter_id_cannot_activate(self):
        service, _, _, _, _ = self.service(reserved_adapter_ids=("module.plugin.synthetic",))
        with self.assertRaises(PluginRegistrationActivationError) as caught:
            service.activate("synthetic", "1.0.0", "read")
        self.assertEqual(caught.exception.code, PLUGIN_REGISTRATION_ACTIVATION_ERROR_ADAPTER_ID_RESERVED)

    def test_reserved_adapter_id_blocks_different_operation(self):
        binding = self.binding(operation="other")
        service, _, _, _, _ = self.service(binding_marker=binding, reserved_adapter_ids=("module.plugin.synthetic",))
        with self.assertRaises(PluginRegistrationActivationError) as caught:
            service.activate("synthetic", "1.0.0", "read")
        self.assertEqual(caught.exception.code, PLUGIN_REGISTRATION_ACTIVATION_ERROR_ADAPTER_ID_RESERVED)

    def test_reserved_capability_id_cannot_activate(self):
        reserved = ExecutableCapabilityPermission(
            capability_id="exec.plugin.synthetic.read",
            target_kind="module",
            adapter_id="module.other",
            operation="other",
            effect="read",
            data_class="external_data",
            owner_approval_required=True,
        )
        service, _, _, _, _ = self.service(reserved_permissions=(reserved,))
        with self.assertRaises(PluginRegistrationActivationError) as caught:
            service.activate("synthetic", "1.0.0", "read")
        self.assertEqual(caught.exception.code, PLUGIN_REGISTRATION_ACTIVATION_ERROR_CAPABILITY_ID_RESERVED)

    def test_reserved_module_route_cannot_activate(self):
        reserved = ExecutableCapabilityPermission(
            capability_id="exec.other",
            target_kind="module",
            adapter_id="module.plugin.synthetic",
            operation="read",
            effect="read",
            data_class="external_data",
            owner_approval_required=True,
        )
        service, _, _, _, _ = self.service(reserved_permissions=(reserved,))
        with self.assertRaises(PluginRegistrationActivationError) as caught:
            service.activate("synthetic", "1.0.0", "read")
        self.assertEqual(caught.exception.code, PLUGIN_REGISTRATION_ACTIVATION_ERROR_ROUTE_RESERVED)

    def test_fixed_d51_echo_id_is_reserved_by_production_inputs(self):
        reserved_ids = tuple(p.adapter_id for p in PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS)
        binding = self.binding(
            plugin_id="echo", capability_name="echo", capabilities=("echo",),
            capability_id="exec.dynamic.echo", adapter_id="module.plugin.echo",
            operation="echo", effect="none", data_class="owner_data",
        )
        service, _, _, _, _ = self.service(
            binding_marker=binding,
            adapter_marker=FakeModuleAdapter("module.plugin.echo", "plugin.echo"),
            reserved_adapter_ids=reserved_ids,
            reserved_permissions=PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS,
        )
        with self.assertRaises(PluginRegistrationActivationError) as caught:
            service.activate("echo", "1.0.0", "echo")
        self.assertEqual(caught.exception.code, PLUGIN_REGISTRATION_ACTIVATION_ERROR_ADAPTER_ID_RESERVED)

    def test_activation_does_not_execute_delegate(self):
        service, _, _, _, adapter = self.service()
        service.activate("synthetic", "1.0.0", "read")
        self.assertEqual(adapter.execute_calls, 0)

    def test_duplicate_activation_is_idempotent_after_revalidation(self):
        service, bs, es, store, _ = self.service()
        first = service.activate("synthetic", "1.0.0", "read")
        second = service.activate("synthetic", "1.0.0", "read")
        self.assertIs(first, second)
        self.assertEqual((bs.calls, es.calls, store.count), (2, 2, 1))

    def test_existing_activation_detects_subject_drift(self):
        service, bs, _, store, _ = self.service()
        service.activate("synthetic", "1.0.0", "read")
        bs.binding = self.binding(capabilities=("other", "read"))
        with self.assertRaises(PluginRegistrationActivationError) as caught:
            service.activate("synthetic", "1.0.0", "read")
        self.assertEqual(caught.exception.code, PLUGIN_REGISTRATION_ACTIVATION_ERROR_SUBJECT_MISMATCH)
        self.assertEqual(store.count, 1)

    def test_deactivate_does_not_require_upstream_state(self):
        service, bs, es, store, _ = self.service()
        record = service.activate("synthetic", "1.0.0", "read")
        bs.error = RuntimeError("down")
        es.error = RuntimeError("down")
        calls = (bs.calls, es.calls)
        self.assertEqual(service.deactivate("synthetic", "1.0.0", "read"), record)
        self.assertEqual((bs.calls, es.calls), calls)
        self.assertEqual(store.count, 0)

    def test_deactivate_missing_is_idempotent(self):
        service, _, _, _, _ = self.service()
        self.assertIsNone(service.deactivate("synthetic", "1.0.0", "read"))

    def test_old_snapshot_wrapper_blocks_after_deactivation(self):
        service, _, _, _, adapter = self.service()
        service.activate("synthetic", "1.0.0", "read")
        old_wrapper = service.runtime_snapshot().adapters[0]
        service.deactivate("synthetic", "1.0.0", "read")
        request, plan = self.request_plan()
        result = old_wrapper.execute(request, plan)
        self.assertEqual(result.error, PLUGIN_REGISTRATION_INACTIVE)
        self.assertEqual(adapter.execute_calls, 0)

    def test_old_wrapper_does_not_resurrect_after_reactivation(self):
        service, _, _, _, adapter = self.service()
        service.activate("synthetic", "1.0.0", "read")
        old_wrapper = service.runtime_snapshot().adapters[0]
        service.deactivate("synthetic", "1.0.0", "read")
        service.activate("synthetic", "1.0.0", "read")
        new_wrapper = service.runtime_snapshot().adapters[0]
        request, plan = self.request_plan()
        self.assertEqual(old_wrapper.execute(request, plan).error, PLUGIN_REGISTRATION_INACTIVE)
        self.assertEqual(new_wrapper.execute(request, plan).status, "succeeded")
        self.assertEqual(adapter.execute_calls, 1)

    def test_binding_staleness_invalidates_activation(self):
        service, bs, _, store, adapter = self.service()
        service.activate("synthetic", "1.0.0", "read")
        wrapper = service.runtime_snapshot().adapters[0]
        bs.error = PluginPermissionBindingError("binding_subject_mismatch")
        request, plan = self.request_plan()
        self.assertEqual(wrapper.execute(request, plan).error, PLUGIN_REGISTRATION_INACTIVE)
        self.assertEqual(store.count, 0)
        self.assertEqual(adapter.execute_calls, 0)

    def test_exposure_staleness_invalidates_activation(self):
        service, _, es, store, adapter = self.service()
        service.activate("synthetic", "1.0.0", "read")
        wrapper = service.runtime_snapshot().adapters[0]
        es.error = PluginModuleExposureError("exposure_subject_mismatch")
        request, plan = self.request_plan()
        self.assertEqual(wrapper.execute(request, plan).error, PLUGIN_REGISTRATION_INACTIVE)
        self.assertEqual(store.count, 0)
        self.assertEqual(adapter.execute_calls, 0)

    def test_runtime_snapshot_prunes_stale_activation(self):
        service, bs, _, store, _ = self.service()
        service.activate("synthetic", "1.0.0", "read")
        bs.binding = None
        snapshot = service.runtime_snapshot()
        self.assertEqual((snapshot.adapters, snapshot.permissions), ((), ()))
        self.assertEqual(store.count, 0)

    def test_runtime_snapshot_is_coherent(self):
        service, _, _, _, _ = self.service()
        record = service.activate("synthetic", "1.0.0", "read")
        snapshot = service.runtime_snapshot()
        self.assertEqual(snapshot.adapters[0].adapter_id, record.module_adapter_id)
        self.assertEqual(snapshot.permissions[0].adapter_id, record.module_adapter_id)
        self.assertEqual(snapshot.permissions[0].capability_id, record.capability_id)

    def test_snapshot_builds_valid_d31_and_d44_objects(self):
        service, _, _, _, _ = self.service()
        service.activate("synthetic", "1.0.0", "read")
        snapshot = service.runtime_snapshot()
        registry = AdapterRegistry(snapshot.adapters)
        policy = CapabilityPermissionPolicy(registry=registry, permissions=snapshot.permissions)
        self.assertEqual(registry.module_adapter_ids, ("module.plugin.synthetic",))
        self.assertIsNotNone(policy.resolve("module", "module.plugin.synthetic", "read"))

    def test_active_wrapper_delegates_only_while_current(self):
        service, _, _, _, adapter = self.service()
        service.activate("synthetic", "1.0.0", "read")
        wrapper = service.runtime_snapshot().adapters[0]
        request, plan = self.request_plan()
        self.assertEqual(wrapper.execute(request, plan).status, "succeeded")
        self.assertEqual(adapter.execute_calls, 1)

    def test_generated_permission_exactly_matches_binding(self):
        binding = self.binding(effect="external_side_effect", data_class="external_data")
        service, _, _, _, _ = self.service(binding_marker=binding)
        service.activate("synthetic", "1.0.0", "read")
        permission = service.runtime_snapshot().permissions[0]
        self.assertEqual(permission.capability_id, binding.capability_id)
        self.assertEqual(permission.adapter_id, binding.module_adapter_id)
        self.assertEqual(permission.operation, binding.operation)
        self.assertEqual(permission.effect, binding.effect)
        self.assertEqual(permission.data_class, binding.data_class)
        self.assertTrue(permission.owner_approval_required)

    def test_store_rejects_duplicate_adapter_id(self):
        store = PluginRegistrationActivationStore()
        service, _, _, _, _ = self.service(store=store)
        service.activate("synthetic", "1.0.0", "read")
        binding = self.binding(plugin_id="other", capability_name="other", capabilities=("other",), capability_id="exec.other", operation="other")
        other, _, _, _, _ = self.service(store=store, binding_marker=binding, adapter_marker=FakeModuleAdapter("module.plugin.synthetic", "plugin.other"))
        with self.assertRaises(PluginRegistrationActivationError) as caught:
            other.activate("other", "1.0.0", "other")
        self.assertEqual(caught.exception.code, PLUGIN_REGISTRATION_ACTIVATION_ERROR_DUPLICATE_ADAPTER_ID)

    def test_store_rejects_duplicate_capability_id(self):
        store = PluginRegistrationActivationStore()
        service, _, _, _, _ = self.service(store=store)
        service.activate("synthetic", "1.0.0", "read")
        binding = self.binding(plugin_id="other", capability_name="other", capabilities=("other",), adapter_id="module.plugin.other", operation="other")
        other, _, _, _, _ = self.service(store=store, binding_marker=binding, adapter_marker=FakeModuleAdapter("module.plugin.other", "plugin.other"))
        with self.assertRaises(PluginRegistrationActivationError) as caught:
            other.activate("other", "1.0.0", "other")
        self.assertEqual(caught.exception.code, PLUGIN_REGISTRATION_ACTIVATION_ERROR_DUPLICATE_CAPABILITY_ID)

    def test_store_is_bounded_without_silent_eviction(self):
        store = PluginRegistrationActivationStore(max_activations=1)
        service, _, _, _, _ = self.service(store=store)
        service.activate("synthetic", "1.0.0", "read")
        binding = self.binding(plugin_id="other", capability_name="other", capabilities=("other",), capability_id="exec.other", adapter_id="module.plugin.other", operation="other")
        other, _, _, _, _ = self.service(store=store, binding_marker=binding, adapter_marker=FakeModuleAdapter("module.plugin.other", "plugin.other"))
        with self.assertRaises(PluginRegistrationActivationError) as caught:
            other.activate("other", "1.0.0", "other")
        self.assertEqual(caught.exception.code, PLUGIN_REGISTRATION_ACTIVATION_ERROR_STORE_FULL)
        self.assertEqual(store.count, 1)

    def test_activation_listing_is_deterministic(self):
        store = PluginRegistrationActivationStore()
        for plugin_id in ("zeta", "alpha"):
            binding = self.binding(plugin_id=plugin_id, capability_name=plugin_id, capabilities=(plugin_id,), capability_id=f"exec.{plugin_id}", adapter_id=f"module.{plugin_id}", operation=plugin_id)
            service, _, _, _, _ = self.service(store=store, binding_marker=binding, adapter_marker=FakeModuleAdapter(f"module.{plugin_id}", plugin_id))
            service.activate(plugin_id, "1.0.0", plugin_id)
        self.assertEqual(tuple(r.plugin_id for r in store.list_records()), ("alpha", "zeta"))

    def test_invalid_subject_fails_before_upstream_resolution(self):
        service, bs, es, _, _ = self.service()
        cases = (
            (" synthetic ", "1.0.0", "read", PLUGIN_REGISTRATION_ACTIVATION_ERROR_INVALID_PLUGIN_ID),
            ("synthetic", "", "read", PLUGIN_REGISTRATION_ACTIVATION_ERROR_INVALID_PLUGIN_VERSION),
            ("synthetic", "1.0.0", " read ", PLUGIN_REGISTRATION_ACTIVATION_ERROR_INVALID_CAPABILITY_NAME),
        )
        for plugin_id, version, capability, expected in cases:
            with self.subTest(expected=expected):
                with self.assertRaises(PluginRegistrationActivationError) as caught:
                    service.activate(plugin_id, version, capability)
                self.assertEqual(caught.exception.code, expected)
        self.assertEqual((bs.calls, es.calls), (0, 0))

    def test_activation_does_not_create_d45_approval(self):
        service, _, _, _, _ = self.service()
        approvals = PendingExecutionApprovalStore()
        service.activate("synthetic", "1.0.0", "read")
        self.assertEqual(approvals.pending_count, 0)

    def test_activation_service_has_no_execution_authority_methods(self):
        service, _, _, _, _ = self.service()
        record = service.activate("synthetic", "1.0.0", "read")
        self.assertIsInstance(record, PluginRegistrationActivationRecord)
        for name in ("execute", "approve", "authorize", "get_plugin", "get_adapter"):
            self.assertFalse(hasattr(service, name))

    def test_static_d44_permissions_are_not_mutated(self):
        service, _, _, _, _ = self.service()
        before = PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS
        service.activate("synthetic", "1.0.0", "read")
        self.assertIs(PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS, before)


if __name__ == "__main__":
    unittest.main()
