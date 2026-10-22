from __future__ import annotations

from uuid import UUID

import pytest

from app.contracts.capability_permission import ExecutableCapabilityPermission
from app.contracts.command import CommandRequest, ExecutionPlan, Result
from app.contracts.execution_approval import ExecutionApprovalProposalOutcome
from app.contracts.explicit_action_cognitive_handoff import ExplicitActionCognitiveHandoffOutcome
from app.contracts.explicit_action_live_chat_routing import ExplicitActionLiveChatProjectionOutcome
from app.contracts.explicit_action_semantic_runtime import ExplicitActionSemanticRuntimeOutcome
from app.contracts.governed_action import ActionIntent, GovernedActionPreparation, RiskClassification
from app.contracts.governed_action_intent_conversion import GovernedActionIntentConversionOutcome
from app.contracts.governed_action_runtime import GovernedActionRuntimeOutcome
from app.contracts.owner_approved_governed_execution import (
    CognitiveExecutionBinding,
    D181_OWNER_APPROVED_GOVERNED_EXECUTION_CONTRACT_VERSION,
)
from app.contracts.structured_action_candidate_producer import StructuredActionSemanticInput
from app.contracts.structured_action_candidate_runtime import StructuredActionCandidateRuntimeOutcome
from app.contracts.structured_action_proposal_runtime import StructuredActionProposalRuntimeOutcome
from app.contracts.structured_action_semantic_lineage import StructuredActionSemanticLineageOutcome
from app.contracts.structured_action_semantic_runtime import StructuredActionSemanticRuntimeOutcome
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.services.adapter_registry import AdapterRegistry
from app.services.capability_permission_policy import CapabilityPermissionPolicy
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.command_execution_coordinator import CommandExecutionCoordinator
from app.services.execution_approval_service import (
    ExecutionApprovalNotPendingError,
    ExecutionApprovalPlanMismatchError,
    ExecutionApprovalService,
    PendingExecutionApprovalStore,
)
from app.services.execution_guard import ExecutionGuard
from app.services.execution_planner import ExecutionPlanner
from app.services.governed_action import governed_action_intent_digest
from app.services.module_runtime import ModuleRuntime
from app.services.owner_approved_governed_execution import (
    CognitiveExecutionBindingConflictError,
    CognitiveExecutionBindingStore,
    CognitiveExecutionBindingStoreFullError,
    CognitiveExecutionLineageMismatchError,
    CognitiveExecutionRiskNotPermittedError,
    CognitiveExecutionWorkspaceMismatchError,
    OwnerApprovedGovernedExecutionService,
)
from app.services.tool_runtime import ToolRuntime


CONVERSATION_ID = UUID("18118118-1111-4111-8111-181181181811")
TURN = "d181-turn"
ARTIFACT = "a" * 64


class StubTool:
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION

    def __init__(self, adapter_id: str) -> None:
        self.adapter_id = adapter_id
        self.tool_name = adapter_id
        self.calls = 0

    def execute(self, request: CommandRequest, plan: ExecutionPlan) -> Result:
        self.calls += 1
        return Result(
            request_id=request.request_id,
            status="succeeded",
            output={"operation": plan.steps[0].operation},
        )


