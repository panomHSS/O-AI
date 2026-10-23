"""D191 deterministic post-authority execution receipt projector."""

from __future__ import annotations

from app.contracts.command import ExecutionPlan, ExecutionStep, Result
from app.contracts.execution_approval import ExecutionApprovalDecisionOutcome
from app.contracts.execution_authorization import ExecutionAuthorization
from app.contracts.execution_integration import ExecutionIntegrationOutcome
from app.contracts.execution_planning import ExecutionPlanningOutcome
from app.contracts.governed_execution_receipt_postcondition import (
    GovernedExecutionReceiptPostcondition,
    compute_governed_execution_receipt_fingerprint,
)
from app.contracts.owner_approved_governed_execution import CognitiveExecutionBinding
from app.contracts.workspace import WorkspaceScope
from app.services.execution_guard import execution_plan_digest


class GovernedExecutionReceiptPostconditionProjector:
    """Project exact D181/D45/D40 facts without inferring postconditions."""

    def __init__(self, *, workspace_scope: WorkspaceScope) -> None:
        if type(workspace_scope) is not WorkspaceScope:
            raise TypeError("workspace_scope must be an exact WorkspaceScope.")
        workspace_scope.__post_init__()
        self._workspace_id = workspace_scope.workspace_id

    def project(
        self,
        *,
        binding: object,
        decision_outcome: object,
    ) -> GovernedExecutionReceiptPostcondition:
        try:
            return self._project_recorded(
                binding=binding,
                decision_outcome=decision_outcome,
            )
        except Exception:
            return self._invalid()

    def _invalid(self) -> GovernedExecutionReceiptPostcondition:
        fingerprint = compute_governed_execution_receipt_fingerprint(
            receipt_status="invalid_evidence",
            reason_code="execution_receipt_invalid_evidence",
            workspace_id=self._workspace_id,
            source_intent_digest=None,
            approval_id=None,
            execution_request_id=None,
            plan_digest=None,
            target_kind=None,
            capability_id=None,
            adapter_id=None,
            operation=None,
            effect=None,
            risk_class=None,
            owner_decision=None,
            execution_status=None,
            authorization_status=None,
            result_status=None,
            execution_reason_code=None,
            postcondition_status=None,
            postcondition_reason_code=None,
        )
        return GovernedExecutionReceiptPostcondition(
            receipt_status="invalid_evidence",
            reason_code="execution_receipt_invalid_evidence",
            workspace_id=self._workspace_id,
            source_intent_digest=None,
            approval_id=None,
            execution_request_id=None,
            plan_digest=None,
            target_kind=None,
            capability_id=None,
            adapter_id=None,
            operation=None,
            effect=None,
            risk_class=None,
            owner_decision=None,
            execution_status=None,
            authorization_status=None,
            result_status=None,
            execution_reason_code=None,
            postcondition_status=None,
            postcondition_reason_code=None,
            receipt_fingerprint=fingerprint,
        )

    def _project_recorded(
        self,
        *,
        binding: object,
        decision_outcome: object,
    ) -> GovernedExecutionReceiptPostcondition:
        if type(binding) is not CognitiveExecutionBinding:
            raise TypeError("binding must be an exact CognitiveExecutionBinding.")
        if type(decision_outcome) is not ExecutionApprovalDecisionOutcome:
            raise TypeError(
                "decision_outcome must be an exact ExecutionApprovalDecisionOutcome."
            )

        binding.__post_init__()
        decision_outcome.__post_init__()

        execution = decision_outcome.execution
        if type(execution) is not ExecutionIntegrationOutcome:
            raise TypeError("execution must be an exact ExecutionIntegrationOutcome.")
        execution.__post_init__()

        planning = execution.planning
        if type(planning) is not ExecutionPlanningOutcome:
            raise TypeError("planning must be an exact ExecutionPlanningOutcome.")
        planning.__post_init__()

        if binding.workspace_id is not self._workspace_id:
            raise ValueError("execution_receipt_workspace_mismatch")
        if binding.approval_id != decision_outcome.approval_id:
            raise ValueError("execution_receipt_approval_mismatch")
        if binding.execution_request_id != execution.request_id:
            raise ValueError("execution_receipt_request_mismatch")
        if planning.request_id != binding.execution_request_id:
            raise ValueError("execution_receipt_planning_request_mismatch")

        if planning.status == "planned":
            plan = planning.plan
            if type(plan) is not ExecutionPlan:
                raise TypeError("planned execution requires an exact ExecutionPlan.")
            if planning.target_kind != binding.target_kind:
                raise ValueError("execution_receipt_target_mismatch")
            if plan.request_id != binding.execution_request_id:
                raise ValueError("execution_receipt_plan_request_mismatch")
            if plan.adapter_id != binding.adapter_id:
                raise ValueError("execution_receipt_adapter_mismatch")
            if len(plan.steps) != 1:
                raise ValueError("execution_receipt_step_count_invalid")
            step = plan.steps[0]
            if type(step) is not ExecutionStep or step.sequence != 1:
                raise ValueError("execution_receipt_step_sequence_invalid")
            if step.operation != binding.operation:
                raise ValueError("execution_receipt_operation_mismatch")
            if execution_plan_digest(plan) != binding.plan_digest:
                raise ValueError("execution_receipt_plan_digest_mismatch")

        authorization = execution.authorization
        authorization_status = None
        if authorization is not None:
            if type(authorization) is not ExecutionAuthorization:
                raise TypeError(
                    "authorization must be an exact ExecutionAuthorization."
                )
            authorization.__post_init__()
            if authorization.request_id != binding.execution_request_id:
                raise ValueError("execution_receipt_authorization_request_mismatch")
            if authorization.target_kind != binding.target_kind:
                raise ValueError("execution_receipt_authorization_target_mismatch")
            if authorization.source_plan_digest != binding.plan_digest:
                raise ValueError("execution_receipt_authorization_plan_mismatch")
            authorization_status = authorization.status

        result = execution.result
        result_status = None
        if result is not None:
            if type(result) is not Result:
                raise TypeError("result must be an exact Result.")
            if result.request_id != binding.execution_request_id:
                raise ValueError("execution_receipt_result_request_mismatch")
            if result.status not in {"succeeded", "failed", "blocked"}:
                raise ValueError("execution_receipt_result_status_invalid")
            result_status = result.status

        if decision_outcome.decision == "denied":
            if execution.status == "completed" or authorization_status == "authorized":
                raise ValueError("execution_receipt_denied_execution_incoherent")

        if execution.status == "completed":
            postcondition_status = "unverified"
            postcondition_reason_code = "result_is_not_postcondition_evidence"
        else:
            postcondition_status = "not_applicable"
            postcondition_reason_code = "execution_not_completed"

        fingerprint = compute_governed_execution_receipt_fingerprint(
            receipt_status="recorded",
            reason_code="execution_receipt_recorded",
            workspace_id=self._workspace_id,
            source_intent_digest=binding.intent_digest,
            approval_id=binding.approval_id,
            execution_request_id=binding.execution_request_id,
            plan_digest=binding.plan_digest,
            target_kind=binding.target_kind,
            capability_id=binding.capability_id,
            adapter_id=binding.adapter_id,
            operation=binding.operation,
            effect=binding.effect,
            risk_class=binding.risk_class,
            owner_decision=decision_outcome.decision,
            execution_status=execution.status,
            authorization_status=authorization_status,
            result_status=result_status,
            execution_reason_code=execution.reason_code,
            postcondition_status=postcondition_status,
            postcondition_reason_code=postcondition_reason_code,
        )
        return GovernedExecutionReceiptPostcondition(
            receipt_status="recorded",
            reason_code="execution_receipt_recorded",
            workspace_id=self._workspace_id,
            source_intent_digest=binding.intent_digest,
            approval_id=binding.approval_id,
            execution_request_id=binding.execution_request_id,
            plan_digest=binding.plan_digest,
            target_kind=binding.target_kind,
            capability_id=binding.capability_id,
            adapter_id=binding.adapter_id,
            operation=binding.operation,
            effect=binding.effect,
            risk_class=binding.risk_class,
            owner_decision=decision_outcome.decision,
            execution_status=execution.status,
            authorization_status=authorization_status,
            result_status=result_status,
            execution_reason_code=execution.reason_code,
            postcondition_status=postcondition_status,
            postcondition_reason_code=postcondition_reason_code,
            receipt_fingerprint=fingerprint,
        )


__all__ = ["GovernedExecutionReceiptPostconditionProjector"]
