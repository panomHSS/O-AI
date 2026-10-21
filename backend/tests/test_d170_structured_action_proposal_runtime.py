from __future__ import annotations

from dataclasses import fields

import pytest

from app.contracts.governed_action import GovernedActionPreparation
from app.contracts.governed_action_runtime import GovernedActionRuntimeOutcome
from app.contracts.structured_action_intent_proposal import (
    StructuredActionIntentCandidate,
)
from app.contracts.structured_action_proposal_runtime import (
    D170_STRUCTURED_ACTION_PROPOSAL_RUNTIME_CONTRACT_VERSION,
    StructuredActionProposalRuntimeOutcome,
)
from app.services.governed_action import governed_action_intent_digest
from app.services.governed_action_intent_conversion import (
    GovernedActionIntentConversionService,
)
from app.services.governed_action_runtime import GovernedActionRuntimeIntegration
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


def proposal(**overrides):
    values = {
        "source_turn_id": TURN,
        "source_artifact_digest": DIGEST,
        "target_kind": "tool",
        "adapter_id": "tool.read",
        "operation": "inspect",
        "parameters": {},
    }
    values.update(overrides)
    return StructuredActionIntentProposalService().propose(
        StructuredActionIntentCandidate(**values)
    )


class SpyConversionService(GovernedActionIntentConversionService):
    def __init__(self, *, calls=None):
        self.calls = calls if calls is not None else []
        self.count = 0

    def convert(self, source):
        self.count += 1
        self.calls.append("d169")
        return super().convert(source)


class RecordingRuntime(GovernedActionRuntimeIntegration):
    def __init__(self, *, calls=None, mode="intent_rejected"):
        self.calls = calls if calls is not None else []
        self.mode = mode
        self.count = 0
        self.intent = None

    def prepare(self, intent, *, command, cognitive_outcome):
        self.count += 1
        self.calls.append("d167")
        self.intent = intent

        if self.mode == "no_action_intent":
            return GovernedActionRuntimeOutcome(
                status="no_action_intent",
                reason_code="no_action_intent",
            )

        digest = governed_action_intent_digest(intent)
        if self.mode == "approval_unavailable":
            reason = "approval_service_unavailable"
            preparation = GovernedActionPreparation(
                intent_digest=digest,
                status="unavailable",
                reason_code=reason,
            )
            return GovernedActionRuntimeOutcome(
                status="approval_unavailable",
                reason_code=reason,
                intent_digest=digest,
                preparation=preparation,
            )

        return GovernedActionRuntimeOutcome(
            status="intent_rejected",
            reason_code="source_artifact_mismatch",
            intent_digest=digest,
        )


def integration(conversion=None, runtime=None):
    return StructuredActionProposalRuntimeIntegration(
        conversion_service=conversion or GovernedActionIntentConversionService(),
        runtime_integration=runtime or RecordingRuntime(),
    )


def test_d170_outcome_contract_is_exact_and_versioned():
    names = {item.name for item in fields(StructuredActionProposalRuntimeOutcome)}
    assert names == {
        "status",
        "reason_code",
        "conversion",
        "runtime",
        "contract_version",
    }
    result = integration().process(
        None,
        command=command(),
        cognitive_outcome=outcome(),
    )
    assert result.contract_version == (
        D170_STRUCTURED_ACTION_PROPOSAL_RUNTIME_CONTRACT_VERSION
    )


def test_d170_no_proposal_stops_before_d169_and_d167():
    conversion = SpyConversionService()
    runtime = RecordingRuntime()
    result = integration(conversion, runtime).process(
        None,
        command=command(),
        cognitive_outcome=outcome(),
    )

    assert result.status == "no_action_proposal"
    assert result.reason_code == "no_structured_action_proposal"
    assert result.conversion is None
    assert result.runtime is None
    assert conversion.count == 0
    assert runtime.count == 0


@pytest.mark.parametrize(
    ("source", "expected_reason"),
    (
        (
            StructuredActionIntentProposalService().propose(None),
            "proposal_not_applicable",
        ),
        (
            proposal(adapter_id=None),
            "proposal_needs_clarification",
        ),
        (
            proposal(target_kind="browser"),
            "proposal_unsupported",
        ),
    ),
)
def test_d170_nonconvertible_proposals_stop_before_d167(
    source,
    expected_reason,
):
    runtime = RecordingRuntime()
    result = integration(runtime=runtime).process(
        source,
        command=command(),
        cognitive_outcome=outcome(),
    )

    assert result.status == "proposal_not_convertible"
    assert result.reason_code == expected_reason
    assert result.conversion is not None
    assert result.conversion.reason_code == expected_reason
    assert result.runtime is None
    assert runtime.count == 0


