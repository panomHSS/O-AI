from datetime import datetime, timezone

from app.contracts.capability_permission import ExecutableCapabilityPermission
from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope, CognitiveFailureCode, CognitiveOrgan,
    CognitiveOrganStatus, CognitiveTurnState,
)
from app.contracts.cognitive_executive import (
    D136_EXECUTIVE_ARTIFACT_TYPE, D136_EXECUTIVE_CONTRACT_VERSION,
    CognitiveExecutiveOutcome, CognitiveExecutiveTraceEvent,
)
from app.contracts.command import CommandRequest, ExecutionPlan, Result
from app.contracts.governed_action import ActionIntent
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.services.adapter_registry import AdapterRegistry
from app.services.capability_permission_policy import CapabilityPermissionPolicy
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.execution_approval_service import (
    ExecutionApprovalService, PendingExecutionApprovalStore,
)
from app.services.execution_planner import ExecutionPlanner
from app.services.governed_action import GovernedActionBoundary
from app.services.governed_action_runtime import GovernedActionRuntimeIntegration

TURN = "d167-turn"
DIGEST = "a" * 64


class StubTool:
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION
    adapter_id = "tool.read"
    tool_name = "tool.read"

    def execute(self, request: CommandRequest, plan: ExecutionPlan) -> Result:
        raise AssertionError("D167 must not execute")


def build_runtime(
    workspace: WorkspaceId = WorkspaceId.PERSONAL,
    approval_required: bool = True,
):
    registry = AdapterRegistry((StubTool(),))
    policy = CapabilityPermissionPolicy(
        registry=registry,
        permissions=(ExecutableCapabilityPermission(
            "exec.test.read", "tool", "tool.read", "inspect", "read",
            "workspace_metadata", approval_required,
        ),),
    )
    planner = ExecutionPlanner(
        registry=registry,
        decision_engine=CommandDecisionEngine(),
        ai_router=object(),  # type: ignore[arg-type]
        ai_discovery=object(),  # type: ignore[arg-type]
        permission_policy=policy,
    )
    store = PendingExecutionApprovalStore()
    approval = ExecutionApprovalService(
        planner=planner,
        permission_policy=policy,
        coordinator=object(),  # type: ignore[arg-type]
        store=store,
        workspace_scope=WorkspaceScope(workspace),
        request_id_factory=lambda: "d167-request",
    )
    runtime = GovernedActionRuntimeIntegration(
        boundary=GovernedActionBoundary(
            permission_policy=policy,
            approval_service=approval,
        ),
        workspace_scope=WorkspaceScope(workspace),
    )
    return runtime, store


def command(request_id: str = TURN, name: str = "chat.message"):
    return CommandRequest(request_id=request_id, command=name)


def action(
    turn: str = TURN,
    digest: str = DIGEST,
    operation: str = "inspect",
):
    return ActionIntent(
        source_turn_id=turn,
        source_artifact_digest=digest,
        target_kind="tool",
        adapter_id="tool.read",
        operation=operation,
        parameters={},
    )


def outcome(
    turn: str = TURN,
    workspace: WorkspaceId = WorkspaceId.PERSONAL,
    terminal: CognitiveTurnState = CognitiveTurnState.COMPLETED,
    digest: str | None = DIGEST,
    stage: str = "publication_accepted",
    state: CognitiveTurnState = CognitiveTurnState.FINALIZING,
    duplicate: bool = False,
):
    status = {
        CognitiveTurnState.COMPLETED: CognitiveOrganStatus.READY,
        CognitiveTurnState.INSUFFICIENT: CognitiveOrganStatus.INSUFFICIENT,
        CognitiveTurnState.FAILED: CognitiveOrganStatus.FAILED,
    }[terminal]
    failure = {
        CognitiveTurnState.COMPLETED: None,
        CognitiveTurnState.INSUFFICIENT: CognitiveFailureCode.INSUFFICIENT_EVIDENCE,
        CognitiveTurnState.FAILED: CognitiveFailureCode.CONTRACT_VIOLATION,
    }[terminal]
    disposition = (
        "eligible" if terminal is CognitiveTurnState.COMPLETED
        else "bounded_insufficiency_only"
        if terminal is CognitiveTurnState.INSUFFICIENT
        else None
    )
    trace = []
    if digest is not None:
        trace.append(CognitiveExecutiveTraceEvent(
            sequence=1, state=state, stage=stage,
            status=CognitiveOrganStatus.READY, artifact_digest=digest,
        ))
        if duplicate:
            trace.append(CognitiveExecutiveTraceEvent(
                sequence=2, state=CognitiveTurnState.FINALIZING,
                stage="publication_accepted",
                status=CognitiveOrganStatus.READY, artifact_digest=digest,
            ))
    else:
        trace.append(CognitiveExecutiveTraceEvent(
            sequence=1, state=terminal, stage="turn_terminal", status=status,
            reason_code=failure.value if failure else None,
        ))
    return CognitiveExecutiveOutcome(
        envelope=CognitiveArtifactEnvelope(
            turn_id=turn,
            artifact_type=D136_EXECUTIVE_ARTIFACT_TYPE,
            contract_version=D136_EXECUTIVE_CONTRACT_VERSION,
            producer_organ=CognitiveOrgan.COGNITIVE_EXECUTIVE,
            workspace_id=workspace,
            context_snapshot_digest="c" * 64,
            created_at=datetime.now(timezone.utc),
            status=status,
        ),
        terminal_state=terminal,
        failure_code=failure,
        revision_count=0,
        invocation_count=0,
        draft_generation_count=0,
        publication_disposition=disposition,  # type: ignore[arg-type]
        trace=tuple(trace),
        bindings=(),
    )


def test_d167_valid_lineage_reaches_owner_review_only():
    runtime, store = build_runtime()
    result = runtime.prepare(
        action(), command=command(), cognitive_outcome=outcome()
    )
    assert result.status == "prepared_for_owner_review"
    assert result.preparation is not None
    assert result.preparation.status == "pending_approval"
    assert store.pending_count == 1


def test_d167_no_intent_creates_nothing():
    runtime, store = build_runtime()
    result = runtime.prepare(
        None, command=command(), cognitive_outcome=outcome()
    )
    assert result.status == "no_action_intent"
    assert store.pending_count == 0


def test_d167_unknown_capability_fails_closed():
    runtime, store = build_runtime()
    result = runtime.prepare(
        action(operation="unknown"),
        command=command(),
        cognitive_outcome=outcome(),
    )
    assert result.status == "intent_rejected"
    assert result.reason_code == "capability_not_permitted"
    assert store.pending_count == 0


def test_d167_no_confirmation_does_not_auto_execute():
    runtime, store = build_runtime(approval_required=False)
    result = runtime.prepare(
        action(), command=command(), cognitive_outcome=outcome()
    )
    assert result.status == "intent_rejected"
    assert result.reason_code == "structured_confirmation_not_required"
    assert store.pending_count == 0
