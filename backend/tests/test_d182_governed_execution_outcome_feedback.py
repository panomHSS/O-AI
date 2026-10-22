from __future__ import annotations

from dataclasses import replace

from app.contracts.command import ExecutionPlan, Result
from app.contracts.execution_approval import ExecutionApprovalDecisionOutcome
from app.contracts.execution_authorization import ExecutionAuthorization
from app.contracts.execution_integration import ExecutionIntegrationOutcome
from app.contracts.execution_planning import ExecutionPlanningOutcome
from app.contracts.governed_execution_outcome_feedback import (
    D182_GOVERNED_EXECUTION_OUTCOME_FEEDBACK_CONTRACT_VERSION,
)
from app.contracts.workspace import WorkspaceScope
from app.services.governed_execution_outcome_feedback import (
    GovernedExecutionOutcomeFeedbackRecorder,
    GovernedExecutionOutcomeFeedbackStore,
)
from app.services.owner_approved_governed_execution import (
    CognitiveExecutionBindingStore,
    OwnerApprovedGovernedExecutionService,
)
from tests.test_d181_owner_approved_governed_execution import (
    binding_from,
    build_d45,
    proposal,
)

DIGEST = "d" * 64


def recorder():
    store = GovernedExecutionOutcomeFeedbackStore()
    return GovernedExecutionOutcomeFeedbackRecorder(store=store), store


def outcome(
    *,
    approval_id: str = "approval-d182",
    request_id: str = "request-d182",
    decision: str = "approved",
    execution_status: str = "completed",
    result_status: str | None = "succeeded",
    reason_code: str = "execution_completed",
    output=None,
    error=None,
):
    if execution_status in {"completed", "blocked"}:
        plan = ExecutionPlan(
            request_id=request_id,
            adapter_id="tool.read",
            steps=(),
            owner_approval_required=True,
        )
        planning = ExecutionPlanningOutcome(
            request_id=request_id,
            status="planned",
            target_kind="tool",
            plan=plan,
            reason_code="execution_planned",
        )
    else:
        planning = ExecutionPlanningOutcome(
            request_id=request_id,
            status="unavailable" if execution_status == "unavailable" else "rejected",
            target_kind=None,
            plan=None,
            reason_code=reason_code,
        )

    authorization = None
    result = None
    target_kind = None
    if execution_status == "completed":
        target_kind = "tool"
        authorized_plan = ExecutionPlan(
            request_id=request_id,
            adapter_id="tool.read",
            steps=(),
            owner_approval_required=False,
        )
        authorization = ExecutionAuthorization(
            request_id=request_id,
            status="authorized",
            target_kind="tool",
            source_plan_digest=DIGEST,
            execution_plan=authorized_plan,
            reason_code="authorized",
        )
        result = Result(
            request_id=request_id,
            status=result_status,
            output=output or {},
            error=error,
        )
    elif execution_status == "blocked":
        target_kind = "tool"
        authorization = ExecutionAuthorization(
            request_id=request_id,
            status="blocked",
            target_kind="tool",
            source_plan_digest=DIGEST,
            execution_plan=None,
            reason_code=reason_code,
        )

    execution = ExecutionIntegrationOutcome(
        request_id=request_id,
        status=execution_status,
        target_kind=target_kind,
        planning=planning,
        authorization=authorization,
        result=result,
        reason_code=reason_code,
    )
    return ExecutionApprovalDecisionOutcome(
        approval_id=approval_id,
        decision=decision,
        execution=execution,
    )


def binding_for(decision):
    d45, _, _ = build_d45()
    reviewed = proposal(d45)
    return replace(
        binding_from(reviewed),
        approval_id=decision.approval_id,
        execution_request_id=decision.execution.request_id,
        plan_digest=DIGEST,
    )


def service_for(d45, binding_store, feedback_store, binding):
    return OwnerApprovedGovernedExecutionService(
        binding_store=binding_store,
        approval_service=d45,
        workspace_scope=WorkspaceScope(binding.workspace_id),
        outcome_feedback_recorder=GovernedExecutionOutcomeFeedbackRecorder(
            store=feedback_store
        ),
    )


def test_d182_contract_version_and_authority_ceiling():
    decision = outcome()
    binding = binding_for(decision)
    rec, store = recorder()
    assert rec.try_record(binding, decision)
    feedback = store.get(decision.approval_id)
    assert feedback is not None
    assert feedback.contract_version == D182_GOVERNED_EXECUTION_OUTCOME_FEEDBACK_CONTRACT_VERSION
    for name in (
        "approval_authority", "authorization_authority", "execution_authority",
        "retry_authority", "rollback_authority", "learning_authority",
        "memory_write_authority", "routing_authority", "model_selection_authority",
        "policy_authority",
    ):
        assert getattr(feedback, name) is False


def test_d182_classification_matrix():
    cases = (
        ("approved", "completed", "succeeded", "execution_succeeded"),
        ("approved", "completed", "failed", "execution_failed"),
        ("approved", "completed", "blocked", "execution_blocked"),
        ("approved", "blocked", None, "execution_blocked"),
        ("approved", "rejected", None, "execution_rejected"),
        ("approved", "unavailable", None, "execution_unavailable"),
        ("denied", "blocked", None, "owner_denied"),
    )
    for index, (decision_value, status, result_status, expected) in enumerate(cases):
        decision = outcome(
            approval_id=f"approval-{index}",
            request_id=f"request-{index}",
            decision=decision_value,
            execution_status=status,
            result_status=result_status,
            reason_code="owner_approval_denied" if decision_value == "denied" else f"reason-{index}",
        )
        binding = binding_for(decision)
        rec, store = recorder()
        assert rec.try_record(binding, decision)
        feedback = store.get(decision.approval_id)
        assert feedback is not None
        assert feedback.classification == expected


