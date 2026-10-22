from __future__ import annotations

from app.api.v1.execution_approvals import approve_execution, deny_execution
from app.contracts.workspace import WorkspaceScope
from app.schemas.execution_approvals import ExecutionApprovalDecisionRequest
from app.services.governed_execution_outcome_feedback import (
    GovernedExecutionOutcomeFeedbackRecorder,
    GovernedExecutionOutcomeFeedbackStore,
)
from app.services.owner_approved_governed_execution import (
    CognitiveExecutionBindingStore,
    OwnerApprovedGovernedExecutionService,
)
from tests.test_d181_owner_approved_governed_execution import binding_from, build_d45, proposal


class NoopCompletion:
    def complete(self, approval_id, outcome):
        return None


def service_with_bound_approval():
    d45, read, _ = build_d45()
    reviewed = proposal(d45)
    binding = binding_from(reviewed)
    bindings = CognitiveExecutionBindingStore()
    bindings.register(binding)
    feedback = GovernedExecutionOutcomeFeedbackStore()
    service = OwnerApprovedGovernedExecutionService(
        binding_store=bindings,
        approval_service=d45,
        workspace_scope=WorkspaceScope(binding.workspace_id),
        outcome_feedback_recorder=GovernedExecutionOutcomeFeedbackRecorder(store=feedback),
    )
    return service, feedback, reviewed, read


def test_d182_approve_api_response_remains_existing_d45_shape():
    service, feedback, reviewed, read = service_with_bound_approval()
    response = approve_execution(
        approval_id=reviewed.approval_id,
        payload=ExecutionApprovalDecisionRequest(plan_digest=reviewed.plan_digest),
        _=None,
        decision_service=service,
        completion_service=NoopCompletion(),  # type: ignore[arg-type]
    )
    assert response.success is True
    assert response.data.approval_id == reviewed.approval_id
    assert response.data.decision == "approved"
    assert response.data.status == "completed"
    assert response.data.result is not None
    assert response.data.result.status == "succeeded"
    assert read.calls == 1
    assert feedback.get(reviewed.approval_id) is not None


def test_d182_deny_api_response_remains_existing_d45_shape():
    service, feedback, reviewed, read = service_with_bound_approval()
    response = deny_execution(
        approval_id=reviewed.approval_id,
        payload=ExecutionApprovalDecisionRequest(plan_digest=reviewed.plan_digest),
        _=None,
        decision_service=service,
        completion_service=NoopCompletion(),  # type: ignore[arg-type]
    )
    assert response.success is True
    assert response.data.approval_id == reviewed.approval_id
    assert response.data.decision == "denied"
    assert response.data.status == "blocked"
    assert response.data.result is None
    assert read.calls == 0
    item = feedback.get(reviewed.approval_id)
    assert item is not None
    assert item.classification == "owner_denied"


def test_d182_feedback_failure_cannot_change_api_response():
    class ExplodingRecorder:
        def try_record(self, binding, decision):
            raise RuntimeError("private feedback failure")

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
    response = approve_execution(
        approval_id=reviewed.approval_id,
        payload=ExecutionApprovalDecisionRequest(plan_digest=reviewed.plan_digest),
        _=None,
        decision_service=service,
        completion_service=NoopCompletion(),  # type: ignore[arg-type]
    )
    assert response.success is True
    assert response.data.status == "completed"
    assert read.calls == 1
