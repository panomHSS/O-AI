import unittest
from dataclasses import FrozenInstanceError

from app.api.dependencies import (
    get_controlled_plugin_loader,
    get_loaded_plugin_store,
    get_plugin_loading_service,
)
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
from app.plugins.context import PluginExecutionContext
from app.plugins.default_plugin_loader import DefaultPluginLoader
from app.plugins.echo import EchoPlugin
from app.plugins.exceptions import PluginNotFoundError
from app.plugins.explicit_plugin_factory_loader import (
    PLUGIN_FACTORY_LOADER_ERROR_UNSUPPORTED_MANIFEST,
    ExplicitPluginFactoryLoader,
    ExplicitPluginFactoryLoaderError,
)
from app.plugins.in_memory_registry import InMemoryPluginRegistry
from app.plugins.plugin_manifest import PluginManifest
from app.plugins.request import PluginRequest
from app.plugins.response import PluginResult
from app.services.adapter_registry import AdapterRegistry
from app.services.capability_permission_policy import (
    PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS,
)
from app.services.execution_approval_service import (
    PendingExecutionApprovalStore,
)
from app.services.plugin_candidate_discovery import (
    PluginCandidateDiscoveryError,
)
from app.services.plugin_governance import PluginGovernanceDecisionStore
from app.services.plugin_loading import (
    PLUGIN_LOADING_ERROR_CANDIDATE_NOT_ELIGIBLE,
    PLUGIN_LOADING_ERROR_CANDIDATE_NOT_FOUND,
    PLUGIN_LOADING_ERROR_CANDIDATE_RESOLUTION_FAILED,
    PLUGIN_LOADING_ERROR_GOVERNANCE_NOT_ADMITTED,
    PLUGIN_LOADING_ERROR_GOVERNANCE_NOT_FOUND,
    PLUGIN_LOADING_ERROR_IDENTITY_MISMATCH,
    PLUGIN_LOADING_ERROR_INVALID_PLUGIN_ID,
    PLUGIN_LOADING_ERROR_INVALID_PLUGIN_VERSION,
    PLUGIN_LOADING_ERROR_LOAD_FAILED,
    PLUGIN_LOADING_ERROR_MANIFEST_NOT_SUPPORTED,
    PLUGIN_LOADING_ERROR_PLUGIN_INVALID,
    PLUGIN_LOADING_ERROR_STORE_FULL,
    PLUGIN_LOADING_ERROR_SUBJECT_MISMATCH,
    LoadedPluginStore,
    PluginLoadingError,
    PluginLoadingService,
)


class SequenceCandidateDiscovery:
    def __init__(self, snapshots) -> None:
        self._snapshots = list(snapshots)
        self.calls = 0

    def discover_candidates(self):
        self.calls += 1
        if not self._snapshots:
            return ()
        index = min(self.calls - 1, len(self._snapshots) - 1)
        item = self._snapshots[index]
        if isinstance(item, Exception):
            raise item
        return item


class GovernanceView:
    def __init__(self, store: PluginGovernanceDecisionStore) -> None:
        self._store = store

    def resolve(self, plugin_id: str, plugin_version: str):
        return self._store.resolve(plugin_id, plugin_version)


class RecordingLoader:
    def __init__(self, result=None, *, error: Exception | None = None) -> None:
        self.result = EchoPlugin() if result is None else result
        self.error = error
        self.calls = 0
        self.manifests: list[PluginManifest] = []

    def load(self, manifest: PluginManifest):
        self.calls += 1
        self.manifests.append(manifest)
        if self.error is not None:
            raise self.error
        return self.result


class FakePlugin:
    def __init__(
        self,
        *,
        plugin_id: str = "echo",
        version: str = "1.0.0",
        name: object = "Fake Echo",
        callable_execute: bool = True,
    ) -> None:
        self._id = plugin_id
        self._version = version
        self._name = name
        self.execute_calls = 0
        if not callable_execute:
            self.execute = None  # type: ignore[assignment]

    @property
    def id(self):
        return self._id

    @property
    def version(self):
        return self._version

    @property
    def name(self):
        return self._name

    def execute(
        self,
        context: PluginExecutionContext,
        request: PluginRequest,
    ) -> PluginResult:
        self.execute_calls += 1
        return PluginResult(content=request.content)


