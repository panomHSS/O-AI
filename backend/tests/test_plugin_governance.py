import unittest
from dataclasses import FrozenInstanceError

from app.api.dependencies import (
    get_plugin_governance_service,
    get_plugin_governance_store,
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
from app.plugins.exceptions import PluginNotFoundError
from app.plugins.in_memory_registry import InMemoryPluginRegistry
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
from app.services.plugin_governance import (
    PLUGIN_GOVERNANCE_ERROR_CANDIDATE_NOT_ELIGIBLE,
    PLUGIN_GOVERNANCE_ERROR_CANDIDATE_NOT_FOUND,
    PLUGIN_GOVERNANCE_ERROR_CANDIDATE_RESOLUTION_FAILED,
    PLUGIN_GOVERNANCE_ERROR_DECISION_NOT_FOUND,
    PLUGIN_GOVERNANCE_ERROR_INVALID_PLUGIN_ID,
    PLUGIN_GOVERNANCE_ERROR_INVALID_PLUGIN_VERSION,
    PLUGIN_GOVERNANCE_ERROR_INVALID_TRANSITION,
    PLUGIN_GOVERNANCE_ERROR_STORE_FULL,
    PLUGIN_GOVERNANCE_ERROR_SUBJECT_MISMATCH,
    PluginGovernanceDecisionStore,
    PluginGovernanceError,
    PluginGovernanceService,
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


class PluginGovernanceTests(unittest.TestCase):
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

    @classmethod
    def service(
        cls,
        *snapshots,
        max_decisions: int = 100,
    ):
        discovery = SequenceCandidateDiscovery(snapshots or [()])
        store = PluginGovernanceDecisionStore(
            max_decisions=max_decisions,
        )
        service = PluginGovernanceService(
            candidate_discovery=discovery,  # type: ignore[arg-type]
            store=store,
        )
        return service, store, discovery

    def test_production_governance_starts_default_deny_and_empty(self) -> None:
        store = get_plugin_governance_store()
        store.clear()
        service = get_plugin_governance_service()

        self.assertIs(store, get_plugin_governance_store())
        self.assertIs(service, get_plugin_governance_service())
        self.assertEqual(store.count, 0)
        self.assertEqual(service.list_decisions(), ())
        self.assertIsNone(service.resolve("echo", "1.0.0"))

    def test_no_decision_is_not_admitted(self) -> None:
        service, _, _ = self.service(())

        self.assertIsNone(service.resolve("echo", "1.0.0"))

    def test_exact_projected_candidate_can_be_admitted(self) -> None:
        candidate = self.candidate()
        service, _, discovery = self.service((candidate,))

        decision = service.admit("echo", "1.0.0")

        self.assertEqual(discovery.calls, 1)
        self.assertEqual(decision.state, PLUGIN_GOVERNANCE_STATE_ADMITTED)

    def test_admission_binds_exact_plugin_id_and_version(self) -> None:
        candidate = self.candidate()
        service, _, _ = self.service((candidate,))

        decision = service.admit("echo", "1.0.0")

        self.assertEqual(decision.plugin_id, "echo")
        self.assertEqual(decision.plugin_version, "1.0.0")
        self.assertIsNone(service.resolve("echo", "2.0.0"))

    def test_admission_binds_exact_projected_capabilities(self) -> None:
        candidate = self.candidate(
            capabilities=("search", "echo", "inspect"),
        )
        service, _, _ = self.service((candidate,))

        decision = service.admit("echo", "1.0.0")

        self.assertEqual(
            decision.projected_capability_names,
            ("echo", "inspect", "search"),
        )

    def test_unprojected_candidate_cannot_be_admitted(self) -> None:
        candidate = self.candidate(
            plugin_id="unknown",
            status=PLUGIN_CANDIDATE_STATUS_UNPROJECTED,
        )
        service, _, _ = self.service((candidate,))

        with self.assertRaises(PluginGovernanceError) as caught:
            service.admit("unknown", "1.0.0")

        self.assertEqual(
            caught.exception.code,
            PLUGIN_GOVERNANCE_ERROR_CANDIDATE_NOT_ELIGIBLE,
        )

    def test_version_mismatch_candidate_cannot_be_admitted(self) -> None:
        candidate = self.candidate(
            plugin_version="2.0.0",
            status=PLUGIN_CANDIDATE_STATUS_VERSION_MISMATCH,
        )
        service, _, _ = self.service((candidate,))

        with self.assertRaises(PluginGovernanceError) as caught:
            service.admit("echo", "2.0.0")

        self.assertEqual(
            caught.exception.code,
            PLUGIN_GOVERNANCE_ERROR_CANDIDATE_NOT_ELIGIBLE,
        )

    def test_candidate_not_found_fails_closed(self) -> None:
        service, _, discovery = self.service(())

        with self.assertRaises(PluginGovernanceError) as caught:
            service.admit("echo", "1.0.0")

        self.assertEqual(discovery.calls, 1)
        self.assertEqual(
            caught.exception.code,
            PLUGIN_GOVERNANCE_ERROR_CANDIDATE_NOT_FOUND,
        )

    def test_candidate_discovery_failure_is_normalized(self) -> None:
        error = PluginCandidateDiscoveryError("discovery_failed")
        service, _, discovery = self.service(error)

        with self.assertRaises(PluginGovernanceError) as caught:
            service.admit("echo", "1.0.0")

        self.assertEqual(discovery.calls, 1)
        self.assertEqual(
            caught.exception.code,
            PLUGIN_GOVERNANCE_ERROR_CANDIDATE_RESOLUTION_FAILED,
        )
        self.assertNotIn("discovery_failed", str(caught.exception))

    def test_admit_discovers_exactly_once(self) -> None:
        candidate = self.candidate()
        service, _, discovery = self.service((candidate,))

        service.admit("echo", "1.0.0")

        self.assertEqual(discovery.calls, 1)

    def test_reject_discovers_exactly_once(self) -> None:
        candidate = self.candidate()
        service, _, discovery = self.service((candidate,))

        decision = service.reject("echo", "1.0.0")

        self.assertEqual(discovery.calls, 1)
        self.assertEqual(decision.state, PLUGIN_GOVERNANCE_STATE_REJECTED)

    def test_none_to_admitted(self) -> None:
        candidate = self.candidate()
        service, _, _ = self.service((candidate,))

        self.assertEqual(
            service.admit("echo", "1.0.0").state,
            PLUGIN_GOVERNANCE_STATE_ADMITTED,
        )

    def test_none_to_rejected(self) -> None:
        candidate = self.candidate()
        service, _, _ = self.service((candidate,))

        self.assertEqual(
            service.reject("echo", "1.0.0").state,
            PLUGIN_GOVERNANCE_STATE_REJECTED,
        )

    def test_rejected_to_admitted_is_explicit_reconsideration(self) -> None:
        candidate = self.candidate()
        service, _, _ = self.service((candidate,), (candidate,))

        service.reject("echo", "1.0.0")
        decision = service.admit("echo", "1.0.0")

        self.assertEqual(decision.state, PLUGIN_GOVERNANCE_STATE_ADMITTED)

    def test_admitted_to_revoked(self) -> None:
        candidate = self.candidate()
        service, _, discovery = self.service((candidate,))

        service.admit("echo", "1.0.0")
        decision = service.revoke("echo", "1.0.0")

        self.assertEqual(discovery.calls, 1)
        self.assertEqual(decision.state, PLUGIN_GOVERNANCE_STATE_REVOKED)

    def test_revoked_to_admitted_is_explicit_readmission(self) -> None:
        candidate = self.candidate()
        service, _, _ = self.service((candidate,), (candidate,))

        service.admit("echo", "1.0.0")
        service.revoke("echo", "1.0.0")
        decision = service.admit("echo", "1.0.0")

        self.assertEqual(decision.state, PLUGIN_GOVERNANCE_STATE_ADMITTED)

    def test_repeated_same_state_is_idempotent(self) -> None:
        candidate = self.candidate()
        service, _, discovery = self.service((candidate,), (candidate,))

        first = service.admit("echo", "1.0.0")
        second = service.admit("echo", "1.0.0")

        self.assertIs(first, second)
        self.assertEqual(discovery.calls, 2)

    def test_admitted_to_rejected_is_invalid_transition(self) -> None:
        candidate = self.candidate()
        service, _, _ = self.service((candidate,), (candidate,))

        service.admit("echo", "1.0.0")
        with self.assertRaises(PluginGovernanceError) as caught:
            service.reject("echo", "1.0.0")

        self.assertEqual(
            caught.exception.code,
            PLUGIN_GOVERNANCE_ERROR_INVALID_TRANSITION,
        )

    def test_revoked_to_rejected_is_invalid_transition(self) -> None:
        candidate = self.candidate()
        service, _, _ = self.service((candidate,), (candidate,))

        service.admit("echo", "1.0.0")
        service.revoke("echo", "1.0.0")
        with self.assertRaises(PluginGovernanceError) as caught:
            service.reject("echo", "1.0.0")

        self.assertEqual(
            caught.exception.code,
            PLUGIN_GOVERNANCE_ERROR_INVALID_TRANSITION,
        )

    def test_revoke_does_not_depend_on_discovery_availability(self) -> None:
        candidate = self.candidate()
        discovery_error = RuntimeError("discovery offline")
        service, _, discovery = self.service(
            (candidate,),
            discovery_error,
        )

        service.admit("echo", "1.0.0")
        decision = service.revoke("echo", "1.0.0")

        self.assertEqual(discovery.calls, 1)
        self.assertEqual(decision.state, PLUGIN_GOVERNANCE_STATE_REVOKED)

    def test_revoke_without_decision_fails_closed(self) -> None:
        service, _, discovery = self.service(
            RuntimeError("must not be called")
        )

        with self.assertRaises(PluginGovernanceError) as caught:
            service.revoke("echo", "1.0.0")

        self.assertEqual(discovery.calls, 0)
        self.assertEqual(
            caught.exception.code,
            PLUGIN_GOVERNANCE_ERROR_DECISION_NOT_FOUND,
        )

    def test_capability_subject_change_fails_closed(self) -> None:
        initial = self.candidate(capabilities=("echo",))
        changed = self.candidate(capabilities=("echo", "search"))
        service, _, discovery = self.service(
            (initial,),
            (changed,),
        )

        service.admit("echo", "1.0.0")
        with self.assertRaises(PluginGovernanceError) as caught:
            service.admit("echo", "1.0.0")

        self.assertEqual(discovery.calls, 2)
        self.assertEqual(
            caught.exception.code,
            PLUGIN_GOVERNANCE_ERROR_SUBJECT_MISMATCH,
        )

    def test_bounded_store_does_not_silently_evict(self) -> None:
        alpha = self.candidate(plugin_id="alpha")
        beta = self.candidate(plugin_id="beta")
        service, store, _ = self.service(
            (alpha, beta),
            (alpha, beta),
            max_decisions=1,
        )

        service.admit("alpha", "1.0.0")
        with self.assertRaises(PluginGovernanceError) as caught:
            service.admit("beta", "1.0.0")

        self.assertEqual(
            caught.exception.code,
            PLUGIN_GOVERNANCE_ERROR_STORE_FULL,
        )
        self.assertEqual(store.count, 1)
        self.assertIsNotNone(service.resolve("alpha", "1.0.0"))
        self.assertIsNone(service.resolve("beta", "1.0.0"))

    def test_decision_listing_is_deterministic(self) -> None:
        alpha = self.candidate(plugin_id="alpha")
        zeta = self.candidate(plugin_id="zeta")
        service, _, _ = self.service(
            (alpha, zeta),
            (alpha, zeta),
        )

        service.admit("zeta", "1.0.0")
        service.admit("alpha", "1.0.0")

        self.assertEqual(
            tuple(
                decision.plugin_id
                for decision in service.list_decisions()
            ),
            ("alpha", "zeta"),
        )

    def test_governance_decision_is_immutable(self) -> None:
        candidate = self.candidate()
        service, _, _ = self.service((candidate,))
        decision = service.admit("echo", "1.0.0")

        with self.assertRaises(FrozenInstanceError):
            decision.state = "rejected"  # type: ignore[misc]

    def test_invalid_subject_identifiers_fail_before_discovery(self) -> None:
        service, _, discovery = self.service(
            RuntimeError("must not be called")
        )

        cases = (
            (" echo ", "1.0.0", PLUGIN_GOVERNANCE_ERROR_INVALID_PLUGIN_ID),
            ("echo", "", PLUGIN_GOVERNANCE_ERROR_INVALID_PLUGIN_VERSION),
        )
        for plugin_id, version, expected in cases:
            with self.subTest(plugin_id=plugin_id, version=version):
                with self.assertRaises(PluginGovernanceError) as caught:
                    service.admit(plugin_id, version)
                self.assertEqual(caught.exception.code, expected)

        self.assertEqual(discovery.calls, 0)

    def test_governance_has_no_loader_registry_or_execution_surface(self) -> None:
        service, _, _ = self.service(())

        for name in (
            "_loader",
            "_plugin_registry",
            "_adapter_registry",
            "_permission_policy",
            "_approval_service",
            "_runtime",
            "load",
            "register",
            "execute",
        ):
            with self.subTest(name=name):
                self.assertFalse(hasattr(service, name))

    def test_governance_does_not_mutate_plugin_registry(self) -> None:
        candidate = self.candidate()
        service, _, _ = self.service((candidate,))
        registry = InMemoryPluginRegistry()

        service.admit("echo", "1.0.0")

        with self.assertRaises(PluginNotFoundError):
            registry.resolve("echo")

    def test_governance_does_not_mutate_adapter_registry(self) -> None:
        candidate = self.candidate()
        service, _, _ = self.service((candidate,))
        registry = AdapterRegistry(())

        service.admit("echo", "1.0.0")

        self.assertEqual(registry.adapter_ids, ())
        self.assertIsNone(registry.resolve_module("module.plugin.echo"))

    def test_governance_does_not_create_d44_permission(self) -> None:
        candidate = self.candidate()
        service, _, _ = self.service((candidate,))
        before = PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS

        service.admit("echo", "1.0.0")

        self.assertIs(
            PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS,
            before,
        )

    def test_governance_does_not_create_d45_execution_approval(self) -> None:
        candidate = self.candidate()
        service, _, _ = self.service((candidate,))
        approval_store = PendingExecutionApprovalStore()

        service.admit("echo", "1.0.0")

        self.assertEqual(approval_store.pending_count, 0)


if __name__ == "__main__":
    unittest.main()