def test_d170_calls_d169_before_d167_and_hands_off_exact_intent():
    calls = []
    conversion = SpyConversionService(calls=calls)
    runtime = RecordingRuntime(calls=calls)

    result = integration(conversion, runtime).process(
        proposal(),
        command=command(),
        cognitive_outcome=outcome(),
    )

    assert calls == ["d169", "d167"]
    assert conversion.count == 1
    assert runtime.count == 1
    assert result.conversion is not None
    assert runtime.intent is result.conversion.action_intent


def test_d170_lineage_rejection_preserves_d167_status_and_reason():
    runtime, store = build_runtime()
    result = integration(runtime=runtime).process(
        proposal(source_turn_id="other-turn"),
        command=command(),
        cognitive_outcome=outcome(),
    )

    assert result.status == "intent_rejected"
    assert result.reason_code == "source_turn_request_mismatch"
    assert result.runtime is not None
    assert result.reason_code == result.runtime.reason_code
    assert store.pending_count == 0


def test_d170_capability_rejection_remains_downstream_governance():
    runtime, store = build_runtime()
    result = integration(runtime=runtime).process(
        proposal(operation="unknown"),
        command=command(),
        cognitive_outcome=outcome(),
    )

    assert result.status == "intent_rejected"
    assert result.reason_code == "capability_not_permitted"
    assert result.runtime is not None
    assert result.runtime.preparation is not None
    assert result.runtime.preparation.status == "rejected"
    assert store.pending_count == 0


def test_d170_valid_lineage_reaches_owner_review_only():
    runtime, store = build_runtime()
    result = integration(runtime=runtime).process(
        proposal(),
        command=command(),
        cognitive_outcome=outcome(),
    )

    assert result.status == "prepared_for_owner_review"
    assert result.runtime is not None
    assert result.runtime.preparation is not None
    assert result.runtime.preparation.status == "pending_approval"
    assert result.runtime.preparation.approval is not None
    assert result.runtime.preparation.approval.status == "pending"
    assert store.pending_count == 1


def test_d170_approval_unavailable_is_preserved_exactly():
    runtime = RecordingRuntime(mode="approval_unavailable")
    result = integration(runtime=runtime).process(
        proposal(),
        command=command(),
        cognitive_outcome=outcome(),
    )

    assert result.status == "approval_unavailable"
    assert result.reason_code == "approval_service_unavailable"
    assert result.runtime is not None
    assert result.runtime.preparation is not None
    assert result.runtime.preparation.status == "unavailable"


def test_d170_impossible_d167_no_action_intent_fails_closed():
    runtime = RecordingRuntime(mode="no_action_intent")
    with pytest.raises(
        RuntimeError,
        match="structured_action_runtime_unexpected_no_action_intent",
    ):
        integration(runtime=runtime).process(
            proposal(),
            command=command(),
            cognitive_outcome=outcome(),
        )


@pytest.mark.parametrize("bad", (object(), "raw text", 42))
def test_d170_wrong_proposal_type_fails_closed(bad):
    with pytest.raises(TypeError, match="StructuredActionIntentProposal"):
        integration().process(
            bad,  # type: ignore[arg-type]
            command=command(),
            cognitive_outcome=outcome(),
        )


def test_d170_wrong_command_type_fails_closed():
    with pytest.raises(TypeError, match="CommandRequest"):
        integration().process(
            None,
            command=object(),  # type: ignore[arg-type]
            cognitive_outcome=outcome(),
        )


def test_d170_wrong_cognitive_outcome_type_fails_closed():
    with pytest.raises(TypeError, match="CognitiveExecutiveOutcome"):
        integration().process(
            None,
            command=command(),
            cognitive_outcome=object(),  # type: ignore[arg-type]
        )


def test_d170_outcome_rejects_authority_like_invalid_state_combinations():
    conversion = GovernedActionIntentConversionService().convert(proposal())

    with pytest.raises(
        ValueError,
        match="structured_action_runtime_no_proposal_invalid",
    ):
        StructuredActionProposalRuntimeOutcome(
            status="no_action_proposal",
            reason_code="no_structured_action_proposal",
            conversion=conversion,
        )

    with pytest.raises(
        ValueError,
        match="structured_action_runtime_downstream_invalid",
    ):
        StructuredActionProposalRuntimeOutcome(
            status="prepared_for_owner_review",
            reason_code="pending_owner_review",
            conversion=conversion,
            runtime=None,
        )