def build_d45(workspace: WorkspaceId = WorkspaceId.PERSONAL):
    read = StubTool("tool.read")
    external = StubTool("tool.external")
    registry = AdapterRegistry((read, external))
    policy = CapabilityPermissionPolicy(
        registry=registry,
        permissions=(
            ExecutableCapabilityPermission(
                "exec.test.read", "tool", "tool.read", "inspect",
                "read", "workspace_metadata", True,
            ),
            ExecutableCapabilityPermission(
                "exec.test.external", "tool", "tool.external", "send",
                "external_side_effect", "external_data", True,
            ),
        ),
    )
    planner = ExecutionPlanner(
        registry=registry,
        decision_engine=CommandDecisionEngine(),
        ai_router=object(),  # type: ignore[arg-type]
        ai_discovery=object(),  # type: ignore[arg-type]
        permission_policy=policy,
    )
    guard = ExecutionGuard(registry=registry, permission_policy=policy)
    coordinator = CommandExecutionCoordinator(
        planner=planner,
        guard=guard,
        tool_runtime=ToolRuntime(registry=registry),
        module_runtime=ModuleRuntime(registry=registry),
    )
    store = PendingExecutionApprovalStore()
    counter = {"value": 0}

    def request_id() -> str:
        counter["value"] += 1
        return f"d181-execution-{counter['value']}"

    d45 = ExecutionApprovalService(
        planner=planner,
        permission_policy=policy,
        coordinator=coordinator,
        store=store,
        workspace_scope=WorkspaceScope(workspace),
        request_id_factory=request_id,
    )
    return d45, read, external


def proposal(d45: ExecutionApprovalService, *, external: bool = False):
    return d45.propose(
        target_kind="tool",
        adapter_id="tool.external" if external else "tool.read",
        operation="send" if external else "inspect",
        parameters={},
    ).proposal


def binding_from(reviewed, *, workspace=WorkspaceId.PERSONAL, risk="R0"):
    assert reviewed is not None
    return CognitiveExecutionBinding(
        workspace_id=workspace,
        conversation_id=CONVERSATION_ID,
        source_turn_id=TURN,
        source_artifact_digest=ARTIFACT,
        intent_digest="b" * 64,
        approval_id=reviewed.approval_id,
        execution_request_id=reviewed.request_id,
        plan_digest=reviewed.plan_digest,
        target_kind=reviewed.target_kind,
        capability_id=reviewed.capability_id,
        adapter_id=reviewed.adapter_id,
        operation=reviewed.operation,
        effect=reviewed.effect,
        risk_class=risk,
        expires_at=reviewed.expires_at,
    )


def wrapper(d45, store=None, *, workspace=WorkspaceId.PERSONAL):
    return OwnerApprovedGovernedExecutionService(
        binding_store=store or CognitiveExecutionBindingStore(),
        approval_service=d45,
        workspace_scope=WorkspaceScope(workspace),
    )


def forged(cls, **values):
    value = object.__new__(cls)
    for name, item in values.items():
        object.__setattr__(value, name, item)
    return value


def cognitive_projection(approval: ExecutionApprovalProposalOutcome, *, semantic_artifact=ARTIFACT):
    reviewed = approval.proposal
    assert reviewed is not None
    intent = ActionIntent(
        source_turn_id=TURN,
        source_artifact_digest=ARTIFACT,
        target_kind=reviewed.target_kind,
        adapter_id=reviewed.adapter_id,
        operation=reviewed.operation,
        parameters=reviewed.parameters,
    )
    risk = RiskClassification(
        capability_id=reviewed.capability_id,
        effect=reviewed.effect,
        risk_class="R0",
        reversible=False,
        reason_code="read_or_no_side_effect",
    )
    preparation = GovernedActionPreparation(
        intent_digest=governed_action_intent_digest(intent),
        status="pending_approval",
        reason_code="owner_decision_required",
        capability_id=reviewed.capability_id,
        effect=reviewed.effect,
        data_class=reviewed.data_class,
        risk=risk,
        confirmation_required=True,
        approval=approval,
    )
    d167 = GovernedActionRuntimeOutcome(
        status="prepared_for_owner_review",
        reason_code="owner_decision_required",
        intent_digest=preparation.intent_digest,
        preparation=preparation,
    )
    conversion = GovernedActionIntentConversionOutcome(
        status="converted_for_lineage_validation",
        reason_code="proposal_converted_for_lineage_validation",
        action_intent=intent,
    )
    d170 = StructuredActionProposalRuntimeOutcome(
        status="prepared_for_owner_review",
        reason_code="owner_decision_required",
        conversion=conversion,
        runtime=d167,
    )
    d173 = forged(
        StructuredActionCandidateRuntimeOutcome,
        status="prepared_for_owner_review",
        reason_code="owner_decision_required",
        runtime=d170,
    )
    semantic = StructuredActionSemanticInput(
        source_turn_id=TURN,
        source_artifact_digest=semantic_artifact,
        semantic_action="system_info",
        parameters={},
    )
    lineage = StructuredActionSemanticLineageOutcome(
        status="semantic_ready",
        reason_code="structured_action_semantic_ready",
        semantic=semantic,
    )
    d175 = StructuredActionSemanticRuntimeOutcome(
        status="prepared_for_owner_review",
        reason_code="owner_decision_required",
        lineage=lineage,
        runtime=d173,
    )
    d177 = forged(
        ExplicitActionSemanticRuntimeOutcome,
        status="prepared_for_owner_review",
        reason_code="owner_decision_required",
        runtime=d175,
    )
    handoff = ExplicitActionCognitiveHandoffOutcome(
        status="prepared_for_owner_review",
        reason_code="owner_decision_required",
        runtime=d177,
    )
    return ExplicitActionLiveChatProjectionOutcome(
        status="pending_approval",
        reason_code="owner_decision_required",
        approval=approval,
        handoff=handoff,
    )


