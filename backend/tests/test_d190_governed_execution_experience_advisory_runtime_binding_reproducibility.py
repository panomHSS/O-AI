from __future__ import annotations

from app.contracts.workspace import WorkspaceId
from app.services.governed_execution_experience_advisory_runtime_binding import (
    GovernedExecutionExperienceAdvisoryRuntimeBinder,
)
from tests.test_d190_governed_execution_experience_advisory_runtime_binding import (
    RetrievalStub,
    action,
    binder,
    evidence_set,
    pending,
)


def bind_with(
    tiers: tuple[int, ...] = (),
    *,
    truncated: bool = False,
    parameters=None,
    promotion_prefix: str = "promotion",
):
    class CustomRetrieval(RetrievalStub):
        def retrieve(self, query):
            self.queries.append(query)
            return evidence_set(
                query,
                tiers,
                truncated=truncated,
                promotion_prefix=promotion_prefix,
            )

    retrieval = CustomRetrieval()
    intent = action(parameters=parameters)
    return binder(retrieval).bind(
        intent=intent,
        preparation=pending(intent),
    )


def test_d190_same_input_produces_same_binding_and_fingerprint():
    left = bind_with((0, 1, 3))
    right = bind_with((0, 1, 3))
    assert left == right
    assert left.binding_fingerprint == right.binding_fingerprint


def test_d190_separate_binder_instances_are_reproducible():
    intent = action()
    left = GovernedExecutionExperienceAdvisoryRuntimeBinder(
        retrieval_service=RetrievalStub((0, 2)),
        workspace_scope=__import__(
            "app.contracts.workspace",
            fromlist=["WorkspaceScope"],
        ).WorkspaceScope(WorkspaceId.PERSONAL),
    )
    right = binder(RetrievalStub((0, 2)))
    assert left.bind(intent=intent, preparation=pending(intent)) == (
        right.bind(intent=intent, preparation=pending(intent))
    )


def test_d190_source_evidence_identity_changes_binding_fingerprint():
    left = bind_with((0,), promotion_prefix="alpha")
    right = bind_with((0,), promotion_prefix="beta")
    assert left.advisory_status == right.advisory_status == "exact_match"
    assert left.binding_fingerprint != right.binding_fingerprint


def test_d190_source_count_changes_binding_fingerprint():
    one = bind_with((0,))
    many = bind_with((0, 0, 0))
    assert one.advisory_status == many.advisory_status == "exact_match"
    assert one.binding_fingerprint != many.binding_fingerprint


def test_d190_truncation_changes_binding_fingerprint():
    normal = bind_with((0,) * 16, truncated=False)
    truncated = bind_with((0,) * 16, truncated=True)
    assert normal.advisory_status == truncated.advisory_status == "exact_match"
    assert normal.binding_fingerprint != truncated.binding_fingerprint


def test_d190_advisory_relevance_changes_binding_fingerprint():
    exact = bind_with((0,))
    operation = bind_with((1,))
    adapter = bind_with((2,))
    capability = bind_with((3,))
    assert len(
        {
            exact.binding_fingerprint,
            operation.binding_fingerprint,
            adapter.binding_fingerprint,
            capability.binding_fingerprint,
        }
    ) == 4


def test_d190_current_intent_digest_changes_binding_fingerprint():
    left = bind_with((), parameters={"value": 1})
    right = bind_with((), parameters={"value": 2})
    assert left.advisory_status == right.advisory_status == "no_evidence"
    # D188 retrieval identity excludes raw action parameters. The D188 query
    # semantics are unchanged, so its evidence-set fingerprint must remain
    # stable. D190 still binds the exact current intent digest separately.
    assert left.source_evidence_set_fingerprint == (
        right.source_evidence_set_fingerprint
    )
    assert left.source_intent_digest != right.source_intent_digest
    assert left.binding_fingerprint != right.binding_fingerprint


def test_d190_unavailable_is_independent_of_exception_detail():
    intent = action()
    left = binder(RetrievalStub(error=RuntimeError("private one"))).bind(
        intent=intent,
        preparation=pending(intent),
    )
    right = binder(RetrievalStub(error=RuntimeError("private two"))).bind(
        intent=intent,
        preparation=pending(intent),
    )
    assert left == right
    assert left.binding_status == "unavailable"


def test_d190_not_applicable_is_deterministic():
    intent = action()
    preparation = pending(
        intent,
        capability_id="capability.write",
        effect="write",
        risk_class="R1",
        reversible=True,
    )
    left = binder(RetrievalStub()).bind(
        intent=intent,
        preparation=preparation,
    )
    right = binder(RetrievalStub()).bind(
        intent=intent,
        preparation=preparation,
    )
    assert left == right
    assert left.binding_status == "not_applicable"
