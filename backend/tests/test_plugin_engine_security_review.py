from tests.workspace_fixture import TEST_WORKSPACE_SCOPE
import inspect
import unittest

from app.adapters.activated_plugin_module import PLUGIN_REGISTRATION_INACTIVE
from app.api import dependencies
from app.api.router import api_router
from app.api.v1.execution_approvals import require_local_execution_request_marker
from app.connectors.github_public_repository import GitHubPublicRepositoryMetadata
from app.contracts.command import CommandRequest
from app.plugins.default_plugin_discovery import DefaultPluginDiscovery
from app.plugins.explicit_plugin_factory_loader import ExplicitPluginFactoryLoader
from app.plugins.github_public_repository import GitHubPublicRepositoryPlugin
from app.services.adapter_registry import AdapterRegistry
from app.services.capability_permission_policy import (
    CapabilityPermissionPolicy,
    PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS,
)
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.command_execution_coordinator import CommandExecutionCoordinator
from app.services.execution_approval_service import (
    ExecutionApprovalPlanMismatchError,
    ExecutionApprovalService,
    PendingExecutionApprovalStore,
)
from app.services.execution_guard import ExecutionGuard
from app.services.execution_planner import ExecutionPlanner
from app.services.module_runtime import ModuleRuntime
from app.services.plugin_candidate_discovery import PluginCandidateDiscovery
from app.services.plugin_governance import (
    PluginGovernanceDecisionStore,
    PluginGovernanceService,
)
from app.services.plugin_loading import LoadedPluginStore, PluginLoadingService
from app.services.plugin_module_exposure import (
    PluginModuleExposureService,
    PluginModuleExposureStore,
)
from app.services.plugin_permission_binding import (
    PRODUCTION_PLUGIN_CAPABILITY_PERMISSION_PROFILES,
    PluginPermissionBindingService,
    PluginPermissionBindingStore,
    PluginPermissionProfileCatalog,
)
from app.services.plugin_projection_catalog import (
    PRODUCTION_PLUGIN_CAPABILITY_PROJECTIONS,
    PluginProjectionCatalog,
)
from app.services.plugin_registration_activation import (
    PluginRegistrationActivationService,
    PluginRegistrationActivationStore,
)
from app.services.tool_runtime import ToolRuntime


PLUGIN_ID = "github_public_repo"
PLUGIN_VERSION = "1.0.0"
CAPABILITY_NAME = "repository_metadata"
ADAPTER_ID = "module.plugin.github_public_repo"
OPERATION = "get_repository_metadata"
CAPABILITY_ID = "exec.plugin.github_public_repo.repository_metadata"
REFERENCE = "openai/openai-python"


class RecordingReader:
    def __init__(self) -> None:
        self.calls = 0

    def get_repository_metadata(self, reference):
        self.calls += 1
        return GitHubPublicRepositoryMetadata(
            full_name=REFERENCE,
            description="OpenAI Python library",
            html_url=f"https://github.com/{REFERENCE}",
            default_branch="main",
            language="Python",
            visibility="public",
            archived=False,
            fork=False,
            stargazers_count=10,
            forks_count=2,
            open_issues_count=1,
            license="Apache-2.0",
            updated_at="2026-09-15T00:00:00Z",
        )


