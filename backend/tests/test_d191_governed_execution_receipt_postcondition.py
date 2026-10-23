from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.contracts.command import ExecutionPlan, ExecutionStep, Result
from app.contracts.execution_approval import ExecutionApprovalDecisionOutcome
from app.contracts.execution_authorization import ExecutionAuthorization
from app.contracts.execution_integration import ExecutionIntegrationOutcome
from app.contracts.execution_planning import ExecutionPlanningOutcome
from app.contracts.governed_execution_receipt_postcondition import (
    D191_CONTRACT_VERSION,
    D191_RECEIPT_POLICY,
    D191_REFERENCE_BASELINE,
)
from app.contracts.owner_approved_governed_execution import CognitiveExecutionBinding
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.services.execution_guard import execution_plan_digest
from app.services.governed_execution_receipt_postcondition import (
    GovernedExecutionReceiptPostconditionProjector,
)

NOW = datetime(2026, 10, 23, tzinfo=timezone.utc)
CONVERSATION = UUID("19119119-1111-4111-8111-191191191911")


def digest(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def plan(*, adapter_id: str = "tool.read", operation: str = "inspect") -> ExecutionPlan:
    return ExecutionPlan(
        request_id="request-d191",
        adapter_id=adapter_id,
        steps=(ExecutionStep(sequence=1, operation=operation, parameters={"value": 1}),),
        owner_approval_required=True,
    )


def binding(
    source_plan: ExecutionPlan | None = None,
    *,
    workspace: WorkspaceId = WorkspaceId.PERSONAL,
    intent_digest: str | None = None,
    adapter_id: str = "tool.read",
    operation: str = "inspect",
) -> CognitiveExecutionBinding:
    source_plan = source_plan or plan(adapter_id=adapter_id, operation=operation)
    return CognitiveExecutionBinding(
        workspace_id=workspace,
        conversation_id=CONVERSATION,
        source_turn_id="d191-turn",
        source_artifact_digest=digest("artifact"),
        intent_digest=intent_digest or digest("intent"),
        approval_id="approval-d191",
        execution_request_id="request-d191",
        plan_digest=execution_plan_digest(source_plan),
        target_kind="tool",
        capability_id="exec.test.read",
        adapter_id=adapter_id,
        operation=operation,
        effect="read",
        risk_class="R0",
        expires_at=NOW,
    )


def planned(source_plan: ExecutionPlan) -> ExecutionPlanningOutcome:
    return ExecutionPlanningOutcome(
        request_id="request-d191",
        status="planned",
        target_kind="tool",
        plan=source_plan,
        reason_code="execution_planned",
    )


def authorization(
    source_plan: ExecutionPlan,
    *,
    status: str = "authorized",
) -> ExecutionAuthorization:
    digest_value = execution_plan_digest(source_plan)
    execution_plan = None
    if status == "authorized":
        execution_plan = ExecutionPlan(
            request_id=source_plan.request_id,
            adapter_id=source_plan.adapter_id,
            steps=source_plan.steps,
            owner_approval_required=False,
        )
    return ExecutionAuthorization(
        request_id="request-d191",
        status=status,
        target_kind="tool",
        source_plan_digest=digest_value,
        execution_plan=execution_plan,
        reason_code={
            "authorized": "owner_approval_verified",
            "blocked": "owner_approval_denied",
            "rejected": "authorization_policy_violation",
        }[status],
    )


def outcome(
    *,
    execution_status: str = "completed",
    result_status: str = "succeeded",
    owner_decision: str = "approved",
    authorization_status: str | None = "authorized",
    output: dict[str, object] | None = None,
    error: str | None = None,
    reason_code: str | None = None,
):
    source_plan = plan()
    source_binding = binding(source_plan)

    if execution_status in {"completed", "blocked"} or authorization_status is not None:
        planning = planned(source_plan)
    elif execution_status == "unavailable":
        planning = ExecutionPlanningOutcome(
            request_id="request-d191",
            status="unavailable",
            target_kind=None,
            plan=None,
            reason_code="planner_unavailable",
        )
    else:
        planning = ExecutionPlanningOutcome(
            request_id="request-d191",
            status="rejected",
            target_kind=None,
            plan=None,
            reason_code="command_not_supported",
        )

    auth = (
        None
        if authorization_status is None
        else authorization(source_plan, status=authorization_status)
    )
    result = (
        Result(
            request_id="request-d191",
            status=result_status,
            output={} if output is None else output,
            error=error,
        )
        if execution_status == "completed"
        else None
    )
    execution = ExecutionIntegrationOutcome(
        request_id="request-d191",
        status=execution_status,
        target_kind="tool" if planning.status == "planned" else None,
        planning=planning,
        authorization=auth,
        result=result,
        reason_code=reason_code or {
            "completed": "execution_completed",
            "blocked": "owner_approval_denied",
            "rejected": "command_not_supported",
            "unavailable": "planner_unavailable",
        }[execution_status],
    )
    decision = ExecutionApprovalDecisionOutcome(
        approval_id="approval-d191",
        decision=owner_decision,
        execution=execution,
    )
    return source_binding, decision


def projector(workspace: WorkspaceId = WorkspaceId.PERSONAL):
    return GovernedExecutionReceiptPostconditionProjector(
        workspace_scope=WorkspaceScope(workspace)
    )


def test_d191_contract_constants_are_exact():
    assert D191_REFERENCE_BASELINE == "88f5326d0017898aaa21514a52ae2203f283b065"
    assert D191_CONTRACT_VERSION == "o-ai.execution-receipt-postcondition.v1"
    assert D191_RECEIPT_POLICY == "d181_d45_d40_factual_execution_receipt_v1"


@pytest.mark.parametrize("result_status", ("succeeded", "failed", "blocked"))
def test_d191_completed_results_are_recorded_but_postcondition_unverified(result_status):
    source_binding, decision = outcome(result_status=result_status)
    receipt = projector().project(binding=source_binding, decision_outcome=decision)
    assert receipt.receipt_status == "recorded"
    assert receipt.owner_decision == "approved"
    assert receipt.execution_status == "completed"
    assert receipt.authorization_status == "authorized"
    assert receipt.result_status == result_status
    assert receipt.postcondition_status == "unverified"
    assert receipt.postcondition_reason_code == "result_is_not_postcondition_evidence"


def test_d191_owner_denied_blocked_is_recorded_not_applicable():
    source_binding, decision = outcome(
        execution_status="blocked",
        owner_decision="denied",
        authorization_status="blocked",
    )
    receipt = projector().project(binding=source_binding, decision_outcome=decision)
    assert receipt.receipt_status == "recorded"
    assert receipt.owner_decision == "denied"
    assert receipt.execution_status == "blocked"
    assert receipt.authorization_status == "blocked"
    assert receipt.result_status is None
    assert receipt.postcondition_status == "not_applicable"


@pytest.mark.parametrize(
    ("execution_status", "authorization_status"),
    (
        ("blocked", "blocked"),
        ("rejected", None),
        ("unavailable", None),
    ),
)
def test_d191_noncompleted_execution_is_recorded_not_applicable(
    execution_status,
    authorization_status,
):
    source_binding, decision = outcome(
        execution_status=execution_status,
        authorization_status=authorization_status,
    )
    receipt = projector().project(binding=source_binding, decision_outcome=decision)
    assert receipt.receipt_status == "recorded"
    assert receipt.execution_status == execution_status
    assert receipt.result_status is None
    assert receipt.postcondition_status == "not_applicable"
    assert receipt.postcondition_reason_code == "execution_not_completed"


def test_d191_exact_factual_projection_comes_from_frozen_lineage():
    source_binding, decision = outcome()
    receipt = projector().project(binding=source_binding, decision_outcome=decision)
    assert receipt.source_intent_digest == source_binding.intent_digest
    assert receipt.approval_id == source_binding.approval_id
    assert receipt.execution_request_id == source_binding.execution_request_id
    assert receipt.plan_digest == source_binding.plan_digest
    assert receipt.target_kind == source_binding.target_kind
    assert receipt.capability_id == source_binding.capability_id
    assert receipt.adapter_id == source_binding.adapter_id
    assert receipt.operation == source_binding.operation
    assert receipt.effect == source_binding.effect
    assert receipt.risk_class == source_binding.risk_class
    assert receipt.execution_reason_code == decision.execution.reason_code


def test_d191_result_payload_claim_cannot_verify_postcondition():
    source_binding, decision = outcome(
        result_status="succeeded",
        output={
            "success": True,
            "verified": True,
            "postcondition_verified": True,
        },
        error=None,
    )
    receipt = projector().project(binding=source_binding, decision_outcome=decision)
    assert receipt.receipt_status == "recorded"
    assert receipt.result_status == "succeeded"
    assert receipt.postcondition_status == "unverified"


@pytest.mark.parametrize(
    "mutation",
    (
        "workspace",
        "approval",
        "request",
        "plan_digest",
        "adapter",
        "operation",
        "authorization_request",
        "authorization_target",
        "authorization_plan",
        "result_request",
    ),
)
def test_d191_lineage_mismatch_collapses_to_canonical_invalid_evidence(mutation):
    source_binding, decision = outcome()
    execution = decision.execution
    if mutation == "workspace":
        object.__setattr__(source_binding, "workspace_id", WorkspaceId.COMPANY)
    elif mutation == "approval":
        object.__setattr__(source_binding, "approval_id", "other-approval")
    elif mutation == "request":
        object.__setattr__(source_binding, "execution_request_id", "other-request")
    elif mutation == "plan_digest":
        object.__setattr__(source_binding, "plan_digest", "0" * 64)
    elif mutation == "adapter":
        object.__setattr__(source_binding, "adapter_id", "other-adapter")
    elif mutation == "operation":
        object.__setattr__(source_binding, "operation", "other-operation")
    elif mutation == "authorization_request":
        object.__setattr__(execution.authorization, "request_id", "other-request")
    elif mutation == "authorization_target":
        object.__setattr__(execution.authorization, "target_kind", "module")
    elif mutation == "authorization_plan":
        object.__setattr__(execution.authorization, "source_plan_digest", "0" * 64)
    elif mutation == "result_request":
        object.__setattr__(execution.result, "request_id", "other-request")

    receipt = projector().project(binding=source_binding, decision_outcome=decision)
    assert receipt.receipt_status == "invalid_evidence"
    assert receipt.reason_code == "execution_receipt_invalid_evidence"
    assert receipt.workspace_id is WorkspaceId.PERSONAL
    assert receipt.source_intent_digest is None
    assert receipt.approval_id is None
    assert receipt.execution_request_id is None
    assert receipt.plan_digest is None
    assert receipt.execution_status is None
    assert receipt.postcondition_status is None


def test_d191_wrong_source_types_are_canonical_invalid_evidence():
    receipt = projector(WorkspaceId.COMPANY).project(
        binding={"approval_id": "attacker"},
        decision_outcome={"execution": "attacker"},
    )
    assert receipt.receipt_status == "invalid_evidence"
    assert receipt.workspace_id is WorkspaceId.COMPANY
    assert receipt.approval_id is None
    assert "attacker" not in repr(receipt)


def test_d191_denied_completed_execution_is_invalid_evidence():
    source_binding, decision = outcome(owner_decision="denied")
    receipt = projector().project(binding=source_binding, decision_outcome=decision)
    assert receipt.receipt_status == "invalid_evidence"
