"""D195 deterministic synthetic-only contract and evaluation tests."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.contracts.owner_approved_governed_execution import CognitiveExecutionBinding
from app.contracts.controlled_r1_write_authorization_assessment import (
    ControlledR1WriteAuthorizationAssessment as Assessment, REASONS, AUTHORITY_FIELDS,
)
from app.services.controlled_r1_write_authorization_assessment import (
    ControlledR1WriteAuthorizationEvaluator as Evaluator, _R1SnapshotQuery, _R1OwnerDecisionFact,
    _R1CapabilityFact, _R1TargetFact, _R1PriorUseFact, _R1CoherentSnapshot,
)

NOW = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)


def binding(workspace=WorkspaceId.PERSONAL):
    return CognitiveExecutionBinding(
        workspace_id=workspace, conversation_id=uuid4(), source_turn_id="turn-195",
        source_artifact_digest="a"*64, intent_digest="b"*64, approval_id="approved-195",
        execution_request_id="request-195", plan_digest="c"*64, target_kind="tool",
        capability_id="synthetic.internal.write", adapter_id="synthetic.adapter", operation="update",
        effect="write", risk_class="R1", expires_at=NOW + timedelta(hours=1),
    )


def snapshot(query):
    target_identity = dict(target_kind=query.target_kind, capability_id=query.capability_id,
                           adapter_id=query.adapter_id, operation=query.operation)
    return _R1CoherentSnapshot(
        query=query,
        owner=_R1OwnerDecisionFact(query.workspace_id, query.approval_id, query.execution_request_id,
                                   query.plan_digest, "approved", NOW + timedelta(hours=1), "active"),
        capability=_R1CapabilityFact(**target_identity, effective_effect="write", permission_state="allowed",
                                     policy_state="allowed", owner_approval_required=True,
                                     data_class="workspace_content"),
        target=_R1TargetFact(**target_identity, internal_scope=True, reversible=True,
                             target_support="supported", has_external_side_effect=False,
                             requires_process_execution=False, effective_risk_class="R1"),
        prior_use=_R1PriorUseFact("complete", "none_observed", query.approval_id,
                                  query.execution_request_id, query.plan_digest, query.workspace_id),
        evaluation_time=NOW, snapshot_revision="synthetic-v1", coherence_state="coherent",
    )


class Source:
    def __init__(self, transform=lambda x: x):
        self.transform = transform
    def retrieve(self, query):
        return self.transform(snapshot(query))


def assess(transform=lambda x: x, *, source=None, b=None):
    b = b or binding()
    return Evaluator(workspace_scope=WorkspaceScope(b.workspace_id),
                     evidence_source=source if source is not None else Source(transform)).evaluate(binding=b)


CASES = [
    (lambda s: s, "eligible_for_authorization_review", "r1_assessment_requirements_met"),
    (lambda s: replace(s, target=replace(s.target, has_external_side_effect=True)), "blocked", "r1_risk_out_of_scope"),
    (lambda s: replace(s, capability=replace(s.capability, permission_state="denied")), "blocked", "r1_permission_denied"),
    (lambda s: replace(s, capability=replace(s.capability, policy_state="blocked")), "blocked", "r1_policy_blocked"),
    (lambda s: replace(s, owner=replace(s.owner, expires_at=NOW)), "blocked", "r1_approval_expired_or_revoked"),
    (lambda s: replace(s, prior_use=replace(s.prior_use, observation="prior_use_observed")), "blocked", "r1_prior_use_observed"),
    (lambda s: replace(s, owner=replace(s.owner, decision="denied")), "rejected", "r1_owner_denied"),
    (lambda s: replace(s, owner=replace(s.owner, revocation_state="unknown")), "unavailable", "r1_evidence_unavailable"),
    (lambda s: replace(s, owner=replace(s.owner, plan_digest="0"*64)), "unavailable", "r1_evidence_invalid"),
    (lambda s: replace(s, coherence_state="conflicting"), "unavailable", "r1_evidence_conflict"),
]


@pytest.mark.parametrize("transform,status,reason", CASES)
def test_all_ten_frozen_pairs(transform, status, reason):
    result = assess(transform)
    assert (result.status, result.reason_code) == (status, reason)
    assert result.manual_review_required is (status != "eligible_for_authorization_review")
    assert all(getattr(result, n) is False for n in AUTHORITY_FIELDS)
    assert (result.assessment_fingerprint is not None) is (status == "eligible_for_authorization_review")


def test_exact_matrix():
    assert sum(map(len, REASONS.values())) == 10
    assert set(REASONS) == {"eligible_for_authorization_review", "blocked", "rejected", "unavailable"}


def test_owner_denial_precedence():
    out = assess(lambda s: replace(s, owner=replace(s.owner, decision="denied"),
                                   capability=replace(s.capability, permission_state="denied")))
    assert out.reason_code == "r1_owner_denied"


def test_permission_before_policy():
    out = assess(lambda s: replace(s, capability=replace(s.capability, permission_state="denied", policy_state="blocked")))
    assert out.reason_code == "r1_permission_denied"


def test_snapshot_lack():
    class Empty:
        def retrieve(self, query):
            return None
    b = binding()
    result = Evaluator(workspace_scope=WorkspaceScope(b.workspace_id), evidence_source=Empty()).evaluate(binding=b)
    assert result.reason_code == "r1_evidence_unavailable"


def test_idempotent_public_evaluation():
    b = binding()
    evaluator = Evaluator(workspace_scope=WorkspaceScope(b.workspace_id), evidence_source=Source())
    a = evaluator.evaluate(binding=b)
    c = evaluator.evaluate(binding=b)
    assert a == c and a.assessment_fingerprint == c.assessment_fingerprint
    assert a.claim_consumed is False and a.atomic_write_guaranteed is False


def test_privacy_minimal_denial():
    result = assess(lambda s: replace(s, owner=replace(s.owner, decision="denied")))
    assert result.source_intent_digest is None and result.plan_digest is None
    assert result.assessment_fingerprint is None
