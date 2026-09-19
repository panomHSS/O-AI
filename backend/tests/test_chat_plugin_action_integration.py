from tests.workspace_fixture import TEST_WORKSPACE_SCOPE
import json
import unittest
from types import SimpleNamespace
from uuid import UUID

from app.connectors.github_public_repository import GitHubPublicRepositoryMetadata
from app.plugins.default_plugin_discovery import DefaultPluginDiscovery
from app.plugins.explicit_plugin_factory_loader import ExplicitPluginFactoryLoader
from app.plugins.github_public_repository import GitHubPublicRepositoryPlugin
from app.services.adapter_registry import AdapterRegistry
from app.services.capability_permission_policy import CapabilityPermissionPolicy
from app.services.chat_action_bridge import ChatActionBridge
from app.services.chat_plugin_action import (
    ChatPluginActionBindingStore,
    ChatPluginActionCompletionService,
    ChatPluginIntentRouter,
    FirstPartyPluginEnablementService,
)
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.command_execution_coordinator import CommandExecutionCoordinator
from app.services.execution_approval_service import (
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


CONVERSATION_ID = UUID("22222222-2222-2222-2222-222222222222")
REFERENCE = "openai/openai-python"


class FakeReader:
    def __init__(self) -> None:
        self.calls = 0

    def get_repository_metadata(self, reference):
        self.calls += 1
        return GitHubPublicRepositoryMetadata(
            full_name=REFERENCE,
            description="The official Python library for the OpenAI API.",
            html_url=f"https://github.com/{REFERENCE}",
            default_branch="main",
            language="Python",
            visibility="public",
            archived=False,
            fork=False,
            stargazers_count=12345,
            forks_count=2345,
            open_issues_count=321,
            license="Apache-2.0",
            updated_at="2026-09-15T00:00:00Z",
        )


class FakeConversationService:
    def __init__(self) -> None:
        self.user_messages: list[str] = []
        self.assistant_messages: list[str] = []

    def begin_turn(self, message, conversation_id=None, project_id=None):
        self.user_messages.append(message)
        return (
            SimpleNamespace(
                id=str(CONVERSATION_ID),
                project_id=None,
            ),
            [],
        )

    def complete_turn(self, conversation_id, reply, citations=None):
        self.assistant_messages.append(reply)


class ExplodingApprovalService:
    def propose(self, **kwargs):
        raise AssertionError("approval service must not be called")


class ChatPluginActionIntegrationTests(unittest.TestCase):
    def compose(self):
        reader = FakeReader()
        projection_catalog = PluginProjectionCatalog(
            PRODUCTION_PLUGIN_CAPABILITY_PROJECTIONS
        )
        discovery = PluginCandidateDiscovery(
            discovery=DefaultPluginDiscovery(),
            projection_catalog=projection_catalog,
        )
        governance = PluginGovernanceService(
            candidate_discovery=discovery,
            store=PluginGovernanceDecisionStore(),
        )
        loaded_store = LoadedPluginStore()
        loading = PluginLoadingService(
            candidate_discovery=discovery,
            governance=governance,
            loader=ExplicitPluginFactoryLoader(
                {
                    ("github_public_repo", "1.0.0"): (
                        lambda: GitHubPublicRepositoryPlugin(client=reader)
                    )
                }
            ),
            store=loaded_store,
        )
        exposure = PluginModuleExposureService(
            projection_catalog=projection_catalog,
            candidate_discovery=discovery,
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
            reserved_permissions=(),
        )
        activation = PluginRegistrationActivationService(
            binding_service=binding,
            exposure_service=exposure,
            store=PluginRegistrationActivationStore(),
            reserved_adapter_ids=(),
            reserved_permissions=(),
        )
        enablement = FirstPartyPluginEnablementService(
            governance=governance,
            loading=loading,
            exposure=exposure,
            binding=binding,
            activation=activation,
        )
        enablement.ensure_github_public_repository_enabled(True)
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
        conversations = FakeConversationService()
        binding_store = ChatPluginActionBindingStore()
        bridge = ChatActionBridge(
            conversation_service=conversations,  # type: ignore[arg-type]
            approval_service=approval,
            plugin_binding_store=binding_store,
            github_public_repo_connector_enabled=True,
        )
        completion = ChatPluginActionCompletionService(
            conversation_service=conversations,  # type: ignore[arg-type]
            binding_store=binding_store,
        )
        return (
            reader,
            governance,
            activation,
            approval,
            conversations,
            binding_store,
            bridge,
            completion,
        )

    def test_router_matches_one_canonical_github_repository(self):
        result = ChatPluginIntentRouter().classify(
            "ช่วยบอกข้อมูลของ GitHub repository "
            "openai/openai-python ให้หน่อย"
        )
        self.assertEqual(result.status, "matched")
        self.assertEqual(result.repository_reference, REFERENCE)

    def test_router_rejects_url_or_ambiguous_repository_request(self):
        router = ChatPluginIntentRouter()
        self.assertEqual(
            router.classify(
                "GitHub repository "
                "https://github.com/openai/openai-python"
            ).status,
            "invalid",
        )
        self.assertEqual(
            router.classify(
                "Compare GitHub repositories openai/openai-python "
                "and pallets/flask"
            ).status,
            "invalid",
        )

    def test_unrelated_chat_is_not_plugin_action(self):
        result = ChatPluginIntentRouter().classify(
            "ช่วยอธิบาย Python list comprehension"
        )
        self.assertEqual(result.status, "none")

    def test_disabled_connector_never_proposes_or_executes(self):
        conversations = FakeConversationService()
        bridge = ChatActionBridge(
            conversation_service=conversations,  # type: ignore[arg-type]
            approval_service=ExplodingApprovalService(),  # type: ignore[arg-type]
            github_public_repo_connector_enabled=False,
        )
        outcome = bridge.process(
            message=(
                "ช่วยดู GitHub repository "
                "openai/openai-python ให้หน่อย"
            )
        )
        self.assertEqual(outcome.status, "unavailable")
        self.assertEqual(
            outcome.reason_code,
            "github_public_repo_connector_disabled",
        )
        self.assertEqual(len(conversations.assistant_messages), 1)

    def test_proposal_performs_zero_connector_calls(self):
        reader, _, _, _, _, store, bridge, _ = self.compose()
        outcome = bridge.process(
            message=(
                "ช่วยบอกข้อมูลของ GitHub repository "
                "openai/openai-python ให้หน่อย"
            )
        )
        self.assertEqual(outcome.status, "pending_approval")
        self.assertEqual(reader.calls, 0)
        assert outcome.approval is not None
        assert outcome.approval.proposal is not None
        self.assertIsNotNone(
            store.resolve(outcome.approval.proposal.approval_id)
        )

    def test_deny_performs_zero_connector_calls_and_persists_reply(self):
        (
            reader,
            _,
            _,
            approval,
            conversations,
            _,
            bridge,
            completion,
        ) = self.compose()
        action = bridge.process(
            message=f"GitHub repository {REFERENCE} metadata please"
        )
        assert action.approval is not None
        assert action.approval.proposal is not None
        proposal = action.approval.proposal

        outcome = approval.deny(
            proposal.approval_id,
            proposal.plan_digest,
        )
        final = completion.complete(proposal.approval_id, outcome)

        self.assertEqual(reader.calls, 0)
        self.assertIsNotNone(final)
        assert final is not None
        self.assertIn("ยกเลิก", final.reply)
        self.assertEqual(
            conversations.assistant_messages[-1],
            final.reply,
        )

    def test_exact_approval_executes_once_and_persists_safe_chat_reply(self):
        (
            reader,
            _,
            _,
            approval,
            conversations,
            _,
            bridge,
            completion,
        ) = self.compose()
        action = bridge.process(
            message=(
                "ช่วยบอก stars และ license ของ GitHub repository "
                f"{REFERENCE}"
            )
        )
        assert action.approval is not None
        assert action.approval.proposal is not None
        proposal = action.approval.proposal

        outcome = approval.approve(
            proposal.approval_id,
            proposal.plan_digest,
        )
        final = completion.complete(proposal.approval_id, outcome)

        self.assertEqual(reader.calls, 1)
        self.assertIsNotNone(final)
        assert final is not None
        self.assertIn("ตรวจข้อมูลสดจาก GitHub", final.reply)
        self.assertIn("Stars: 12,345", final.reply)
        self.assertIn("License: Apache-2.0", final.reply)
        self.assertIn(REFERENCE, final.reply)
        self.assertEqual(
            conversations.assistant_messages[-1],
            final.reply,
        )

    def test_deactivation_after_proposal_blocks_connector_call(self):
        (
            reader,
            _,
            activation,
            approval,
            _,
            _,
            bridge,
            completion,
        ) = self.compose()
        action = bridge.process(
            message=f"GitHub repository {REFERENCE} metadata"
        )
        assert action.approval is not None
        assert action.approval.proposal is not None
        proposal = action.approval.proposal
        activation.deactivate(
            "github_public_repo",
            "1.0.0",
            "repository_metadata",
        )

        outcome = approval.approve(
            proposal.approval_id,
            proposal.plan_digest,
        )
        final = completion.complete(proposal.approval_id, outcome)

        self.assertEqual(reader.calls, 0)
        self.assertIsNotNone(final)
        assert final is not None
        self.assertIn("ไม่สามารถ", final.reply)

    def test_governance_revocation_after_proposal_blocks_connector_call(self):
        (
            reader,
            governance,
            _,
            approval,
            _,
            _,
            bridge,
            completion,
        ) = self.compose()
        action = bridge.process(
            message=f"GitHub repo {REFERENCE} stars"
        )
        assert action.approval is not None
        assert action.approval.proposal is not None
        proposal = action.approval.proposal
        governance.revoke("github_public_repo", "1.0.0")

        outcome = approval.approve(
            proposal.approval_id,
            proposal.plan_digest,
        )
        final = completion.complete(proposal.approval_id, outcome)

        self.assertEqual(reader.calls, 0)
        self.assertIsNotNone(final)
        assert final is not None
        self.assertIn("ไม่สามารถ", final.reply)

    def test_plugin_output_is_composed_deterministically_without_ai(self):
        (
            _,
            _,
            _,
            approval,
            _,
            _,
            bridge,
            completion,
        ) = self.compose()
        action = bridge.process(
            message=f"GitHub repo {REFERENCE} language"
        )
        assert action.approval is not None
        assert action.approval.proposal is not None
        proposal = action.approval.proposal
        outcome = approval.approve(
            proposal.approval_id,
            proposal.plan_digest,
        )
        final = completion.complete(proposal.approval_id, outcome)
        assert final is not None

        self.assertIn("Language: Python", final.reply)
        self.assertNotIn("{", final.reply)
        self.assertNotIn('"stargazers_count"', final.reply)


if __name__ == "__main__":
    unittest.main()
