"""D181 owner-approved governed execution binding and decision gate."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from threading import RLock
from uuid import UUID

from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep
from app.contracts.execution_approval import ExecutionApprovalDecisionOutcome
from app.contracts.explicit_action_cognitive_handoff import ExplicitActionCognitiveHandoffOutcome
from app.contracts.explicit_action_live_chat_routing import ExplicitActionLiveChatProjectionOutcome
from app.contracts.explicit_action_semantic_runtime import ExplicitActionSemanticRuntimeOutcome
from app.contracts.governed_action import ActionIntent, GovernedActionPreparation
from app.contracts.governed_action_runtime import GovernedActionRuntimeOutcome
from app.contracts.owner_approved_governed_execution import CognitiveExecutionBinding
from app.contracts.structured_action_candidate_runtime import StructuredActionCandidateRuntimeOutcome
from app.contracts.structured_action_proposal_runtime import StructuredActionProposalRuntimeOutcome
from app.contracts.structured_action_semantic_runtime import StructuredActionSemanticRuntimeOutcome
from app.contracts.workspace import WorkspaceScope
from app.services.execution_approval_service import ExecutionApprovalService
from app.services.execution_guard import execution_plan_digest
from app.services.governed_action import governed_action_intent_digest
from app.services.governed_execution_outcome_feedback import (
    GovernedExecutionOutcomeFeedbackRecorder,
)

DEFAULT_MAX_COGNITIVE_EXECUTION_BINDINGS = 100


class OwnerApprovedGovernedExecutionError(RuntimeError):
    reason_code = "cognitive_execution_binding_invalid"


class CognitiveExecutionBindingInvalidError(OwnerApprovedGovernedExecutionError):
    reason_code = "cognitive_execution_binding_invalid"


class CognitiveExecutionBindingConflictError(OwnerApprovedGovernedExecutionError):
    reason_code = "cognitive_execution_binding_conflict"


class CognitiveExecutionWorkspaceMismatchError(OwnerApprovedGovernedExecutionError):
    reason_code = "cognitive_execution_workspace_mismatch"


class CognitiveExecutionLineageMismatchError(OwnerApprovedGovernedExecutionError):
    reason_code = "cognitive_execution_lineage_mismatch"


class CognitiveExecutionApprovalMismatchError(OwnerApprovedGovernedExecutionError):
    reason_code = "cognitive_execution_approval_mismatch"


class CognitiveExecutionRiskNotPermittedError(OwnerApprovedGovernedExecutionError):
    reason_code = "cognitive_execution_risk_not_permitted"


class CognitiveExecutionBindingStoreFullError(OwnerApprovedGovernedExecutionError):
    reason_code = "cognitive_execution_binding_store_full"


def _canonical(value: object) -> object:
    if isinstance(value, Mapping):
        return tuple((key, _canonical(item)) for key, item in sorted(value.items()))
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(_canonical(item) for item in value)
    return value


class CognitiveExecutionBindingStore:
    """Bounded process-local sidecar binding store with no silent eviction."""

    def __init__(self, *, max_bindings: int = DEFAULT_MAX_COGNITIVE_EXECUTION_BINDINGS) -> None:
        if isinstance(max_bindings, bool) or not isinstance(max_bindings, int) or max_bindings < 1:
            raise ValueError("max_bindings must be a positive integer.")
        self._max_bindings = max_bindings
        self._items: dict[str, CognitiveExecutionBinding] = {}
        self._lock = RLock()

    @property
    def binding_count(self) -> int:
        with self._lock:
            return len(self._items)

    def register(self, binding: CognitiveExecutionBinding) -> CognitiveExecutionBinding:
        if not isinstance(binding, CognitiveExecutionBinding):
            raise CognitiveExecutionBindingInvalidError("The cognitive execution binding is invalid.")
        with self._lock:
            existing = self._items.get(binding.approval_id)
            if existing is not None:
                if existing == binding:
                    return existing
                raise CognitiveExecutionBindingConflictError(
                    "The approval already has a different cognitive binding."
                )
            if len(self._items) >= self._max_bindings:
                raise CognitiveExecutionBindingStoreFullError(
                    "Cognitive execution binding capacity is full."
                )
            self._items[binding.approval_id] = binding
            return binding

    def get(self, approval_id: str) -> CognitiveExecutionBinding | None:
        with self._lock:
            return self._items.get(approval_id)

    def discard(self, approval_id: str) -> None:
        with self._lock:
            self._items.pop(approval_id, None)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


class OwnerApprovedGovernedExecutionService:
    """Validate cognitive lineage, then delegate to frozen D45 authority."""

    def __init__(
        self,
        *,
        binding_store: CognitiveExecutionBindingStore,
        approval_service: ExecutionApprovalService,
        workspace_scope: WorkspaceScope | None,
        outcome_feedback_recorder: GovernedExecutionOutcomeFeedbackRecorder | None = None,
    ) -> None:
        if not isinstance(binding_store, CognitiveExecutionBindingStore):
            raise TypeError("binding_store must be a CognitiveExecutionBindingStore.")
        if not isinstance(approval_service, ExecutionApprovalService):
            raise TypeError("approval_service must be an ExecutionApprovalService.")
        if workspace_scope is not None and not isinstance(workspace_scope, WorkspaceScope):
            raise TypeError("workspace_scope must be a WorkspaceScope or None.")
        self._store = binding_store
        self._approval_service = approval_service
        self._workspace_id = (
            workspace_scope.workspace_id
            if workspace_scope is not None
            else None
        )
        self._outcome_feedback_recorder = outcome_feedback_recorder

    def binding_for(self, approval_id: str) -> CognitiveExecutionBinding | None:
        return self._store.get(approval_id)

    def register_cognitive_projection(
        self,
        *,
        projection: ExplicitActionLiveChatProjectionOutcome,
        command: CommandRequest,
        conversation_id: UUID,
    ) -> CognitiveExecutionBinding:
        binding = self._binding_from_projection(
            projection=projection,
            command=command,
            conversation_id=conversation_id,
        )
        return self._store.register(binding)

    def approve(self, approval_id: str, plan_digest: str) -> ExecutionApprovalDecisionOutcome:
        binding = self._store.get(approval_id)
        if binding is None:
            return self._approval_service.approve(approval_id, plan_digest)

        self._require_workspace(binding)
        if binding.risk_class != "R0" or binding.effect not in {"none", "read"}:
            raise CognitiveExecutionRiskNotPermittedError(
                "This cognitive execution risk is not permitted in D181 V1."
            )

        try:
            outcome = self._approval_service.approve(approval_id, plan_digest)
            self._try_record_outcome_feedback(binding, outcome)
            return outcome
        finally:
            self._store.discard(approval_id)

    def deny(self, approval_id: str, plan_digest: str) -> ExecutionApprovalDecisionOutcome:
        binding = self._store.get(approval_id)
        if binding is None:
            return self._approval_service.deny(approval_id, plan_digest)

        self._require_workspace(binding)
        try:
            outcome = self._approval_service.deny(approval_id, plan_digest)
            self._try_record_outcome_feedback(binding, outcome)
            return outcome
        finally:
            self._store.discard(approval_id)

    def _try_record_outcome_feedback(
        self,
        binding: CognitiveExecutionBinding,
        outcome: ExecutionApprovalDecisionOutcome,
    ) -> None:
        recorder = self._outcome_feedback_recorder
        if recorder is None:
            return
        try:
            recorder.try_record(binding, outcome)
        except Exception:
            # D182 is post-authority observation and cannot alter D45/D40 outcome.
            return

    def _require_workspace(self, binding: CognitiveExecutionBinding) -> None:
        if (
            self._workspace_id is None
            or binding.workspace_id is not self._workspace_id
        ):
            raise CognitiveExecutionWorkspaceMismatchError(
                "The cognitive execution binding belongs to another workspace."
            )

    def _binding_from_projection(
        self,
        *,
        projection: ExplicitActionLiveChatProjectionOutcome,
        command: CommandRequest,
        conversation_id: UUID,
    ) -> CognitiveExecutionBinding:
        if not isinstance(projection, ExplicitActionLiveChatProjectionOutcome):
            raise CognitiveExecutionBindingInvalidError("The D180 projection is invalid.")
        if not isinstance(command, CommandRequest):
            raise CognitiveExecutionBindingInvalidError("The cognitive command is invalid.")
        if not isinstance(conversation_id, UUID):
            raise CognitiveExecutionBindingInvalidError("The conversation identity is invalid.")
        if (
            projection.status != "pending_approval"
            or projection.approval is None
            or projection.approval.status != "pending"
            or projection.approval.proposal is None
        ):
            raise CognitiveExecutionBindingInvalidError(
                "Only one pending D180 approval may be bound."
            )

        handoff = projection.handoff
        if (
            not isinstance(handoff, ExplicitActionCognitiveHandoffOutcome)
            or handoff.status != "prepared_for_owner_review"
        ):
            raise CognitiveExecutionLineageMismatchError("The D179 lineage is not owner-reviewable.")

        d177 = handoff.runtime
        if (
            not isinstance(d177, ExplicitActionSemanticRuntimeOutcome)
            or d177.status != "prepared_for_owner_review"
        ):
            raise CognitiveExecutionLineageMismatchError("The D177 lineage is invalid.")
        d175 = d177.runtime
        if (
            not isinstance(d175, StructuredActionSemanticRuntimeOutcome)
            or d175.status != "prepared_for_owner_review"
            or d175.lineage.status != "semantic_ready"
            or d175.lineage.semantic is None
        ):
            raise CognitiveExecutionLineageMismatchError("The D175 lineage is invalid.")
        d173 = d175.runtime
        if (
            not isinstance(d173, StructuredActionCandidateRuntimeOutcome)
            or d173.status != "prepared_for_owner_review"
        ):
            raise CognitiveExecutionLineageMismatchError("The D173 lineage is invalid.")
        d170 = d173.runtime
        if (
            not isinstance(d170, StructuredActionProposalRuntimeOutcome)
            or d170.status != "prepared_for_owner_review"
            or d170.conversion is None
            or d170.conversion.status != "converted_for_lineage_validation"
            or not isinstance(d170.conversion.action_intent, ActionIntent)
        ):
            raise CognitiveExecutionLineageMismatchError("The D170 lineage is invalid.")
        d167 = d170.runtime
        if (
            not isinstance(d167, GovernedActionRuntimeOutcome)
            or d167.status != "prepared_for_owner_review"
            or not isinstance(d167.preparation, GovernedActionPreparation)
            or d167.preparation.status != "pending_approval"
            or d167.preparation.risk is None
        ):
            raise CognitiveExecutionLineageMismatchError("The D167 lineage is invalid.")

        intent = d170.conversion.action_intent
        semantic = d175.lineage.semantic
        preparation = d167.preparation
        approval = projection.approval
        proposal = approval.proposal
        assert proposal is not None

        if (
            command.command != "chat.message"
            or intent.source_turn_id != command.request_id
            or semantic.source_turn_id != intent.source_turn_id
            or semantic.source_artifact_digest != intent.source_artifact_digest
        ):
            raise CognitiveExecutionLineageMismatchError(
                "The cognitive source lineage does not match."
            )

        expected_intent_digest = governed_action_intent_digest(intent)
        if preparation.intent_digest != expected_intent_digest:
            raise CognitiveExecutionLineageMismatchError(
                "The governed action intent digest does not match."
            )

        risk = preparation.risk
        if (
            risk.capability_id != preparation.capability_id
            or risk.effect != preparation.effect
            or approval.request_id != proposal.request_id
            or approval.target_kind != proposal.target_kind
            or proposal.target_kind != intent.target_kind
            or proposal.adapter_id != intent.adapter_id
            or proposal.operation != intent.operation
            or _canonical(proposal.parameters) != _canonical(intent.parameters)
            or proposal.capability_id != preparation.capability_id
            or proposal.effect != preparation.effect
            or proposal.data_class != preparation.data_class
            or proposal.owner_approval_required is not True
        ):
            raise CognitiveExecutionApprovalMismatchError(
                "The D45 proposal does not match governed cognitive intent."
            )

        reviewed_plan = ExecutionPlan(
            request_id=proposal.request_id,
            adapter_id=proposal.adapter_id,
            steps=(ExecutionStep(1, proposal.operation, proposal.parameters),),
            owner_approval_required=proposal.owner_approval_required,
        )
        try:
            digest = execution_plan_digest(reviewed_plan)
        except (TypeError, ValueError) as error:
            raise CognitiveExecutionApprovalMismatchError(
                "The reviewed execution plan is invalid."
            ) from error
        if digest != proposal.plan_digest:
            raise CognitiveExecutionApprovalMismatchError(
                "The reviewed plan digest does not match."
            )

        workspace_id = self._workspace_id
        if workspace_id is None:
            raise CognitiveExecutionWorkspaceMismatchError(
                "An exact workspace is required for cognitive execution binding."
            )

        return CognitiveExecutionBinding(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            source_turn_id=intent.source_turn_id,
            source_artifact_digest=intent.source_artifact_digest,
            intent_digest=preparation.intent_digest,
            approval_id=proposal.approval_id,
            execution_request_id=proposal.request_id,
            plan_digest=proposal.plan_digest,
            target_kind=proposal.target_kind,
            capability_id=proposal.capability_id,
            adapter_id=proposal.adapter_id,
            operation=proposal.operation,
            effect=proposal.effect,
            risk_class=risk.risk_class,
            expires_at=proposal.expires_at,
        )


__all__ = [
    "CognitiveExecutionApprovalMismatchError",
    "CognitiveExecutionBindingConflictError",
    "CognitiveExecutionBindingInvalidError",
    "CognitiveExecutionBindingStore",
    "CognitiveExecutionBindingStoreFullError",
    "CognitiveExecutionLineageMismatchError",
    "CognitiveExecutionRiskNotPermittedError",
    "CognitiveExecutionWorkspaceMismatchError",
    "OwnerApprovedGovernedExecutionError",
    "OwnerApprovedGovernedExecutionService",
]