def test_d182_raw_result_output_and_error_are_not_projected():
    secret_output = "PRIVATE_RESULT_OUTPUT_MUST_NOT_ESCAPE"
    secret_error = "PRIVATE_RESULT_ERROR_MUST_NOT_ESCAPE"
    decision = outcome(
        result_status="failed",
        output={"secret": secret_output},
        error=secret_error,
    )
    binding = binding_for(decision)
    rec, store = recorder()
    assert rec.try_record(binding, decision)
    feedback = store.get(decision.approval_id)
    assert feedback is not None
    rendered = repr(feedback)
    assert secret_output not in rendered
    assert secret_error not in rendered
    assert secret_output not in feedback.feedback_fingerprint
    assert secret_error not in feedback.feedback_fingerprint


def test_d182_identity_mismatches_fail_feedback_closed():
    decision = outcome()
    rec, store = recorder()
    bad_approval = replace(binding_for(decision), approval_id="different-approval")
    assert rec.try_record(bad_approval, decision) is False
    bad_request = replace(binding_for(decision), execution_request_id="different-request")
    assert rec.try_record(bad_request, decision) is False
    assert store.feedback_count == 0


def test_d182_store_duplicate_idempotent_conflict_and_capacity_fail_closed():
    decision = outcome()
    binding = binding_for(decision)
    rec, store = recorder()
    assert rec.try_record(binding, decision)
    first = store.get(decision.approval_id)
    assert rec.try_record(binding, decision)
    assert store.get(decision.approval_id) is first
    changed = outcome(
        approval_id=decision.approval_id,
        request_id=decision.execution.request_id,
        result_status="failed",
    )
    assert rec.try_record(binding, changed) is False
    assert store.get(decision.approval_id) is first

    limited = GovernedExecutionOutcomeFeedbackStore(max_items=1)
    limited_rec = GovernedExecutionOutcomeFeedbackRecorder(store=limited)
    one = outcome(approval_id="one", request_id="one-request")
    two = outcome(approval_id="two", request_id="two-request")
    assert limited_rec.try_record(binding_for(one), one)
    assert limited_rec.try_record(binding_for(two), two) is False
    assert limited.feedback_count == 1


def test_d182_bound_r0_approve_records_after_exact_single_execution():
    d45, read, _ = build_d45()
    reviewed = proposal(d45)
    binding = binding_from(reviewed)
    bindings = CognitiveExecutionBindingStore()
    bindings.register(binding)
    feedback = GovernedExecutionOutcomeFeedbackStore()
    service = service_for(d45, bindings, feedback, binding)
    result = service.approve(reviewed.approval_id, reviewed.plan_digest)
    assert result.execution.status == "completed"
    assert read.calls == 1
    item = feedback.get(reviewed.approval_id)
    assert item is not None
    assert item.classification == "execution_succeeded"
    assert bindings.get(reviewed.approval_id) is None


def test_d182_bound_owner_deny_records_without_dispatch():
    d45, read, _ = build_d45()
    reviewed = proposal(d45)
    binding = binding_from(reviewed)
    bindings = CognitiveExecutionBindingStore()
    bindings.register(binding)
    feedback = GovernedExecutionOutcomeFeedbackStore()
    result = service_for(d45, bindings, feedback, binding).deny(
        reviewed.approval_id,
        reviewed.plan_digest,
    )
    assert result.execution.status == "blocked"
    assert read.calls == 0
    item = feedback.get(reviewed.approval_id)
    assert item is not None
    assert item.classification == "owner_denied"


def test_d182_unbound_legacy_d45_records_no_feedback():
    d45, read, _ = build_d45()
    reviewed = proposal(d45)
    feedback = GovernedExecutionOutcomeFeedbackStore()
    service = OwnerApprovedGovernedExecutionService(
        binding_store=CognitiveExecutionBindingStore(),
        approval_service=d45,
        workspace_scope=None,
        outcome_feedback_recorder=GovernedExecutionOutcomeFeedbackRecorder(store=feedback),
    )
    result = service.approve(reviewed.approval_id, reviewed.plan_digest)
    assert result.execution.status == "completed"
    assert read.calls == 1
    assert feedback.feedback_count == 0


def test_d182_feedback_exception_cannot_change_authoritative_outcome():
    class ExplodingRecorder:
        def try_record(self, binding, decision):
            raise RuntimeError("feedback must be isolated")

    d45, read, _ = build_d45()
    reviewed = proposal(d45)
    binding = binding_from(reviewed)
    bindings = CognitiveExecutionBindingStore()
    bindings.register(binding)
    service = OwnerApprovedGovernedExecutionService(
        binding_store=bindings,
        approval_service=d45,
        workspace_scope=WorkspaceScope(binding.workspace_id),
        outcome_feedback_recorder=ExplodingRecorder(),  # type: ignore[arg-type]
    )
    result = service.approve(reviewed.approval_id, reviewed.plan_digest)
    assert result.execution.status == "completed"
    assert read.calls == 1
    assert bindings.get(reviewed.approval_id) is None
