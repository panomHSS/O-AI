import unittest
from dataclasses import FrozenInstanceError

from app.adapters.projected_plugin_module import (
    PLUGIN_MODULE_INVOCATION_ERROR_EXECUTION_FAILED,
    PLUGIN_MODULE_INVOCATION_ERROR_INACTIVE,
)
from app.api.dependencies import (
    get_loaded_plugin_store,
    get_plugin_governance_store,
    get_plugin_module_exposure_service,
    get_plugin_module_exposure_store,
)
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep
from app.contracts.plugin_candidate import (
    PLUGIN_CANDIDATE_REASON_PROJECTION_MATCH,
    PLUGIN_CANDIDATE_REASON_PROJECTION_MISSING,
    PLUGIN_CANDIDATE_REASON_VERSION_MISMATCH,
    PLUGIN_CANDIDATE_STATUS_PROJECTED_MATCH,
    PLUGIN_CANDIDATE_STATUS_UNPROJECTED,
    PLUGIN_CANDIDATE_STATUS_VERSION_MISMATCH,
    PluginDiscoveryCandidate,
)
from app.contracts.plugin_governance import (
    PLUGIN_GOVERNANCE_STATE_ADMITTED,
    PLUGIN_GOVERNANCE_STATE_REJECTED,
    PLUGIN_GOVERNANCE_STATE_REVOKED,
    PluginGovernanceDecision,
)
from app.contracts.plugin_loading import LoadedPluginRecord
from app.contracts.plugin_module_exposure import PluginModuleExposureRecord
from app.contracts.plugin_projection import PluginCapabilityProjection
from app.plugins.context import PluginExecutionContext
from app.plugins.request import PluginRequest
from app.plugins.response import PluginResult
from app.services.adapter_registry import AdapterRegistry
from app.services.capability_permission_policy import PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS
from app.services.execution_approval_service import PendingExecutionApprovalStore
from app.services.plugin_candidate_discovery import PluginCandidateDiscoveryError
from app.services.plugin_governance import PluginGovernanceDecisionStore
from app.services.plugin_loading import LoadedPluginStore
from app.services.plugin_module_exposure import (
    PLUGIN_MODULE_EXPOSURE_ERROR_CANDIDATE_NOT_ELIGIBLE,
    PLUGIN_MODULE_EXPOSURE_ERROR_CANDIDATE_NOT_FOUND,
    PLUGIN_MODULE_EXPOSURE_ERROR_CANDIDATE_RESOLUTION_FAILED,
    PLUGIN_MODULE_EXPOSURE_ERROR_DUPLICATE_TARGET,
    PLUGIN_MODULE_EXPOSURE_ERROR_GOVERNANCE_NOT_ADMITTED,
    PLUGIN_MODULE_EXPOSURE_ERROR_GOVERNANCE_NOT_FOUND,
    PLUGIN_MODULE_EXPOSURE_ERROR_INVALID_CAPABILITY_NAME,
    PLUGIN_MODULE_EXPOSURE_ERROR_INVALID_PLUGIN_ID,
    PLUGIN_MODULE_EXPOSURE_ERROR_INVALID_PLUGIN_VERSION,
    PLUGIN_MODULE_EXPOSURE_ERROR_PLUGIN_NOT_LOADED,
    PLUGIN_MODULE_EXPOSURE_ERROR_PROJECTION_NOT_FOUND,
    PLUGIN_MODULE_EXPOSURE_ERROR_PROJECTION_VERSION_MISMATCH,
    PLUGIN_MODULE_EXPOSURE_ERROR_STORE_FULL,
    PLUGIN_MODULE_EXPOSURE_ERROR_SUBJECT_MISMATCH,
    PluginModuleExposureError,
    PluginModuleExposureService,
    PluginModuleExposureStore,
)
from app.services.plugin_projection_catalog import PluginProjectionCatalog

