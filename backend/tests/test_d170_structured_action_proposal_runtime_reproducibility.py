from __future__ import annotations

from app.contracts.structured_action_intent_proposal import (
    StructuredActionIntentCandidate,
)
from app.services.governed_action_intent_conversion import (
    GovernedActionIntentConversionService,
)
from app.services.structured_action_intent_proposal import (
    StructuredActionIntentProposalService,
)
from app.services.structured_action_proposal_runtime import (
    StructuredActionProposalRuntimeIntegration,
)
from tests.test_d167_governed_action_runtime import (
    DIGEST,
    TURN,
    build_runtime,
    command,
    outcome,
)
from tests.test_d170_structured_action_proposal_runtime import RecordingRuntime


def proposal(parameters=None, **overrides):
    values = {
        "source_turn_id": TURN,
        "source_artifact_digest": DIGEST,
        "target_kind": "tool",
        "adapter_id": "tool.read",
        "operation": "inspect",
        "parameters": parameters or {},
    }
    values.update(overrides)
    return StructuredActionIntentProposalService().propose(
        StructuredActionIntentCandidate(**values)
    )


def integration(runtime):
    return StructuredActionProposalRuntimeIntegration(
        conversion_service=GovernedActionIntentConversionService(),
        runtime_integration=runtime,
    )


def test_d170_no_proposal_is_reproducible():
    service = integration(RecordingRuntime())
    first = service.process(
        None,
        command=command(),
        cognitive_outcome=outcome(),
    )
    second = service.process(
        None,
        command=command(),
        cognitive_outcome=outcome(),
    )
    assert first == second


def test_d170_nonconvertible_semantics_are_reproducible():
    source = StructuredActionIntentProposalService().propose(None)
    service = integration(RecordingRuntime())

    first = service.process(
        source,
        command=command(),
        cognitive_outcome=outcome(),
    )
    second = service.process(
        source,
        command=command(),
        cognitive_outcome=outcome(),
    )

    assert first == second
    assert first.status == "proposal_not_convertible"


def test_d170_mapping_order_preserves_rejection_semantics():
    first_runtime = RecordingRuntime()
    second_runtime = RecordingRuntime()

    first = integration(first_runtime).process(
        proposal({"b": 2, "a": {"y": 2, "x": 1}}),
        command=command(),
        cognitive_outcome=outcome(),
    )
    second = integration(second_runtime).process(
        proposal({"a": {"x": 1, "y": 2}, "b": 2}),
        command=command(),
        cognitive_outcome=outcome(),
    )

    assert first == second
    assert first.status == "intent_rejected"
    assert first.reason_code == "source_artifact_mismatch"


def test_d170_owner_review_reproducibility_is_semantic_not_ticket_identity():
    first_runtime, first_store = build_runtime()
    second_runtime, second_store = build_runtime()

    first = integration(first_runtime).process(
        proposal(),
        command=command(),
        cognitive_outcome=outcome(),
    )
    second = integration(second_runtime).process(
        proposal(),
        command=command(),
        cognitive_outcome=outcome(),
    )

    assert first.status == second.status == "prepared_for_owner_review"
    assert first.reason_code == second.reason_code
    assert first_store.pending_count == second_store.pending_count == 1
    assert first.runtime is not None
    assert second.runtime is not None
    assert first.runtime.preparation is not None
    assert second.runtime.preparation is not None
    assert first.runtime.preparation.status == "pending_approval"
    assert second.runtime.preparation.status == "pending_approval"