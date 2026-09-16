import json
import unittest

from app.connectors.github_public_repository import GitHubPublicRepositoryMetadata
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep
from app.plugins.default_plugin_discovery import DefaultPluginDiscovery
from app.plugins.explicit_plugin_factory_loader import ExplicitPluginFactoryLoader
from app.plugins.github_public_repository import GitHubPublicRepositoryPlugin
from app.services.adapter_registry import AdapterRegistry
from app.services.capability_permission_policy import (
    CapabilityPermissionPolicy,
    PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS,
)
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.execution_planner import ExecutionPlanner
from app.services.module_runtime import ModuleRuntime
from app.services.plugin_candidate_discovery import PluginCandidateDiscovery
from app.services.plugin_governance import (
    PluginGovernanceDecisionStore,
    PluginGovernanceService,
)
from app.services.plugin_loading import (
    LoadedPluginStore,
    PLUGIN_LOADING_ERROR_GOVERNANCE_NOT_FOUND,
    PluginLoadingError,
    PluginLoadingService,
)
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


class FakeReader:
    def __init__(self) -> None:
        self.calls = 0

    def get_repository_metadata(self, reference):
        self.calls += 1
        return GitHubPublicRepositoryMetadata(
            full_name="openai/openai-python",
            description="OpenAI Python library",
            html_url="https://github.com/openai/openai-python",
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


class D59ExternalConnectorLifecycleTests(unittest.TestCase):
    def compose(self):
        reader = FakeReader()
        projection_catalog = PluginProjectionCatalog(
            PRODUCTION_PLUGIN_CAPABILITY_PROJECTIONS
        )
        candidate_discovery = PluginCandidateDiscovery(
            discovery=DefaultPluginDiscovery(),
            projection_catalog=projection_catalog,
        )
        governance_store = PluginGovernanceDecisionStore()
        governance = PluginGovernanceService(
            candidate_discovery=candidate_discovery,
            store=governance_store,
        )
        loader = ExplicitPluginFactoryLoader(
            {
                ("github_public_repo", "1.0.0"): (
                    lambda: GitHubPublicRepositoryPlugin(client=reader)
                )
            }
        )
        loaded_store = LoadedPluginStore()
        loading = PluginLoadingService(
            candidate_discovery=candidate_discovery,
            governance=governance,
            loader=loader,
            store=loaded_store,
        )
        exposure_store = PluginModuleExposureStore()
        exposure = PluginModuleExposureService(
            projection_catalog=projection_catalog,
            candidate_discovery=candidate_discovery,
            governance=governance,
            loading=loading,
            loaded_store=loaded_store,
            exposure_store=exposure_store,
        )
        binding_store = PluginPermissionBindingStore()
        binding = PluginPermissionBindingService(
            exposure_service=exposure,
            profile_catalog=PluginPermissionProfileCatalog(
                PRODUCTION_PLUGIN_CAPABILITY_PERMISSION_PROFILES
            ),
            store=binding_store,
            reserved_permissions=PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS,
        )
        activation_store = PluginRegistrationActivationStore()
        activation = PluginRegistrationActivationService(
            binding_service=binding,
            exposure_service=exposure,
            store=activation_store,
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

    def advance_to_activation(self):
        parts = self.compose()
        reader, _, governance, loading, exposure, binding, activation = parts
        governance.admit("github_public_repo", "1.0.0")
        loading.load("github_public_repo", "1.0.0")
        exposure.expose("github_public_repo", "1.0.0", "repository_metadata")
        binding.bind("github_public_repo", "1.0.0", "repository_metadata")
        activation.activate("github_public_repo", "1.0.0", "repository_metadata")
        self.assertEqual(reader.calls, 0)
        return parts

    def test_production_connector_is_known_but_default_deny(self):
        reader, candidate_discovery, governance, loading, exposure, binding, activation = self.compose()
        candidates = candidate_discovery.discover_candidates()
        self.assertEqual(len(candidates), 3)
        github = next(
            candidate
            for candidate in candidates
            if candidate.plugin_id == "github_public_repo"
        )
        self.assertEqual(github.status, "projected_match")
        self.assertEqual(
            github.projected_capability_names,
            ("repository_metadata",),
        )
        self.assertIsNone(governance.resolve("github_public_repo", "1.0.0"))
        self.assertEqual(loading.list_loaded(), ())
        self.assertEqual(exposure.list_exposures(), ())
        self.assertEqual(binding.list_bindings(), ())
        self.assertEqual(activation.list_activations(), ())
        self.assertEqual(reader.calls, 0)

    def test_load_requires_explicit_governance_admission(self):
        reader, _, _, loading, _, _, _ = self.compose()
        with self.assertRaises(PluginLoadingError) as caught:
            loading.load("github_public_repo", "1.0.0")
        self.assertEqual(
            caught.exception.code,
            PLUGIN_LOADING_ERROR_GOVERNANCE_NOT_FOUND,
        )
        self.assertEqual(reader.calls, 0)

    def test_explicit_d54_through_d58_lifecycle_causes_no_network(self):
        reader, _, governance, loading, exposure, binding, activation = self.compose()
        governance.admit("github_public_repo", "1.0.0")
        loading.load("github_public_repo", "1.0.0")
        exposure.expose("github_public_repo", "1.0.0", "repository_metadata")
        bound = binding.bind("github_public_repo", "1.0.0", "repository_metadata")
        active = activation.activate("github_public_repo", "1.0.0", "repository_metadata")
        self.assertEqual(bound.effect, "read")
        self.assertEqual(bound.data_class, "external_data")
        self.assertTrue(bound.owner_approval_required)
        self.assertEqual(active.capability_id, bound.capability_id)
        self.assertEqual(reader.calls, 0)

    def test_d58_snapshot_registers_exact_read_external_data_permission(self):
        reader, _, _, _, _, _, activation = self.advance_to_activation()
        snapshot = activation.runtime_snapshot()
        self.assertEqual(len(snapshot.adapters), 1)
        self.assertEqual(len(snapshot.permissions), 1)
        permission = snapshot.permissions[0]
        self.assertEqual(permission.target_kind, "module")
        self.assertEqual(permission.adapter_id, "module.plugin.github_public_repo")
        self.assertEqual(permission.operation, "get_repository_metadata")
        self.assertEqual(permission.effect, "read")
        self.assertEqual(permission.data_class, "external_data")
        self.assertTrue(permission.owner_approval_required)
        self.assertEqual(reader.calls, 0)

    def test_execution_planner_requires_owner_approval(self):
        reader, _, _, _, _, _, activation = self.advance_to_activation()
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
        request = CommandRequest(
            request_id="req-d59-plan",
            command="module.execute",
            arguments={
                "adapter_id": "module.plugin.github_public_repo",
                "operation": "get_repository_metadata",
                "parameters": {"content": "openai/openai-python"},
            },
        )
        outcome = planner.plan(request)
        self.assertEqual(outcome.status, "planned")
        self.assertIsNotNone(outcome.plan)
        self.assertTrue(outcome.plan.owner_approval_required)
        self.assertEqual(reader.calls, 0)

    def test_module_runtime_rejects_without_d36_authorization(self):
        reader, _, _, _, _, _, activation = self.advance_to_activation()
        snapshot = activation.runtime_snapshot()
        runtime = ModuleRuntime(registry=AdapterRegistry(snapshot.adapters))
        request = CommandRequest(
            request_id="req-d59-auth",
            command="module.execute",
        )
        result = runtime.execute(request, object())  # type: ignore[arg-type]
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error, "module_authorization_rejected")
        self.assertEqual(reader.calls, 0)

    def test_post_authorization_adapter_seam_reads_once(self):
        reader, _, _, _, _, _, activation = self.advance_to_activation()
        snapshot = activation.runtime_snapshot()
        request = CommandRequest(
            request_id="req-d59-exec",
            command="module.execute",
        )
        plan = ExecutionPlan(
            request_id="req-d59-exec",
            adapter_id="module.plugin.github_public_repo",
            steps=(
                ExecutionStep(
                    sequence=1,
                    operation="get_repository_metadata",
                    parameters={"content": "openai/openai-python"},
                ),
            ),
            owner_approval_required=False,
        )
        result = snapshot.adapters[0].execute(request, plan)
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(reader.calls, 1)
        parsed = json.loads(result.output["content"])
        self.assertEqual(parsed["full_name"], "openai/openai-python")

    def test_activation_service_exposes_no_direct_execution_method(self):
        *_, activation = self.compose()
        self.assertFalse(hasattr(activation, "execute"))
        self.assertFalse(hasattr(activation, "approve"))
        self.assertFalse(hasattr(activation, "authorize"))


if __name__ == "__main__":
    unittest.main()