class SequenceCandidateDiscovery:
    def __init__(self, snapshots):
        self.snapshots = list(snapshots)
        self.calls = 0
    def discover_candidates(self):
        self.calls += 1
        item = self.snapshots[min(self.calls - 1, len(self.snapshots) - 1)] if self.snapshots else ()
        if isinstance(item, Exception):
            raise item
        return item

class GovernanceView:
    def __init__(self, store): self.store = store
    def resolve(self, plugin_id, plugin_version): return self.store.resolve(plugin_id, plugin_version)

class LoadingView:
    def __init__(self, store): self.store = store
    def resolve(self, plugin_id, plugin_version): return self.store.resolve_record(plugin_id, plugin_version)

class FakePlugin:
    def __init__(self, *, result=None, error=None):
        self.result, self.error, self.execute_calls = result, error, 0
    @property
    def id(self): return "echo"
    @property
    def version(self): return "1.0.0"
    @property
    def name(self): return "Fake Echo"
    def execute(self, context, request):
        self.execute_calls += 1
        if self.error: raise self.error
        if self.result is not None: return self.result
        return PluginResult(content=request.content)

class PluginModuleExposureTests(unittest.TestCase):
    @staticmethod
    def candidate(*, status=PLUGIN_CANDIDATE_STATUS_PROJECTED_MATCH, capabilities=("echo",)):
        reasons = {
            PLUGIN_CANDIDATE_STATUS_PROJECTED_MATCH: PLUGIN_CANDIDATE_REASON_PROJECTION_MATCH,
            PLUGIN_CANDIDATE_STATUS_UNPROJECTED: PLUGIN_CANDIDATE_REASON_PROJECTION_MISSING,
            PLUGIN_CANDIDATE_STATUS_VERSION_MISMATCH: PLUGIN_CANDIDATE_REASON_VERSION_MISMATCH,
        }
        if status != PLUGIN_CANDIDATE_STATUS_PROJECTED_MATCH:
            capabilities = ()
        return PluginDiscoveryCandidate(plugin_id="echo", plugin_version="1.0.0", status=status, projected_capability_names=capabilities, reason_code=reasons[status])

    @staticmethod
    def projection(*, version="1.0.0", adapter_id="module.plugin.echo", operation="echo"):
        return PluginCapabilityProjection(plugin_id="echo", plugin_version=version, capability_name="echo", description="test", module_adapter_id=adapter_id, operation=operation)

    @staticmethod
    def governance(*, state=PLUGIN_GOVERNANCE_STATE_ADMITTED, capabilities=("echo",)):
        store = PluginGovernanceDecisionStore()
        store.record(PluginGovernanceDecision(plugin_id="echo", plugin_version="1.0.0", projected_capability_names=capabilities, state=state), allowed_existing_states=frozenset())
        return store

    @staticmethod
    def loaded(*, capabilities=("echo",), plugin=None):
        plugin = plugin or FakePlugin()
        store = LoadedPluginStore()
        store.add(record=LoadedPluginRecord(plugin_id="echo", plugin_version="1.0.0", plugin_name=plugin.name, projected_capability_names=capabilities), plugin=plugin)
        return store, plugin

    @classmethod
    def service(cls, *, snapshots=None, governance=None, loaded=None, catalog=None, exposure_store=None, plugin=None):
        discovery = SequenceCandidateDiscovery(snapshots or [(cls.candidate(),)])
        governance = governance or cls.governance()
        if loaded is None:
            loaded, plugin = cls.loaded(plugin=plugin)
        catalog = catalog or PluginProjectionCatalog((cls.projection(),))
        exposure_store = exposure_store or PluginModuleExposureStore()
        service = PluginModuleExposureService(
            projection_catalog=catalog,
            candidate_discovery=discovery,
            governance=GovernanceView(governance),
            loading=LoadingView(loaded),
            loaded_store=loaded,
            exposure_store=exposure_store,
        )
        return service, exposure_store, discovery, governance, loaded, plugin

    @staticmethod
    def request_plan(**kw):
        rid = kw.get("request_id", "r1")
        request = CommandRequest(request_id=rid, command="plugin.echo")
        steps = kw.get("steps")
        if steps is None:
            steps = (ExecutionStep(sequence=1, operation=kw.get("operation", "echo"), parameters=kw.get("parameters", {"content": kw.get("content", "hello")})),)
        plan = ExecutionPlan(request_id=kw.get("plan_request_id", rid), adapter_id=kw.get("adapter_id", "module.plugin.echo"), steps=steps, owner_approval_required=kw.get("owner_approval_required", False))
        return request, plan
    def test_production_composition_starts_empty_and_default_deny(self):
        get_plugin_governance_store().clear(); get_loaded_plugin_store().clear()
        store = get_plugin_module_exposure_store(); store.clear()
        service = get_plugin_module_exposure_service()
        self.assertIs(store, get_plugin_module_exposure_store())
        self.assertIs(service, get_plugin_module_exposure_service())
        self.assertEqual(service.list_exposures(), ())
        with self.assertRaises(PluginModuleExposureError) as caught:
            service.expose("echo", "1.0.0", "echo")
        self.assertEqual(caught.exception.code, PLUGIN_MODULE_EXPOSURE_ERROR_GOVERNANCE_NOT_FOUND)

    def test_exact_subject_exposes_metadata_without_execution(self):
        service, store, discovery, _, _, plugin = self.service()
        record = service.expose("echo", "1.0.0", "echo")
        self.assertEqual(discovery.calls, 1); self.assertEqual(store.count, 1)
        self.assertEqual((record.module_adapter_id, record.module_name, record.operation), ("module.plugin.echo", "plugin.echo", "echo"))
        self.assertEqual(plugin.execute_calls, 0)

    def test_record_is_immutable_metadata_only(self):
        service, *_ = self.service(); record = service.expose("echo", "1.0.0", "echo")
        self.assertFalse(hasattr(record, "adapter")); self.assertFalse(hasattr(record, "plugin")); self.assertFalse(hasattr(record, "execute"))
        with self.assertRaises(FrozenInstanceError): record.operation = "x"

    def test_no_rejected_or_revoked_governance_cannot_expose(self):
        cases = [
            (PluginGovernanceDecisionStore(), PLUGIN_MODULE_EXPOSURE_ERROR_GOVERNANCE_NOT_FOUND),
            (self.governance(state=PLUGIN_GOVERNANCE_STATE_REJECTED), PLUGIN_MODULE_EXPOSURE_ERROR_GOVERNANCE_NOT_ADMITTED),
            (self.governance(state=PLUGIN_GOVERNANCE_STATE_REVOKED), PLUGIN_MODULE_EXPOSURE_ERROR_GOVERNANCE_NOT_ADMITTED),
        ]
        for governance, expected in cases:
            with self.subTest(expected=expected):
                service, _, discovery, *_ = self.service(governance=governance)
                with self.assertRaises(PluginModuleExposureError) as caught: service.expose("echo", "1.0.0", "echo")
                self.assertEqual(caught.exception.code, expected); self.assertEqual(discovery.calls, 0)

    def test_candidate_missing_or_ineligible_cannot_expose(self):
        cases = [
            ((), PLUGIN_MODULE_EXPOSURE_ERROR_CANDIDATE_NOT_FOUND),
            ((self.candidate(status=PLUGIN_CANDIDATE_STATUS_UNPROJECTED),), PLUGIN_MODULE_EXPOSURE_ERROR_CANDIDATE_NOT_ELIGIBLE),
            ((self.candidate(status=PLUGIN_CANDIDATE_STATUS_VERSION_MISMATCH),), PLUGIN_MODULE_EXPOSURE_ERROR_CANDIDATE_NOT_ELIGIBLE),
        ]
        for snapshot, expected in cases:
            with self.subTest(expected=expected):
                service, *_ = self.service(snapshots=[snapshot])
                with self.assertRaises(PluginModuleExposureError) as caught: service.expose("echo", "1.0.0", "echo")
                self.assertEqual(caught.exception.code, expected)

    def test_candidate_failure_is_normalized(self):
        service, *_ = self.service(snapshots=[PluginCandidateDiscoveryError("sensitive")])
        with self.assertRaises(PluginModuleExposureError) as caught: service.expose("echo", "1.0.0", "echo")
        self.assertEqual(caught.exception.code, PLUGIN_MODULE_EXPOSURE_ERROR_CANDIDATE_RESOLUTION_FAILED)
        self.assertNotIn("sensitive", str(caught.exception))

    def test_capability_subject_drift_fails_closed(self):
        service, store, *_ = self.service(snapshots=[(self.candidate(capabilities=("echo", "search")),)])
        with self.assertRaises(PluginModuleExposureError) as caught: service.expose("echo", "1.0.0", "echo")
        self.assertEqual(caught.exception.code, PLUGIN_MODULE_EXPOSURE_ERROR_SUBJECT_MISMATCH); self.assertEqual(store.count, 0)

    def test_plugin_must_already_be_loaded_and_match_subject(self):
        empty = LoadedPluginStore()
        service, *_ = self.service(loaded=empty)
        with self.assertRaises(PluginModuleExposureError) as caught: service.expose("echo", "1.0.0", "echo")
        self.assertEqual(caught.exception.code, PLUGIN_MODULE_EXPOSURE_ERROR_PLUGIN_NOT_LOADED)
        loaded, _ = self.loaded(capabilities=("echo", "search"))
        service, *_ = self.service(loaded=loaded)
        with self.assertRaises(PluginModuleExposureError) as caught: service.expose("echo", "1.0.0", "echo")
        self.assertEqual(caught.exception.code, PLUGIN_MODULE_EXPOSURE_ERROR_SUBJECT_MISMATCH)

    def test_projection_must_exist_and_version_match(self):
        service, *_ = self.service(catalog=PluginProjectionCatalog(()))
        with self.assertRaises(PluginModuleExposureError) as caught: service.expose("echo", "1.0.0", "echo")
        self.assertEqual(caught.exception.code, PLUGIN_MODULE_EXPOSURE_ERROR_PROJECTION_NOT_FOUND)
        service, *_ = self.service(catalog=PluginProjectionCatalog((self.projection(version="2.0.0"),)))
        with self.assertRaises(PluginModuleExposureError) as caught: service.expose("echo", "1.0.0", "echo")
        self.assertEqual(caught.exception.code, PLUGIN_MODULE_EXPOSURE_ERROR_PROJECTION_VERSION_MISMATCH)

    def test_duplicate_exposure_is_idempotent_after_revalidation(self):
        service, store, discovery, *_ = self.service(snapshots=[(self.candidate(),), (self.candidate(),)])
        first = service.expose("echo", "1.0.0", "echo"); a1 = store._resolve_adapter("echo", "1.0.0", "echo")
        second = service.expose("echo", "1.0.0", "echo"); a2 = store._resolve_adapter("echo", "1.0.0", "echo")
        self.assertIs(first, second); self.assertIs(a1, a2); self.assertEqual(discovery.calls, 2)

    def test_store_rejects_duplicate_target_and_is_bounded(self):
        store = PluginModuleExposureStore(max_exposures=1); dummy = object()
        one = PluginModuleExposureRecord("a", "1", "one", ("one",), "module.shared", "shared", "run")
        store.add(record=one, adapter=dummy)
        two = PluginModuleExposureRecord("b", "1", "two", ("two",), "module.shared", "shared", "run")
        with self.assertRaises(PluginModuleExposureError) as caught: store.add(record=two, adapter=dummy)
        self.assertEqual(caught.exception.code, PLUGIN_MODULE_EXPOSURE_ERROR_DUPLICATE_TARGET)
        three = PluginModuleExposureRecord("c", "1", "three", ("three",), "module.other", "other", "run")
        with self.assertRaises(PluginModuleExposureError) as caught: store.add(record=three, adapter=dummy)
        self.assertEqual(caught.exception.code, PLUGIN_MODULE_EXPOSURE_ERROR_STORE_FULL); self.assertEqual(store.count, 1)

    def test_public_surface_does_not_expose_adapter_or_plugin(self):
        service, store, *_ = self.service(); record = service.expose("echo", "1.0.0", "echo")
        self.assertIsInstance(record, PluginModuleExposureRecord); self.assertFalse(hasattr(service, "resolve_adapter")); self.assertFalse(hasattr(service, "execute"))
        self.assertIsNotNone(store._resolve_adapter("echo", "1.0.0", "echo"))

    def test_exposure_does_not_mutate_registry_permission_or_approval(self):
        service, *_ = self.service(); registry = AdapterRegistry(()); approvals = PendingExecutionApprovalStore(); before = PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS
        service.expose("echo", "1.0.0", "echo")
        self.assertEqual(registry.adapter_ids, ()); self.assertIsNone(registry.resolve_module("module.plugin.echo")); self.assertIs(PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS, before); self.assertEqual(approvals.pending_count, 0)

    def test_invalid_subject_fails_before_discovery(self):
        service, _, discovery, *_ = self.service(snapshots=[RuntimeError("must not run")])
        cases = [(" echo ", "1.0.0", "echo", PLUGIN_MODULE_EXPOSURE_ERROR_INVALID_PLUGIN_ID), ("echo", "", "echo", PLUGIN_MODULE_EXPOSURE_ERROR_INVALID_PLUGIN_VERSION), ("echo", "1.0.0", " echo ", PLUGIN_MODULE_EXPOSURE_ERROR_INVALID_CAPABILITY_NAME)]
        for plugin_id, version, capability, expected in cases:
            with self.assertRaises(PluginModuleExposureError) as caught: service.expose(plugin_id, version, capability)
            self.assertEqual(caught.exception.code, expected)
        self.assertEqual(discovery.calls, 0)
    def test_adapter_validation_blocks_before_plugin(self):
        cases = [
            ({"plan_request_id": "other"}, "request_plan_mismatch"),
            ({"adapter_id": "module.other"}, "adapter_mismatch"),
            ({"owner_approval_required": True}, "owner_approval_required"),
            ({"steps": ()}, "invalid_plan_shape"),
            ({"operation": "other"}, "unsupported_operation"),
            ({"parameters": {"content": "x", "plugin_id": "echo"}}, "invalid_operation_shape"),
            ({"content": 123}, "invalid_content"),
            ({"content": "x" * (16 * 1024 + 1)}, "content_too_large"),
        ]
        for kwargs, expected in cases:
            with self.subTest(expected=expected):
                plugin = FakePlugin(); service, store, *_ = self.service(plugin=plugin)
                service.expose("echo", "1.0.0", "echo"); adapter = store._resolve_adapter("echo", "1.0.0", "echo")
                request, plan = self.request_plan(**kwargs); result = adapter.execute(request, plan)
                self.assertEqual(result.error, expected); self.assertEqual(plugin.execute_calls, 0)

    def test_adapter_invokes_exact_active_plugin(self):
        plugin = FakePlugin(); service, store, discovery, *_ = self.service(plugin=plugin, snapshots=[(self.candidate(),), (self.candidate(),)])
        service.expose("echo", "1.0.0", "echo"); adapter = store._resolve_adapter("echo", "1.0.0", "echo")
        request, plan = self.request_plan(content="hello"); result = adapter.execute(request, plan)
        self.assertEqual(discovery.calls, 2); self.assertEqual(plugin.execute_calls, 1); self.assertEqual(result.status, "succeeded"); self.assertEqual(result.output, {"content": "hello"})

    def test_adapter_validates_plugin_result_and_output_bound(self):
        cases = [(object(), "plugin_result_invalid"), (PluginResult(content="x" * (16 * 1024 + 1)), "plugin_result_too_large")]
        for payload, expected in cases:
            with self.subTest(expected=expected):
                plugin = FakePlugin(result=payload); service, store, *_ = self.service(plugin=plugin, snapshots=[(self.candidate(),), (self.candidate(),)])
                service.expose("echo", "1.0.0", "echo"); adapter = store._resolve_adapter("echo", "1.0.0", "echo")
                request, plan = self.request_plan(); result = adapter.execute(request, plan)
                self.assertEqual(result.error, expected); self.assertEqual(plugin.execute_calls, 1)

    def test_revocation_makes_materialized_exposure_inactive(self):
        governance = self.governance(); plugin = FakePlugin(); service, store, *_ = self.service(governance=governance, plugin=plugin, snapshots=[(self.candidate(),), (self.candidate(),)])
        service.expose("echo", "1.0.0", "echo"); governance.revoke("echo", "1.0.0")
        adapter = store._resolve_adapter("echo", "1.0.0", "echo"); request, plan = self.request_plan(); result = adapter.execute(request, plan)
        self.assertEqual(result.error, PLUGIN_MODULE_INVOCATION_ERROR_INACTIVE); self.assertEqual(plugin.execute_calls, 0)

    def test_candidate_drift_makes_materialized_exposure_inactive(self):
        plugin = FakePlugin(); changed = self.candidate(capabilities=("echo", "search")); service, store, *_ = self.service(plugin=plugin, snapshots=[(self.candidate(),), (changed,)])
        service.expose("echo", "1.0.0", "echo"); adapter = store._resolve_adapter("echo", "1.0.0", "echo")
        request, plan = self.request_plan(); result = adapter.execute(request, plan)
        self.assertEqual(result.error, PLUGIN_MODULE_INVOCATION_ERROR_INACTIVE); self.assertEqual(plugin.execute_calls, 0)

    def test_missing_loaded_subject_makes_exposure_inactive(self):
        plugin = FakePlugin(); service, store, _, _, loaded, _ = self.service(plugin=plugin, snapshots=[(self.candidate(),), (self.candidate(),)])
        service.expose("echo", "1.0.0", "echo"); loaded.clear(); adapter = store._resolve_adapter("echo", "1.0.0", "echo")
        request, plan = self.request_plan(); result = adapter.execute(request, plan)
        self.assertEqual(result.error, PLUGIN_MODULE_INVOCATION_ERROR_INACTIVE); self.assertEqual(plugin.execute_calls, 0)

    def test_plugin_exception_is_normalized(self):
        plugin = FakePlugin(error=RuntimeError("sensitive plugin failure")); service, store, *_ = self.service(plugin=plugin, snapshots=[(self.candidate(),), (self.candidate(),)])
        service.expose("echo", "1.0.0", "echo"); adapter = store._resolve_adapter("echo", "1.0.0", "echo")
        request, plan = self.request_plan(); result = adapter.execute(request, plan)
        self.assertEqual(result.error, PLUGIN_MODULE_INVOCATION_ERROR_EXECUTION_FAILED); self.assertEqual(plugin.execute_calls, 1); self.assertNotIn("sensitive", str(result.error))

    def test_d55_internal_seam_rejects_subject_mismatch_without_execution(self):
        loaded, plugin = self.loaded()
        with self.assertRaises(Exception):
            loaded._invoke_loaded_for_module(plugin_id="echo", plugin_version="1.0.0", projected_capability_names=("other",), context=PluginExecutionContext(), request=PluginRequest(content="hello"))
        self.assertEqual(plugin.execute_calls, 0)

if __name__ == "__main__":
    unittest.main()