def test_d181_contract_version_and_r0_semantics():
    d45, _, _ = build_d45()
    value = binding_from(proposal(d45))
    assert value.contract_version == D181_OWNER_APPROVED_GOVERNED_EXECUTION_CONTRACT_VERSION
    assert value.risk_class == "R0"
    assert value.effect == "read"


def test_d181_store_duplicate_is_idempotent_and_conflict_fails():
    d45, _, _ = build_d45()
    first = binding_from(proposal(d45))
    store = CognitiveExecutionBindingStore()
    assert store.register(first) is first
    assert store.register(first) is first
    conflict = CognitiveExecutionBinding(
        workspace_id=first.workspace_id,
        conversation_id=UUID("18118118-2222-4222-8222-181181181822"),
        source_turn_id=first.source_turn_id,
        source_artifact_digest=first.source_artifact_digest,
        intent_digest=first.intent_digest,
        approval_id=first.approval_id,
        execution_request_id=first.execution_request_id,
        plan_digest=first.plan_digest,
        target_kind=first.target_kind,
        capability_id=first.capability_id,
        adapter_id=first.adapter_id,
        operation=first.operation,
        effect=first.effect,
        risk_class=first.risk_class,
        expires_at=first.expires_at,
    )
    with pytest.raises(CognitiveExecutionBindingConflictError):
        store.register(conflict)


def test_d181_store_is_bounded_without_eviction():
    d45, _, _ = build_d45()
    first = binding_from(proposal(d45))
    second = binding_from(proposal(d45))
    store = CognitiveExecutionBindingStore(max_bindings=1)
    store.register(first)
    with pytest.raises(CognitiveExecutionBindingStoreFullError):
        store.register(second)
    assert store.get(first.approval_id) is first


def test_d181_r0_approve_delegates_exact_d45_once_and_replay_fails():
    d45, read, _ = build_d45()
    reviewed = proposal(d45)
    store = CognitiveExecutionBindingStore()
    store.register(binding_from(reviewed))
    service = wrapper(d45, store)
    result = service.approve(reviewed.approval_id, reviewed.plan_digest)
    assert result.execution.status == "completed"
    assert read.calls == 1
    assert store.get(reviewed.approval_id) is None
    with pytest.raises(ExecutionApprovalNotPendingError):
        service.approve(reviewed.approval_id, reviewed.plan_digest)
    assert read.calls == 1


def test_d181_deny_consumes_bound_ticket_without_execution():
    d45, read, _ = build_d45()
    reviewed = proposal(d45)
    store = CognitiveExecutionBindingStore()
    store.register(binding_from(reviewed))
    result = wrapper(d45, store).deny(reviewed.approval_id, reviewed.plan_digest)
    assert result.execution.status == "blocked"
    assert result.execution.reason_code == "owner_approval_denied"
    assert read.calls == 0
    assert store.get(reviewed.approval_id) is None


