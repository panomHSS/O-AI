from __future__ import annotations

from app.api.v1.execution_approvals import approve_execution, deny_execution
from app.contracts.workspace import WorkspaceScope
from app.schemas.execution_approvals import ExecutionApprovalDecisionRequest
from app.services.governed_execution_experience_runtime import (
    GovernedExecutionExperienceRuntimeIntegration,
    GovernedExecutionExperienceRuntimeStore,
)
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


class NoopCompletion:
    def complete(self, approval_id, outcome):
        return None


def service_with_d185():
    d45, read, _ = build_d45()
    reviewed = proposal(d45)
    binding = binding_from(reviewed)
    bindings = CognitiveExecutionBindingStore()
    bindings.register(binding)

    feedback = GovernedExecutionOutcomeFeedbackStore()
    runtime = GovernedExecutionExperienceRuntimeStore()
    integration = GovernedExecutionExperienceRuntimeIntegration(
        feedback_store=feedback,
        runtime_store=runtime,
    )
    service = OwnerApprovedGovernedExecutionService(
        binding_store=bindings,
        approval_service=d45,
        workspace_scope=WorkspaceScope(binding.workspace_id),
        outcome_feedback_recorder=GovernedExecutionOutcomeFeedbackRecorder(
            store=feedback
        ),
        experience_runtime_integration=integration,
    )
    return service, feedback, runtime, reviewed, read


def test_d185_approve_api_shape_is_unchanged_and_runtime_evidence_exists():
    service, feedback, runtime, reviewed, read = service_with_d185()
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

    outcome = runtime.get(reviewed.approval_id)
    assert outcome is not None
    assert outcome.runtime_status == "review_eligible"
    assert outcome.review is not None
    assert outcome.review.eligibility == "eligible_for_owner_review"


def test_d185_deny_api_shape_is_unchanged_and_owner_decline_is_ineligible():
    service, feedback, runtime, reviewed, read = service_with_d185()
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
    assert feedback.get(reviewed.approval_id) is not None

    outcome = runtime.get(reviewed.approval_id)
    assert outcome is not None
    assert outcome.runtime_status == "review_ineligible"
    assert outcome.review is not None
    assert outcome.review.eligibility == "ineligible"
    assert outcome.review.reason_code == "owner_declined"


class ExplodingIntegration:
    def try_integrate(self, approval_id):
        raise RuntimeError("private d185 runtime failure")


def service_with_exploding_d185():
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
        outcome_feedback_recorder=GovernedExecutionOutcomeFeedbackRecorder(
            store=feedback
        ),
        experience_runtime_integration=ExplodingIntegration(),  # type: ignore[arg-type]
    )
    return service, feedback, reviewed, read


def test_d185_failure_cannot_change_approve_api_response():
    service, feedback, reviewed, read = service_with_exploding_d185()
    response = approve_execution(
        approval_id=reviewed.approval_id,
        payload=ExecutionApprovalDecisionRequest(plan_digest=reviewed.plan_digest),
        _=None,
        decision_service=service,
        completion_service=NoopCompletion(),  # type: ignore[arg-type]
    )
    assert response.success is True
    assert response.data.decision == "approved"
    assert response.data.status == "completed"
    assert response.data.result is not None
    assert response.data.result.status == "succeeded"
    assert read.calls == 1
    assert feedback.get(reviewed.approval_id) is not None


def test_d185_failure_cannot_change_deny_api_response():
    service, feedback, reviewed, read = service_with_exploding_d185()
    response = deny_execution(
        approval_id=reviewed.approval_id,
        payload=ExecutionApprovalDecisionRequest(plan_digest=reviewed.plan_digest),
        _=None,
        decision_service=service,
        completion_service=NoopCompletion(),  # type: ignore[arg-type]
    )
    assert response.success is True
    assert response.data.decision == "denied"
    assert response.data.status == "blocked"
    assert response.data.result is None
    assert read.calls == 0
    assert feedback.get(reviewed.approval_id) is not None
