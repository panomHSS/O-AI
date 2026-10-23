from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from app.contracts.execution_approval import (
    ExecutionApprovalProposal,
    ExecutionApprovalProposalOutcome,
)
from app.contracts.governed_action import (
    ActionIntent,
    GovernedActionPreparation,
    RiskClassification,
)
from app.contracts.governed_execution_experience_advisory_runtime_binding import (
    D190_BINDING_POLICY,
    D190_CONTRACT_VERSION,
    D190_REFERENCE_BASELINE,
)
from app.contracts.governed_execution_experience_retrieval import (
    TrustedExecutionExperienceEvidence,
    TrustedExecutionExperienceEvidenceSet,
    TrustedExecutionExperienceRetrievalQuery,
    compute_trusted_execution_experience_evidence_set_fingerprint,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.services.governed_action import governed_action_intent_digest
from app.services.trusted_execution_experience_advisory import (
    TrustedExecutionExperienceAdvisoryEvaluator,
)
from app.services.governed_execution_experience_advisory_runtime_binding import (
    GovernedExecutionExperienceAdvisoryRuntimeBinder,
)

NOW = datetime(2026, 10, 23, tzinfo=timezone.utc)


def digest(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def action(
    *,
    adapter_id: str = "tool.read",
    operation: str = "inspect",
    parameters: dict[str, object] | None = None,
) -> ActionIntent:
    return ActionIntent(
        source_turn_id="d190-turn",
        source_artifact_digest=digest("artifact"),
        target_kind="tool",
        adapter_id=adapter_id,
        operation=operation,
        parameters={} if parameters is None else parameters,
    )


def pending(
    intent: ActionIntent,
    *,
    capability_id: str = "exec.test.read",
    effect: str = "read",
    risk_class: str = "R0",
    reversible: bool = False,
    intent_digest: str | None = None,
) -> GovernedActionPreparation:
    intent_fp = (
        governed_action_intent_digest(intent)
        if intent_digest is None
        else intent_digest
    )
    risk = RiskClassification(
        capability_id=capability_id,
        effect=effect,
        risk_class=risk_class,
        reversible=reversible,
        reason_code={
            "R0": "read_or_no_side_effect",
            "R1": "explicit_reversible_write",
            "R2": "external_side_effect",
            "R3": (
                "process_execution"
                if effect == "process_execution"
                else "write_reversibility_not_established"
            ),
        }[risk_class],
    )
    proposal = ExecutionApprovalProposal(
        approval_id="approval-d190",
        request_id="request-d190",
        target_kind=intent.target_kind,
        adapter_id=intent.adapter_id,
        operation=intent.operation,
        parameters={},
        capability_id=capability_id,
        effect=effect,
        data_class="workspace_metadata",
        owner_approval_required=True,
        plan_digest=digest("plan"),
        expires_at=NOW + timedelta(minutes=5),
    )
    approval = ExecutionApprovalProposalOutcome(
        request_id="request-d190",
        status="pending",
        target_kind=intent.target_kind,
        reason_code="owner_decision_required",
        proposal=proposal,
    )
    return GovernedActionPreparation(
        intent_digest=intent_fp,
        status="pending_approval",
        reason_code="owner_decision_required",
        capability_id=capability_id,
        effect=effect,
        data_class="workspace_metadata",
        risk=risk,
        confirmation_required=True,
        approval=approval,
    )


def rejected(intent: ActionIntent) -> GovernedActionPreparation:
    return GovernedActionPreparation(
        intent_digest=governed_action_intent_digest(intent),
        status="rejected",
        reason_code="capability_not_permitted",
    )


def evidence(
    query: TrustedExecutionExperienceRetrievalQuery,
    number: int,
    tier: int,
    *,
    promotion_seed: str | None = None,
) -> TrustedExecutionExperienceEvidence:
    adapter_id, operation = {
        0: (query.adapter_id, query.operation),
        1: ("other-adapter", query.operation),
        2: (query.adapter_id, "other-operation"),
        3: ("other-adapter", "other-operation"),
    }[tier]
    return TrustedExecutionExperienceEvidence(
        trusted_execution_experience_id=UUID(int=number),
        promotion_fingerprint=digest(
            promotion_seed or f"promotion-{number}"
        ),
        target_kind=query.target_kind,
        capability_id=query.capability_id,
        adapter_id=adapter_id,
        operation=operation,
        effect=query.effect,
        risk_class=query.risk_class,
    )


def evidence_set(
    query: TrustedExecutionExperienceRetrievalQuery,
    tiers: tuple[int, ...] = (),
    *,
    truncated: bool = False,
    promotion_prefix: str = "promotion",
) -> TrustedExecutionExperienceEvidenceSet:
    items = tuple(
        evidence(
            query,
            number,
            tier,
            promotion_seed=f"{promotion_prefix}-{number}",
        )
        for number, tier in enumerate(tiers, start=1)
    )
    fingerprint = compute_trusted_execution_experience_evidence_set_fingerprint(
        query=query,
        evidence=items,
    )
    return TrustedExecutionExperienceEvidenceSet(
        workspace_id=query.workspace_id,
        query=query,
        evidence=items,
        selected_count=len(items),
        truncated=truncated,
        evidence_set_fingerprint=fingerprint,
    )


class RetrievalStub:
    def __init__(
        self,
        tiers: tuple[int, ...] = (),
        *,
        truncated: bool = False,
        factory=None,
        error: Exception | None = None,
    ) -> None:
        self.tiers = tiers
        self.truncated = truncated
        self.factory = factory
        self.error = error
        self.queries: list[TrustedExecutionExperienceRetrievalQuery] = []

    def retrieve(self, query):
        self.queries.append(query)
        if self.error is not None:
            raise self.error
        if self.factory is not None:
            return self.factory(query)
        return evidence_set(query, self.tiers, truncated=self.truncated)


def binder(
    retrieval,
    workspace: WorkspaceId = WorkspaceId.PERSONAL,
):
    return GovernedExecutionExperienceAdvisoryRuntimeBinder(
        retrieval_service=retrieval,
        workspace_scope=WorkspaceScope(workspace),
    )


def test_d190_contract_constants_are_exact():
    assert D190_REFERENCE_BASELINE == (
        "ed0174450726d64a268af54ce4e933963812dde3"
    )
    assert D190_CONTRACT_VERSION == (
        "o-ai.execution-experience-advisory-runtime-binding.v1"
    )
    assert D190_BINDING_POLICY == (
        "d188_retrieval_d189_advisory_current_action_binding_v1"
    )


def test_d190_empty_history_is_valid_bound_no_evidence():
    retrieval = RetrievalStub()
    intent = action()
    result = binder(retrieval).bind(
        intent=intent,
        preparation=pending(intent),
    )
    assert result.binding_status == "bound"
    assert result.reason_code == "execution_experience_advisory_bound"
    assert result.advisory_status == "no_evidence"
    assert result.best_relevance_tier is None
    assert result.mixed_relevance is False
    assert result.source_selected_count == 0
    assert result.source_truncated is False


@pytest.mark.parametrize(
    ("tier", "status"),
    (
        (0, "exact_match"),
        (1, "operation_match"),
        (2, "adapter_match"),
        (3, "capability_only"),
    ),
)
def test_d190_all_single_relevance_tiers_bind(
    tier: int,
    status: str,
):
    retrieval = RetrievalStub((tier, tier))
    intent = action()
    result = binder(retrieval).bind(
        intent=intent,
        preparation=pending(intent),
    )
    assert result.binding_status == "bound"
    assert result.advisory_status == status
    assert result.best_relevance_tier == tier
    assert result.mixed_relevance is False


def test_d190_mixed_relevance_binds_without_authority():
    retrieval = RetrievalStub((3, 1, 0))
    intent = action()
    result = binder(retrieval).bind(
        intent=intent,
        preparation=pending(intent),
    )
    assert result.binding_status == "bound"
    assert result.advisory_status == "mixed_relevance"
    assert result.best_relevance_tier == 0
    assert result.mixed_relevance is True


def test_d190_query_is_derived_only_from_current_governed_action():
    retrieval = RetrievalStub()
    intent = action(adapter_id="tool.alpha", operation="inspect")
    preparation = pending(
        intent,
        capability_id="capability.alpha",
        effect="none",
    )
    result = binder(retrieval, WorkspaceId.COMPANY).bind(
        intent=intent,
        preparation=preparation,
    )
    assert result.binding_status == "bound"
    assert len(retrieval.queries) == 1
    query = retrieval.queries[0]
    assert query.workspace_id is WorkspaceId.COMPANY
    assert query.target_kind == intent.target_kind
    assert query.capability_id == "capability.alpha"
    assert query.adapter_id == "tool.alpha"
    assert query.operation == "inspect"
    assert query.effect == "none"
    assert query.risk_class == "R0"


def test_d190_nonpending_preparation_is_not_applicable_and_does_not_retrieve():
    retrieval = RetrievalStub()
    intent = action()
    result = binder(retrieval).bind(
        intent=intent,
        preparation=rejected(intent),
    )
    assert result.binding_status == "not_applicable"
    assert result.advisory_status is None
    assert result.source_intent_digest == governed_action_intent_digest(intent)
    assert retrieval.queries == []


@pytest.mark.parametrize(
    ("effect", "risk_class", "reversible"),
    (
        ("write", "R1", True),
        ("external_side_effect", "R2", False),
        ("write", "R3", False),
        ("process_execution", "R3", False),
    ),
)
def test_d190_non_r0_effects_are_not_applicable(
    effect: str,
    risk_class: str,
    reversible: bool,
):
    retrieval = RetrievalStub()
    intent = action()
    result = binder(retrieval).bind(
        intent=intent,
        preparation=pending(
            intent,
            capability_id=f"capability.{risk_class.lower()}",
            effect=effect,
            risk_class=risk_class,
            reversible=reversible,
        ),
    )
    assert result.binding_status == "not_applicable"
    assert result.advisory_status is None
    assert retrieval.queries == []


def test_d190_intent_digest_mismatch_is_unavailable():
    retrieval = RetrievalStub()
    intent = action()
    result = binder(retrieval).bind(
        intent=intent,
        preparation=pending(intent, intent_digest="0" * 64),
    )
    assert result.binding_status == "unavailable"
    assert retrieval.queries == []


def test_d190_risk_capability_mismatch_is_unavailable():
    retrieval = RetrievalStub()
    intent = action()
    preparation = pending(intent)
    assert preparation.risk is not None
    object.__setattr__(
        preparation.risk,
        "capability_id",
        "different.capability",
    )
    result = binder(retrieval).bind(
        intent=intent,
        preparation=preparation,
    )
    assert result.binding_status == "unavailable"
    assert retrieval.queries == []


def test_d190_risk_effect_mismatch_is_unavailable():
    retrieval = RetrievalStub()
    intent = action()
    preparation = pending(intent)
    assert preparation.risk is not None
    object.__setattr__(preparation.risk, "effect", "none")
    result = binder(retrieval).bind(
        intent=intent,
        preparation=preparation,
    )
    assert result.binding_status == "unavailable"
    assert retrieval.queries == []


def test_d190_approval_semantic_mismatch_is_unavailable():
    retrieval = RetrievalStub()
    intent = action()
    preparation = pending(intent)
    assert preparation.approval is not None
    assert preparation.approval.proposal is not None
    object.__setattr__(
        preparation.approval.proposal,
        "adapter_id",
        "different-adapter",
    )
    result = binder(retrieval).bind(
        intent=intent,
        preparation=preparation,
    )
    assert result.binding_status == "unavailable"
    assert retrieval.queries == []


def test_d190_wrong_d188_return_type_is_unavailable():
    retrieval = RetrievalStub(factory=lambda _query: object())
    intent = action()
    result = binder(retrieval).bind(
        intent=intent,
        preparation=pending(intent),
    )
    assert result.binding_status == "unavailable"


def test_d190_tampered_d188_fingerprint_is_unavailable():
    def tampered(query):
        value = evidence_set(query, (0,))
        object.__setattr__(value, "evidence_set_fingerprint", "0" * 64)
        return value

    intent = action()
    result = binder(RetrievalStub(factory=tampered)).bind(
        intent=intent,
        preparation=pending(intent),
    )
    assert result.binding_status == "unavailable"


def test_d190_d188_query_mismatch_is_unavailable():
    def mismatched(query):
        other = TrustedExecutionExperienceRetrievalQuery(
            workspace_id=query.workspace_id,
            target_kind=query.target_kind,
            capability_id=query.capability_id,
            adapter_id="different-adapter",
            operation=query.operation,
            effect=query.effect,
            risk_class=query.risk_class,
        )
        return evidence_set(other)

    intent = action()
    result = binder(RetrievalStub(factory=mismatched)).bind(
        intent=intent,
        preparation=pending(intent),
    )
    assert result.binding_status == "unavailable"


def test_d190_retrieval_exception_collapses_to_unavailable():
    intent = action()
    result = binder(
        RetrievalStub(error=RuntimeError("private stack detail"))
    ).bind(
        intent=intent,
        preparation=pending(intent),
    )
    assert result.binding_status == "unavailable"
    assert result.advisory_status is None


def test_d190_invalid_d189_advisory_is_unavailable(monkeypatch):
    intent = action()
    invalid = TrustedExecutionExperienceAdvisoryEvaluator.evaluate(
        evidence_set=object()
    )

    monkeypatch.setattr(
        TrustedExecutionExperienceAdvisoryEvaluator,
        "evaluate",
        classmethod(lambda cls, *, evidence_set: invalid),
    )
    result = binder(RetrievalStub()).bind(
        intent=intent,
        preparation=pending(intent),
    )
    assert result.binding_status == "unavailable"


def test_d190_d189_source_mismatch_is_unavailable(monkeypatch):
    intent = action()
    retrieval = RetrievalStub()

    other_query = TrustedExecutionExperienceRetrievalQuery(
        workspace_id=WorkspaceId.PERSONAL,
        target_kind="tool",
        capability_id="exec.test.read",
        adapter_id="different-adapter",
        operation="inspect",
        effect="read",
        risk_class="R0",
    )
    other = evidence_set(other_query, (0,))
    advisory = TrustedExecutionExperienceAdvisoryEvaluator.evaluate(
        evidence_set=other
    )

    monkeypatch.setattr(
        TrustedExecutionExperienceAdvisoryEvaluator,
        "evaluate",
        classmethod(lambda cls, *, evidence_set: advisory),
    )
    result = binder(retrieval).bind(
        intent=intent,
        preparation=pending(intent),
    )
    assert result.binding_status == "unavailable"


def test_d190_invalid_input_uses_canonical_unavailable_without_attacker_metadata():
    result = binder(RetrievalStub(), WorkspaceId.COMPANY).bind(
        intent={"source_turn_id": "attacker"},
        preparation={"intent_digest": "attacker"},
    )
    assert result.binding_status == "unavailable"
    assert result.workspace_id is WorkspaceId.COMPANY
    assert result.source_intent_digest is None
    assert result.source_evidence_set_fingerprint is None
    assert result.advisory_fingerprint is None


def test_d190_does_not_mutate_current_action_or_preparation():
    retrieval = RetrievalStub((0, 2))
    intent = action(parameters={"alpha": (1, 2)})
    preparation = pending(intent)
    before_intent_digest = governed_action_intent_digest(intent)
    before_preparation_digest = preparation.intent_digest
    before_status = preparation.status

    result = binder(retrieval).bind(
        intent=intent,
        preparation=preparation,
    )
    assert result.binding_status == "bound"
    assert governed_action_intent_digest(intent) == before_intent_digest
    assert preparation.intent_digest == before_preparation_digest
    assert preparation.status == before_status