class PluginEngineSecurityReviewTests(unittest.TestCase):
    def compose(self):
        reader = RecordingReader()
        projection_catalog = PluginProjectionCatalog(
            PRODUCTION_PLUGIN_CAPABILITY_PROJECTIONS
        )
        candidate_discovery = PluginCandidateDiscovery(
            discovery=DefaultPluginDiscovery(),
            projection_catalog=projection_catalog,
        )
        governance = PluginGovernanceService(
            candidate_discovery=candidate_discovery,
            store=PluginGovernanceDecisionStore(),
        )
        loaded_store = LoadedPluginStore()
        loading = PluginLoadingService(
            candidate_discovery=candidate_discovery,
            governance=governance,
            loader=ExplicitPluginFactoryLoader(
                {
                    (PLUGIN_ID, PLUGIN_VERSION): (
                        lambda: GitHubPublicRepositoryPlugin(client=reader)
                    )
                }
            ),
            store=loaded_store,
        )
        exposure = PluginModuleExposureService(
            projection_catalog=projection_catalog,
            candidate_discovery=candidate_discovery,
            governance=governance,
            loading=loading,
            loaded_store=loaded_store,
            exposure_store=PluginModuleExposureStore(),
        )
        binding = PluginPermissionBindingService(
            exposure_service=exposure,
            profile_catalog=PluginPermissionProfileCatalog(
                PRODUCTION_PLUGIN_CAPABILITY_PERMISSION_PROFILES
            ),
            store=PluginPermissionBindingStore(),
            reserved_permissions=PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS,
        )
        activation = PluginRegistrationActivationService(
            binding_service=binding,
            exposure_service=exposure,
            store=PluginRegistrationActivationStore(),
            reserved_adapter_ids=tuple(
                permission.adapter_id
                for permission in PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS
            ),
            reserved_permissions=PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS,
        )
        return (
            reader,
            candidate_discovery,
            governance,
            loading,
            exposure,
            binding,
            activation,
        )

    def activate(self):
        parts = self.compose()
        reader, _, governance, loading, exposure, binding, activation = parts
        governance.admit(PLUGIN_ID, PLUGIN_VERSION)
        loading.load(PLUGIN_ID, PLUGIN_VERSION)
        exposure.expose(PLUGIN_ID, PLUGIN_VERSION, CAPABILITY_NAME)
        binding.bind(PLUGIN_ID, PLUGIN_VERSION, CAPABILITY_NAME)
        activation.activate(PLUGIN_ID, PLUGIN_VERSION, CAPABILITY_NAME)
        self.assertEqual(reader.calls, 0)
        return parts

    @staticmethod
    def execution_lane(activation):
        snapshot = activation.runtime_snapshot()
        registry = AdapterRegistry(snapshot.adapters)
        policy = CapabilityPermissionPolicy(
            registry=registry,
            permissions=snapshot.permissions,
        )
        planner = ExecutionPlanner(
            registry=registry,
            decision_engine=CommandDecisionEngine(),
            ai_router=None,  # type: ignore[arg-type]
            ai_discovery=None,  # type: ignore[arg-type]
            permission_policy=policy,
        )
        guard = ExecutionGuard(
            registry=registry,
            permission_policy=policy,
        )
        coordinator = CommandExecutionCoordinator(
            planner=planner,
            guard=guard,
            tool_runtime=ToolRuntime(registry=registry),
            module_runtime=ModuleRuntime(registry=registry),
        )
        approval = ExecutionApprovalService(
            workspace_scope=TEST_WORKSPACE_SCOPE,
            planner=planner,
            permission_policy=policy,
            coordinator=coordinator,
            store=PendingExecutionApprovalStore(),
        )
        return coordinator, approval

    @staticmethod
    def request(request_id):
        return CommandRequest(
            request_id=request_id,
            command="module.execute",
            arguments={
                "adapter_id": ADAPTER_ID,
                "operation": OPERATION,
                "parameters": {"content": REFERENCE},
            },
        )

    def pending_proposal(self, approval):
        outcome = approval.propose(
            target_kind="module",
            adapter_id=ADAPTER_ID,
            operation=OPERATION,
            parameters={"content": REFERENCE},
        )
        self.assertEqual(outcome.status, "pending")
        self.assertIsNotNone(outcome.proposal)
        assert outcome.proposal is not None
        return outcome.proposal

    def test_lifecycle_through_activation_performs_no_network(self):
        reader, candidates, governance, loading, exposure, binding, activation = (
            self.compose()
        )
        self.assertEqual(len(candidates.discover_candidates()), 3)
        governance.admit(PLUGIN_ID, PLUGIN_VERSION)
        loading.load(PLUGIN_ID, PLUGIN_VERSION)
        exposure.expose(PLUGIN_ID, PLUGIN_VERSION, CAPABILITY_NAME)
        binding.bind(PLUGIN_ID, PLUGIN_VERSION, CAPABILITY_NAME)
        activation.activate(PLUGIN_ID, PLUGIN_VERSION, CAPABILITY_NAME)
        activation.runtime_snapshot()
        self.assertEqual(reader.calls, 0)

    def test_d45_and_d36_fail_closed_until_exact_approval(self):
        reader, *_, activation = self.activate()
        coordinator, approval = self.execution_lane(activation)

        blocked = coordinator.execute(self.request("req-d60-blocked"))
        self.assertEqual(blocked.status, "blocked")
        self.assertEqual(blocked.reason_code, "owner_approval_required")
        self.assertEqual(reader.calls, 0)

        proposal = self.pending_proposal(approval)
        self.assertTrue(proposal.owner_approval_required)
        self.assertEqual(reader.calls, 0)

        with self.assertRaises(ExecutionApprovalPlanMismatchError):
            approval.approve(proposal.approval_id, "0" * 64)
        self.assertEqual(reader.calls, 0)

    def test_exact_owner_approval_reaches_connector_once(self):
        reader, *_, activation = self.activate()
        _, approval = self.execution_lane(activation)
        proposal = self.pending_proposal(approval)

        decision = approval.approve(
            proposal.approval_id,
            proposal.plan_digest,
        )

        self.assertEqual(decision.execution.status, "completed")
        self.assertIsNotNone(decision.execution.authorization)
        assert decision.execution.authorization is not None
        self.assertEqual(decision.execution.authorization.status, "authorized")
        self.assertIsNotNone(decision.execution.result)
        assert decision.execution.result is not None
        self.assertEqual(decision.execution.result.status, "succeeded")
        self.assertEqual(reader.calls, 1)

    def test_deactivation_invalidates_already_proposed_stale_lane(self):
        reader, *_, activation = self.activate()
        _, approval = self.execution_lane(activation)
        proposal = self.pending_proposal(approval)

        activation.deactivate(PLUGIN_ID, PLUGIN_VERSION, CAPABILITY_NAME)
        decision = approval.approve(
            proposal.approval_id,
            proposal.plan_digest,
        )

        self.assertIsNotNone(decision.execution.result)
        assert decision.execution.result is not None
        self.assertEqual(decision.execution.result.status, "failed")
        self.assertEqual(
            decision.execution.result.error,
            PLUGIN_REGISTRATION_INACTIVE,
        )
        self.assertEqual(reader.calls, 0)

    def test_governance_revocation_invalidates_proposed_stale_lane(self):
        reader, _, governance, _, _, _, activation = self.activate()
        _, approval = self.execution_lane(activation)
        proposal = self.pending_proposal(approval)

        governance.revoke(PLUGIN_ID, PLUGIN_VERSION)
        decision = approval.approve(
            proposal.approval_id,
            proposal.plan_digest,
        )

        self.assertIsNotNone(decision.execution.result)
        assert decision.execution.result is not None
        self.assertEqual(decision.execution.result.status, "failed")
        self.assertEqual(
            decision.execution.result.error,
            PLUGIN_REGISTRATION_INACTIVE,
        )
        self.assertEqual(reader.calls, 0)

    def test_d59_production_permission_profile_remains_exact(self):
        self.assertEqual(
            len(PRODUCTION_PLUGIN_CAPABILITY_PERMISSION_PROFILES),
            3,
        )
        profile = next(
            item
            for item in PRODUCTION_PLUGIN_CAPABILITY_PERMISSION_PROFILES
            if item.plugin_id == PLUGIN_ID
        )
        self.assertEqual(
            (
                profile.plugin_id,
                profile.plugin_version,
                profile.capability_name,
                profile.capability_id,
                profile.module_adapter_id,
                profile.operation,
                profile.effect,
                profile.data_class,
                profile.owner_approval_required,
            ),
            (
                PLUGIN_ID,
                PLUGIN_VERSION,
                CAPABILITY_NAME,
                CAPABILITY_ID,
                ADAPTER_ID,
                OPERATION,
                "read",
                "external_data",
                True,
            ),
        )

    def test_legacy_runtime_and_registrar_are_quarantined_from_dependencies(self):
        source = inspect.getsource(dependencies)
        self.assertNotIn("DefaultPluginRuntime", source)
        self.assertNotIn("DefaultPluginRegistrar", source)

    def test_api_has_no_plugin_lifecycle_control_routes(self):
        paths = tuple(getattr(route, "path", "") for route in api_router.routes)
        forbidden = (
            "plugin-governance",
            "plugin-load",
            "plugin-exposure",
            "plugin-binding",
            "plugin-activation",
            "plugin-activate",
            "plugin-deactivate",
        )
        for path in paths:
            for fragment in forbidden:
                self.assertNotIn(fragment, path)

    def test_local_request_marker_is_documented_as_non_authentication(self):
        doc = inspect.getdoc(require_local_execution_request_marker) or ""
        self.assertIn("not authentication", doc)


if __name__ == "__main__":
    unittest.main()