def test_d181_unbound_legacy_approval_preserves_d45_behavior():
    d45, read, _ = build_d45()
    reviewed = proposal(d45)
    result = wrapper(d45).approve(reviewed.approval_id, reviewed.plan_digest)
    assert result.execution.status == "completed"
    assert read.calls == 1


def test_d181_non_r0_approve_is_blocked_but_deny_remains_available():
    d45, _, external = build_d45()
    reviewed = proposal(d45, external=True)
    store = CognitiveExecutionBindingStore()
    store.register(binding_from(reviewed, risk="R2"))
    service = wrapper(d45, store)
    with pytest.raises(CognitiveExecutionRiskNotPermittedError):
        service.approve(reviewed.approval_id, reviewed.plan_digest)
    assert external.calls == 0
    assert store.get(reviewed.approval_id) is not None
    denied = service.deny(reviewed.approval_id, reviewed.plan_digest)
    assert denied.execution.status == "blocked"
    assert external.calls == 0


def test_d181_workspace_mismatch_stops_before_d45():
    d45, read, _ = build_d45()
    reviewed = proposal(d45)
    store = CognitiveExecutionBindingStore()
    store.register(binding_from(reviewed, workspace=WorkspaceId.PERSONAL))
    service = wrapper(d45, store, workspace=WorkspaceId.COMPANY)
    with pytest.raises(CognitiveExecutionWorkspaceMismatchError):
        service.approve(reviewed.approval_id, reviewed.plan_digest)
    assert read.calls == 0
    assert store.get(reviewed.approval_id) is not None


def test_d181_digest_mismatch_preserves_d45_invalidation_semantics():
    d45, read, _ = build_d45()
    reviewed = proposal(d45)
    store = CognitiveExecutionBindingStore()
    store.register(binding_from(reviewed))
    service = wrapper(d45, store)
    wrong = "0" * 64
    if wrong == reviewed.plan_digest:
        wrong = "f" * 64
    with pytest.raises(ExecutionApprovalPlanMismatchError):
        service.approve(reviewed.approval_id, wrong)
    assert read.calls == 0
    assert store.get(reviewed.approval_id) is None
    with pytest.raises(ExecutionApprovalNotPendingError):
        service.approve(reviewed.approval_id, reviewed.plan_digest)


def test_d181_registers_exact_cognitive_lineage_and_approval_identity():
    d45, _, _ = build_d45()
    outcome = d45.propose(
        target_kind="tool", adapter_id="tool.read", operation="inspect", parameters={}
    )
    service = wrapper(d45)
    command = CommandRequest(request_id=TURN, command="chat.message")
    binding = service.register_cognitive_projection(
        projection=cognitive_projection(outcome),
        command=command,
        conversation_id=CONVERSATION_ID,
    )
    reviewed = outcome.proposal
    assert reviewed is not None
    assert binding.approval_id == reviewed.approval_id
    assert binding.execution_request_id == reviewed.request_id
    assert binding.plan_digest == reviewed.plan_digest
    assert binding.source_turn_id == TURN
    assert binding.source_artifact_digest == ARTIFACT
    assert binding.risk_class == "R0"


def test_d181_rejects_mutated_cognitive_artifact_lineage():
    d45, _, _ = build_d45()
    outcome = d45.propose(
        target_kind="tool", adapter_id="tool.read", operation="inspect", parameters={}
    )
    with pytest.raises(CognitiveExecutionLineageMismatchError):
        wrapper(d45).register_cognitive_projection(
            projection=cognitive_projection(outcome, semantic_artifact="c" * 64),
            command=CommandRequest(request_id=TURN, command="chat.message"),
            conversation_id=CONVERSATION_ID,
        )