class PluginLoadingTests(unittest.TestCase):
    @staticmethod
    def candidate(
        *,
        plugin_id: str = "echo",
        plugin_version: str = "1.0.0",
        status: str = PLUGIN_CANDIDATE_STATUS_PROJECTED_MATCH,
        capabilities: tuple[str, ...] = ("echo",),
    ) -> PluginDiscoveryCandidate:
        if status == PLUGIN_CANDIDATE_STATUS_PROJECTED_MATCH:
            reason = PLUGIN_CANDIDATE_REASON_PROJECTION_MATCH
        elif status == PLUGIN_CANDIDATE_STATUS_UNPROJECTED:
            reason = PLUGIN_CANDIDATE_REASON_PROJECTION_MISSING
            capabilities = ()
        else:
            reason = PLUGIN_CANDIDATE_REASON_VERSION_MISMATCH
            capabilities = ()
        return PluginDiscoveryCandidate(
            plugin_id=plugin_id,
            plugin_version=plugin_version,
            status=status,  # type: ignore[arg-type]
            projected_capability_names=capabilities,
            reason_code=reason,
        )

    @staticmethod
    def governance_store(
        *,
        plugin_id: str = "echo",
        plugin_version: str = "1.0.0",
        capabilities: tuple[str, ...] = ("echo",),
        state: str = PLUGIN_GOVERNANCE_STATE_ADMITTED,
    ) -> PluginGovernanceDecisionStore:
        store = PluginGovernanceDecisionStore()
        store.record(
            PluginGovernanceDecision(
                plugin_id=plugin_id,
                plugin_version=plugin_version,
                projected_capability_names=capabilities,
                state=state,  # type: ignore[arg-type]
            ),
            allowed_existing_states=frozenset(),
        )
        return store

    @classmethod
    def service(
        cls,
        *,
        snapshots=None,
        governance_store: PluginGovernanceDecisionStore | None = None,
        loader=None,
        max_loaded: int = 100,
    ):
        discovery = SequenceCandidateDiscovery(
            snapshots
            if snapshots is not None
            else [(cls.candidate(),)]
        )
        governance_store = (
            governance_store
            if governance_store is not None
            else cls.governance_store()
        )
        loader = loader if loader is not None else RecordingLoader()
        loaded_store = LoadedPluginStore(max_loaded=max_loaded)
        service = PluginLoadingService(
            candidate_discovery=discovery,  # type: ignore[arg-type]
            governance=GovernanceView(governance_store),  # type: ignore[arg-type]
            loader=loader,
            store=loaded_store,
        )
        return service, loaded_store, discovery, loader

    def test_production_composition_starts_empty_and_default_deny(self) -> None:
        store = get_loaded_plugin_store()
        store.clear()
        service = get_plugin_loading_service()

        self.assertIs(store, get_loaded_plugin_store())
        self.assertIs(service, get_plugin_loading_service())
        self.assertIs(
            get_controlled_plugin_loader(),
            get_controlled_plugin_loader(),
        )
        self.assertEqual(store.count, 0)
        self.assertEqual(service.list_loaded(), ())
        self.assertIsNone(service.resolve("echo", "1.0.0"))

        with self.assertRaises(PluginLoadingError) as caught:
            service.load("echo", "1.0.0")
        self.assertEqual(
            caught.exception.code,
            PLUGIN_LOADING_ERROR_GOVERNANCE_NOT_FOUND,
        )

    def test_exact_admitted_current_subject_loads(self) -> None:
        service, store, discovery, loader = self.service()

        record = service.load("echo", "1.0.0")

        self.assertEqual(discovery.calls, 1)
        self.assertEqual(loader.calls, 1)
        self.assertEqual(store.count, 1)
        self.assertEqual(record.plugin_id, "echo")
        self.assertEqual(record.plugin_version, "1.0.0")
        self.assertEqual(record.projected_capability_names, ("echo",))

    def test_loaded_record_is_immutable_metadata_only(self) -> None:
        service, _, _, _ = self.service()
        record = service.load("echo", "1.0.0")

        self.assertFalse(hasattr(record, "plugin"))
        self.assertFalse(hasattr(record, "execute"))
        with self.assertRaises(FrozenInstanceError):
            record.plugin_name = "changed"  # type: ignore[misc]

    def test_no_governance_decision_cannot_load(self) -> None:
        service, _, discovery, loader = self.service(
            governance_store=PluginGovernanceDecisionStore()
        )

        with self.assertRaises(PluginLoadingError) as caught:
            service.load("echo", "1.0.0")

        self.assertEqual(
            caught.exception.code,
            PLUGIN_LOADING_ERROR_GOVERNANCE_NOT_FOUND,
        )
        self.assertEqual(discovery.calls, 0)
        self.assertEqual(loader.calls, 0)

    def test_rejected_governance_cannot_load(self) -> None:
        governance = self.governance_store(
            state=PLUGIN_GOVERNANCE_STATE_REJECTED
        )
        service, _, discovery, loader = self.service(
            governance_store=governance
        )

        with self.assertRaises(PluginLoadingError) as caught:
            service.load("echo", "1.0.0")

        self.assertEqual(
            caught.exception.code,
            PLUGIN_LOADING_ERROR_GOVERNANCE_NOT_ADMITTED,
        )
        self.assertEqual(discovery.calls, 0)
        self.assertEqual(loader.calls, 0)

    def test_revoked_governance_cannot_load(self) -> None:
        governance = self.governance_store(
            state=PLUGIN_GOVERNANCE_STATE_REVOKED
        )
        service, _, discovery, loader = self.service(
            governance_store=governance
        )

        with self.assertRaises(PluginLoadingError) as caught:
            service.load("echo", "1.0.0")

        self.assertEqual(
            caught.exception.code,
            PLUGIN_LOADING_ERROR_GOVERNANCE_NOT_ADMITTED,
        )
        self.assertEqual(discovery.calls, 0)
        self.assertEqual(loader.calls, 0)

    def test_candidate_not_found_cannot_load(self) -> None:
        service, _, discovery, loader = self.service(snapshots=[()])

        with self.assertRaises(PluginLoadingError) as caught:
            service.load("echo", "1.0.0")

        self.assertEqual(discovery.calls, 1)
        self.assertEqual(loader.calls, 0)
        self.assertEqual(
            caught.exception.code,
            PLUGIN_LOADING_ERROR_CANDIDATE_NOT_FOUND,
        )

    def test_unprojected_candidate_cannot_load(self) -> None:
        candidate = self.candidate(
            status=PLUGIN_CANDIDATE_STATUS_UNPROJECTED
        )
        service, _, _, loader = self.service(snapshots=[(candidate,)])

        with self.assertRaises(PluginLoadingError) as caught:
            service.load("echo", "1.0.0")

        self.assertEqual(loader.calls, 0)
        self.assertEqual(
            caught.exception.code,
            PLUGIN_LOADING_ERROR_CANDIDATE_NOT_ELIGIBLE,
        )

    def test_version_mismatch_candidate_cannot_load(self) -> None:
        candidate = self.candidate(
            status=PLUGIN_CANDIDATE_STATUS_VERSION_MISMATCH
        )
        service, _, _, loader = self.service(snapshots=[(candidate,)])

        with self.assertRaises(PluginLoadingError) as caught:
            service.load("echo", "1.0.0")

        self.assertEqual(loader.calls, 0)
        self.assertEqual(
            caught.exception.code,
            PLUGIN_LOADING_ERROR_CANDIDATE_NOT_ELIGIBLE,
        )

    def test_candidate_failure_is_normalized_without_load(self) -> None:
        failure = PluginCandidateDiscoveryError("sensitive_discovery_error")
        service, _, discovery, loader = self.service(
            snapshots=[failure]
        )

        with self.assertRaises(PluginLoadingError) as caught:
            service.load("echo", "1.0.0")

        self.assertEqual(discovery.calls, 1)
        self.assertEqual(loader.calls, 0)
        self.assertEqual(
            caught.exception.code,
            PLUGIN_LOADING_ERROR_CANDIDATE_RESOLUTION_FAILED,
        )
        self.assertNotIn("sensitive", str(caught.exception))

    def test_capability_drift_fails_closed_before_loader(self) -> None:
        current = self.candidate(capabilities=("echo", "search"))
        service, _, _, loader = self.service(snapshots=[(current,)])

        with self.assertRaises(PluginLoadingError) as caught:
            service.load("echo", "1.0.0")

        self.assertEqual(loader.calls, 0)
        self.assertEqual(
            caught.exception.code,
            PLUGIN_LOADING_ERROR_SUBJECT_MISMATCH,
        )

    def test_duplicate_load_is_idempotent_and_factory_not_called_twice(self) -> None:
        service, store, discovery, loader = self.service(
            snapshots=[(self.candidate(),), (self.candidate(),)]
        )

        first = service.load("echo", "1.0.0")
        second = service.load("echo", "1.0.0")

        self.assertIs(first, second)
        self.assertEqual(store.count, 1)
        self.assertEqual(discovery.calls, 2)
        self.assertEqual(loader.calls, 1)

    def test_duplicate_load_rechecks_governance_before_returning_record(self) -> None:
        governance = self.governance_store()
        service, store, _, loader = self.service(
            governance_store=governance,
            snapshots=[(self.candidate(),), (self.candidate(),)],
        )
        service.load("echo", "1.0.0")
        governance.revoke("echo", "1.0.0")

        with self.assertRaises(PluginLoadingError) as caught:
            service.load("echo", "1.0.0")

        self.assertEqual(store.count, 1)
        self.assertEqual(loader.calls, 1)
        self.assertEqual(
            caught.exception.code,
            PLUGIN_LOADING_ERROR_GOVERNANCE_NOT_ADMITTED,
        )

    def test_duplicate_load_rechecks_current_candidate_subject(self) -> None:
        initial = self.candidate(capabilities=("echo",))
        changed = self.candidate(capabilities=("echo", "search"))
        service, store, discovery, loader = self.service(
            snapshots=[(initial,), (changed,)]
        )

        service.load("echo", "1.0.0")
        with self.assertRaises(PluginLoadingError) as caught:
            service.load("echo", "1.0.0")

        self.assertEqual(store.count, 1)
        self.assertEqual(discovery.calls, 2)
        self.assertEqual(loader.calls, 1)
        self.assertEqual(
            caught.exception.code,
            PLUGIN_LOADING_ERROR_SUBJECT_MISMATCH,
        )

    def test_store_capacity_checked_before_factory(self) -> None:
        alpha = self.candidate(plugin_id="alpha")
        beta = self.candidate(plugin_id="beta")
        governance = PluginGovernanceDecisionStore()
        for plugin_id in ("alpha", "beta"):
            governance.record(
                PluginGovernanceDecision(
                    plugin_id=plugin_id,
                    plugin_version="1.0.0",
                    projected_capability_names=("echo",),
                    state=PLUGIN_GOVERNANCE_STATE_ADMITTED,
                ),
                allowed_existing_states=frozenset(),
            )
        loader = RecordingLoader(result=FakePlugin(plugin_id="alpha"))
        service, store, discovery, _ = self.service(
            governance_store=governance,
            loader=loader,
            max_loaded=1,
            snapshots=[(alpha, beta), (alpha, beta)],
        )

        service.load("alpha", "1.0.0")
        loader.result = FakePlugin(plugin_id="beta")
        with self.assertRaises(PluginLoadingError) as caught:
            service.load("beta", "1.0.0")

        self.assertEqual(store.count, 1)
        self.assertEqual(discovery.calls, 2)
        self.assertEqual(loader.calls, 1)
        self.assertEqual(
            caught.exception.code,
            PLUGIN_LOADING_ERROR_STORE_FULL,
        )

    def test_loaded_records_are_sorted_deterministically(self) -> None:
        alpha = self.candidate(plugin_id="alpha")
        zeta = self.candidate(plugin_id="zeta")
        governance = PluginGovernanceDecisionStore()
        for plugin_id in ("zeta", "alpha"):
            governance.record(
                PluginGovernanceDecision(
                    plugin_id=plugin_id,
                    plugin_version="1.0.0",
                    projected_capability_names=("echo",),
                    state=PLUGIN_GOVERNANCE_STATE_ADMITTED,
                ),
                allowed_existing_states=frozenset(),
            )
        loader = RecordingLoader(result=FakePlugin(plugin_id="zeta"))
        service, _, _, _ = self.service(
            governance_store=governance,
            loader=loader,
            snapshots=[(alpha, zeta), (alpha, zeta)],
        )

        service.load("zeta", "1.0.0")
        loader.result = FakePlugin(plugin_id="alpha")
        service.load("alpha", "1.0.0")

        self.assertEqual(
            tuple(record.plugin_id for record in service.list_loaded()),
            ("alpha", "zeta"),
        )

    def test_explicit_factory_loader_loads_only_exact_echo_identity(self) -> None:
        loader = ExplicitPluginFactoryLoader()

        plugin = loader.load(
            PluginManifest(plugin_id="echo", version="1.0.0")
        )

        self.assertEqual(plugin.id, "echo")
        self.assertEqual(plugin.version, "1.0.0")

    def test_explicit_factory_loader_rejects_unknown_manifest_without_fallback(self) -> None:
        loader = ExplicitPluginFactoryLoader()

        with self.assertRaises(ExplicitPluginFactoryLoaderError) as caught:
            loader.load(
                PluginManifest(plugin_id="echo", version="2.0.0")
            )

        self.assertEqual(
            caught.exception.code,
            PLUGIN_FACTORY_LOADER_ERROR_UNSUPPORTED_MANIFEST,
        )

    def test_unsupported_manifest_is_normalized(self) -> None:
        unsupported = ExplicitPluginFactoryLoader(factories={})
        service, _, _, _ = self.service(loader=unsupported)

        with self.assertRaises(PluginLoadingError) as caught:
            service.load("echo", "1.0.0")

        self.assertEqual(
            caught.exception.code,
            PLUGIN_LOADING_ERROR_MANIFEST_NOT_SUPPORTED,
        )

    def test_loader_exception_is_normalized_without_retry(self) -> None:
        loader = RecordingLoader(
            error=RuntimeError("sensitive factory failure")
        )
        service, store, _, _ = self.service(loader=loader)

        with self.assertRaises(PluginLoadingError) as caught:
            service.load("echo", "1.0.0")

        self.assertEqual(loader.calls, 1)
        self.assertEqual(store.count, 0)
        self.assertEqual(
            caught.exception.code,
            PLUGIN_LOADING_ERROR_LOAD_FAILED,
        )
        self.assertNotIn("sensitive", str(caught.exception))

    def test_wrong_loaded_plugin_id_is_rejected(self) -> None:
        loader = RecordingLoader(result=FakePlugin(plugin_id="other"))
        service, store, _, _ = self.service(loader=loader)

        with self.assertRaises(PluginLoadingError) as caught:
            service.load("echo", "1.0.0")

        self.assertEqual(store.count, 0)
        self.assertEqual(
            caught.exception.code,
            PLUGIN_LOADING_ERROR_IDENTITY_MISMATCH,
        )

    def test_wrong_loaded_plugin_version_is_rejected(self) -> None:
        loader = RecordingLoader(result=FakePlugin(version="2.0.0"))
        service, store, _, _ = self.service(loader=loader)

        with self.assertRaises(PluginLoadingError) as caught:
            service.load("echo", "1.0.0")

        self.assertEqual(store.count, 0)
        self.assertEqual(
            caught.exception.code,
            PLUGIN_LOADING_ERROR_IDENTITY_MISMATCH,
        )

    def test_invalid_loaded_plugin_name_is_rejected(self) -> None:
        loader = RecordingLoader(result=FakePlugin(name=" "))
        service, store, _, _ = self.service(loader=loader)

        with self.assertRaises(PluginLoadingError) as caught:
            service.load("echo", "1.0.0")

        self.assertEqual(store.count, 0)
        self.assertEqual(
            caught.exception.code,
            PLUGIN_LOADING_ERROR_PLUGIN_INVALID,
        )

    def test_non_callable_execute_surface_is_rejected(self) -> None:
        loader = RecordingLoader(
            result=FakePlugin(callable_execute=False)
        )
        service, store, _, _ = self.service(loader=loader)

        with self.assertRaises(PluginLoadingError) as caught:
            service.load("echo", "1.0.0")

        self.assertEqual(store.count, 0)
        self.assertEqual(
            caught.exception.code,
            PLUGIN_LOADING_ERROR_PLUGIN_INVALID,
        )

    def test_loading_never_executes_plugin(self) -> None:
        plugin = FakePlugin()
        loader = RecordingLoader(result=plugin)
        service, _, _, _ = self.service(loader=loader)

        service.load("echo", "1.0.0")

        self.assertEqual(plugin.execute_calls, 0)

    def test_invalid_request_identity_fails_before_governance_or_discovery(self) -> None:
        governance = PluginGovernanceDecisionStore()
        service, _, discovery, loader = self.service(
            governance_store=governance,
            snapshots=[RuntimeError("must not run")],
        )

        cases = (
            (" echo ", "1.0.0", PLUGIN_LOADING_ERROR_INVALID_PLUGIN_ID),
            ("echo", "", PLUGIN_LOADING_ERROR_INVALID_PLUGIN_VERSION),
        )
        for plugin_id, version, expected in cases:
            with self.subTest(plugin_id=plugin_id, version=version):
                with self.assertRaises(PluginLoadingError) as caught:
                    service.load(plugin_id, version)
                self.assertEqual(caught.exception.code, expected)

        self.assertEqual(discovery.calls, 0)
        self.assertEqual(loader.calls, 0)

    def test_service_surface_does_not_expose_loaded_plugin_object(self) -> None:
        service, store, _, _ = self.service()
        service.load("echo", "1.0.0")

        self.assertFalse(hasattr(service, "resolve_plugin"))
        self.assertFalse(hasattr(service, "execute"))
        self.assertFalse(hasattr(service, "register"))
        self.assertFalse(hasattr(store, "resolve_plugin"))
        record = service.resolve("echo", "1.0.0")
        self.assertIsInstance(record, LoadedPluginRecord)

    def test_loading_does_not_mutate_plugin_registry(self) -> None:
        service, _, _, _ = self.service()
        registry = InMemoryPluginRegistry()

        service.load("echo", "1.0.0")

        with self.assertRaises(PluginNotFoundError):
            registry.resolve("echo")

    def test_loading_does_not_mutate_adapter_registry(self) -> None:
        service, _, _, _ = self.service()
        registry = AdapterRegistry(())

        service.load("echo", "1.0.0")

        self.assertEqual(registry.adapter_ids, ())
        self.assertIsNone(registry.resolve_module("module.plugin.echo"))

    def test_loading_does_not_create_d44_permission(self) -> None:
        service, _, _, _ = self.service()
        before = PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS

        service.load("echo", "1.0.0")

        self.assertIs(PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS, before)

    def test_loading_does_not_create_d45_execution_approval(self) -> None:
        service, _, _, _ = self.service()
        approval_store = PendingExecutionApprovalStore()

        service.load("echo", "1.0.0")

        self.assertEqual(approval_store.pending_count, 0)

    def test_legacy_default_loader_remains_unimplemented(self) -> None:
        loader = DefaultPluginLoader()

        with self.assertRaises(NotImplementedError):
            loader.load(
                PluginManifest(plugin_id="echo", version="1.0.0")
            )


if __name__ == "__main__":
    unittest.main()
