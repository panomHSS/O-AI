"""D195 standalone synthetic-only assessment; no production provider or write authority.

Exact dataclasses and source-returned facts are validation, NOT authentication.
Production provenance/coherence/freshness require separate acceptance and wiring.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, replace
from datetime import datetime, timezone

from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.contracts.owner_approved_governed_execution import CognitiveExecutionBinding
from app.contracts.controlled_r1_write_authorization_assessment import (
    ControlledR1WriteAuthorizationAssessment, CORRELATION_FIELDS, compute_assessment_fingerprint,
)


@dataclass(frozen=True, slots=True)
class _R1SnapshotQuery:
    workspace_id: WorkspaceId
    conversation_id: object
    source_turn_id: str
    source_artifact_digest: str
    intent_digest: str
    plan_digest: str
    approval_id: str
    execution_request_id: str
    target_kind: str
    capability_id: str
    adapter_id: str
    operation: str
    effect: str
    risk_class: str


@dataclass(frozen=True, slots=True)
class _R1OwnerDecisionFact:
    workspace_id: WorkspaceId
    approval_id: str
    execution_request_id: str
    plan_digest: str
    decision: str
    expires_at: datetime
    revocation_state: str


@dataclass(frozen=True, slots=True)
class _R1CapabilityFact:
    target_kind: str
    capability_id: str
    adapter_id: str
    operation: str
    effective_effect: str
    permission_state: str
    policy_state: str
    owner_approval_required: bool
    data_class: str


@dataclass(frozen=True, slots=True)
class _R1TargetFact:
    target_kind: str
    capability_id: str
    adapter_id: str
    operation: str
    internal_scope: bool
    reversible: bool
    target_support: str
    has_external_side_effect: bool
    requires_process_execution: bool
    effective_risk_class: str


@dataclass(frozen=True, slots=True)
class _R1PriorUseFact:
    coverage: str
    observation: str
    covered_approval_id: str
    covered_execution_request_id: str
    covered_plan_digest: str
    covered_workspace_id: WorkspaceId


@dataclass(frozen=True, slots=True)
class _R1CoherentSnapshot:
    query: _R1SnapshotQuery
    owner: _R1OwnerDecisionFact
    capability: _R1CapabilityFact
    target: _R1TargetFact
    prior_use: _R1PriorUseFact
    evaluation_time: datetime
    snapshot_revision: str
    coherence_state: str


def _aware(value: object) -> bool:
    return type(value) is datetime and value.tzinfo is not None and value.utcoffset() is not None


def _decision(snapshot: _R1CoherentSnapshot, query: _R1SnapshotQuery) -> tuple[str, str]:
    """Validate ALL facts before applying frozen substantive precedence."""
    if snapshot.query != query:
        raise ValueError("snapshot_query_mismatch")
    facts = ((snapshot.owner, _R1OwnerDecisionFact), (snapshot.capability, _R1CapabilityFact),
             (snapshot.target, _R1TargetFact), (snapshot.prior_use, _R1PriorUseFact))
    if any(type(obj) is not expected for obj, expected in facts):
        raise ValueError("snapshot_fact_type")
    if type(snapshot.snapshot_revision) is not str or not snapshot.snapshot_revision or len(snapshot.snapshot_revision.encode("utf-8")) > 128:
        raise ValueError("snapshot_revision_invalid")
    if not _aware(snapshot.evaluation_time) or not _aware(snapshot.owner.expires_at):
        raise ValueError("snapshot_time_invalid")
    owner, cap, target, prior = snapshot.owner, snapshot.capability, snapshot.target, snapshot.prior_use
    if (owner.workspace_id != query.workspace_id or owner.approval_id != query.approval_id
            or owner.execution_request_id != query.execution_request_id or owner.plan_digest != query.plan_digest
            or prior.covered_workspace_id != query.workspace_id or prior.covered_approval_id != query.approval_id
            or prior.covered_execution_request_id != query.execution_request_id or prior.covered_plan_digest != query.plan_digest):
        raise ValueError("snapshot_lineage_invalid")
    exact_target = (query.target_kind, query.capability_id, query.adapter_id, query.operation)
    if any((fact.target_kind, fact.capability_id, fact.adapter_id, fact.operation) != exact_target for fact in (cap, target)):
        raise ValueError("snapshot_target_identity_invalid")
    if (type(cap.owner_approval_required) is not bool or any(type(getattr(target, n)) is not bool for n in
             ("internal_scope", "reversible", "has_external_side_effect", "requires_process_execution"))):
        raise ValueError("snapshot_bool_invalid")
    if (owner.decision not in {"approved", "denied"} or owner.revocation_state not in {"active", "revoked", "unknown"}
            or cap.permission_state not in {"allowed", "denied", "unknown"}
            or cap.policy_state not in {"allowed", "blocked", "unknown"}
            or cap.effective_effect not in {"none", "read", "write", "external_side_effect", "process_execution"}
            or cap.data_class not in {"none", "system_metadata", "workspace_metadata", "workspace_content", "owner_data", "external_data"}
            or target.effective_risk_class not in {"R0", "R1", "R2", "R3"}
            or target.target_support not in {"supported", "unsupported", "unknown"}
            or prior.coverage not in {"complete", "incomplete", "unknown"}
            or prior.observation not in {"none_observed", "prior_use_observed", "conflict", "unknown"}
            or snapshot.coherence_state not in {"coherent", "unavailable", "invalid", "conflicting"}):
        raise ValueError("snapshot_enum_invalid")
    # A well-formed explicit conflict outranks unknown availability.
    if snapshot.coherence_state == "invalid":
        raise ValueError("snapshot_coherence_invalid")
    if snapshot.coherence_state == "conflicting" or prior.observation == "conflict":
        return "unavailable", "r1_evidence_conflict"
    if snapshot.coherence_state == "unavailable" or owner.revocation_state == "unknown" or cap.permission_state == "unknown" or cap.policy_state == "unknown" or target.target_support == "unknown" or prior.coverage != "complete" or prior.observation == "unknown":
        return "unavailable", "r1_evidence_unavailable"
    if (owner.decision == "denied"):
        return "rejected", "r1_owner_denied"
    if (query.risk_class != "R1" or query.effect != "write" or target.effective_risk_class != "R1"
            or cap.effective_effect != "write" or target.target_support != "supported"
            or not target.internal_scope or not target.reversible or target.has_external_side_effect
            or target.requires_process_execution or not cap.owner_approval_required):
        return "blocked", "r1_risk_out_of_scope"
    if cap.permission_state == "denied":
        return "blocked", "r1_permission_denied"
    if cap.policy_state == "blocked":
        return "blocked", "r1_policy_blocked"
    if owner.revocation_state == "revoked" or snapshot.evaluation_time.astimezone(timezone.utc) >= owner.expires_at.astimezone(timezone.utc):
        return "blocked", "r1_approval_expired_or_revoked"
    if prior.observation == "prior_use_observed":
        return "blocked", "r1_prior_use_observed"
    return "eligible_for_authorization_review", "r1_assessment_requirements_met"


class ControlledR1WriteAuthorizationEvaluator:
    """Pure read-only evaluator; source injection is not production trust certification."""

    def __init__(self, *, workspace_scope: WorkspaceScope, evidence_source: object) -> None:
        if type(workspace_scope) is not WorkspaceScope:
            raise TypeError("workspace_scope must be an exact WorkspaceScope")
        workspace_scope.__post_init__()
        self._workspace_id = workspace_scope.workspace_id
        self._source = evidence_source

    def evaluate(self, *, binding: object) -> ControlledR1WriteAuthorizationAssessment:
        try:
            if type(binding) is not CognitiveExecutionBinding:
                raise ValueError("r1_binding_type_invalid")
            binding.__post_init__()
            if binding.workspace_id != self._workspace_id:
                raise ValueError("r1_binding_workspace_invalid")
            stable = replace(binding)
            query = _R1SnapshotQuery(**{f.name: getattr(stable, f.name) for f in fields(_R1SnapshotQuery)})
            if self._source is None:
                return self._minimal("unavailable", "r1_evidence_unavailable")
            retrieve = getattr(self._source, "retrieve", None)
            if not callable(retrieve):
                raise ValueError("r1_source_invalid")
        except Exception:
            return self._minimal("unavailable", "r1_evidence_invalid")
        try:
            snapshot = retrieve(query)
        except Exception:
            return self._minimal("unavailable", "r1_evidence_unavailable")
        try:
            binding.__post_init__()
            if binding != stable:
                raise ValueError("r1_binding_changed")
            if snapshot is None:
                return self._minimal("unavailable", "r1_evidence_unavailable")
            if type(snapshot) is not _R1CoherentSnapshot:
                raise ValueError("r1_snapshot_type_invalid")
            status, reason = _decision(snapshot, query)
            if status != "eligible_for_authorization_review":
                return self._minimal(status, reason)
            values = dict(workspace_id=self._workspace_id, status=status, reason_code=reason,
                          manual_review_required=False,
                          source_intent_digest=stable.intent_digest, plan_digest=stable.plan_digest,
                          target_kind=stable.target_kind, capability_id=stable.capability_id,
                          adapter_id=stable.adapter_id, operation=stable.operation,
                          effect=stable.effect, risk_class=stable.risk_class)
            payload = {f.name: values.get(f.name, f.default)
                       for f in fields(ControlledR1WriteAuthorizationAssessment)
                       if f.name != "assessment_fingerprint"}
            payload["workspace_id"] = self._workspace_id.value
            return ControlledR1WriteAuthorizationAssessment(
                **values, assessment_fingerprint=compute_assessment_fingerprint(payload))
        except Exception:
            return self._minimal("unavailable", "r1_evidence_invalid")

    def _minimal(self, status: str, reason: str) -> ControlledR1WriteAuthorizationAssessment:
        return ControlledR1WriteAuthorizationAssessment(
            workspace_id=self._workspace_id, status=status, reason_code=reason,
            manual_review_required=True)
