from __future__ import annotations

from app.contracts.structured_action_candidate_producer import (
    StructuredActionCandidateProductionOutcome,
    StructuredActionSemanticInput,
)
from app.contracts.structured_action_intent_proposal import StructuredActionIntentCandidate
from app.services.governed_action_intent_conversion import GovernedActionIntentConversionService
from app.services.structured_action_candidate_producer import StructuredActionCandidateProducer
from app.services.structured_action_candidate_runtime import StructuredActionCandidateRuntimeIntegration
from app.services.structured_action_intent_proposal import StructuredActionIntentProposalService
from app.services.structured_action_proposal_runtime import StructuredActionProposalRuntimeIntegration
from tests.test_d167_governed_action_runtime import DIGEST, TURN, build_runtime, command, outcome
from tests.test_d170_structured_action_proposal_runtime import RecordingRuntime


class FixtureProducer(StructuredActionCandidateProducer):
    def produce(self, source):
        return StructuredActionCandidateProductionOutcome(
            status="candidate_ready",
            reason_code="structured_action_candidate_ready",
            candidate=StructuredActionIntentCandidate(
                source_turn_id=TURN,
                source_artifact_digest=DIGEST,
                target_kind="tool",
                adapter_id="tool.read",
                operation="inspect",
                parameters={},
            ),
        )


def make_service(*, producer=None, runtime=None):
    return StructuredActionCandidateRuntimeIntegration(
        candidate_producer=producer or StructuredActionCandidateProducer(),
        proposal_service=StructuredActionIntentProposalService(),
        proposal_runtime=StructuredActionProposalRuntimeIntegration(
            conversion_service=GovernedActionIntentConversionService(),
            runtime_integration=runtime or RecordingRuntime(),
        ),
    )


def semantic(action, *, parameters=None, missing_information=()):
    return StructuredActionSemanticInput(
        source_turn_id=TURN,
        source_artifact_digest=DIGEST,
        semantic_action=action,
        parameters=parameters or {},
        missing_information=missing_information,
    )


def test_d173_no_semantics_and_unsupported_are_reproducible():
    service = make_service()
    assert service.process(None, command=command(), cognitive_outcome=outcome()) == service.process(
        None, command=command(), cognitive_outcome=outcome()
    )
    source = semantic("unknown_semantic")
    assert service.process(source, command=command(), cognitive_outcome=outcome()) == service.process(
        source, command=command(), cognitive_outcome=outcome()
    )


def test_d173_clarification_missing_information_order_is_canonical():
    first = make_service().process(
        semantic("echo", parameters={"value": "hello"}, missing_information=("scope", "recipient")),
        command=command(), cognitive_outcome=outcome(),
    )
    second = make_service().process(
        semantic("echo", parameters={"value": "hello"}, missing_information=("recipient", "scope")),
        command=command(), cognitive_outcome=outcome(),
    )
    assert first == second
    assert first.proposal.missing_information == ("recipient", "scope")


def test_d173_parameter_source_mutation_cannot_change_input_or_candidate():
    parameters = {"path": "docs/ARCHITECTURE.md"}
    structured = semantic("workspace_read_text", parameters=parameters)
    parameters["path"] = "changed.txt"
    result = make_service().process(structured, command=command(), cognitive_outcome=outcome())
    assert structured.parameters["path"] == "docs/ARCHITECTURE.md"
    assert result.production.candidate.parameters["path"] == "docs/ARCHITECTURE.md"


def test_d173_equivalent_ready_inputs_preserve_semantic_rejection():
    first = make_service().process(
        semantic("echo", parameters={"value": "hello"}),
        command=command(), cognitive_outcome=outcome(),
    )
    second = make_service().process(
        StructuredActionSemanticInput(
            semantic_action="echo",
            source_artifact_digest=DIGEST,
            source_turn_id=TURN,
            parameters={"value": "hello"},
        ),
        command=command(), cognitive_outcome=outcome(),
    )
    assert first == second
    assert first.status == "intent_rejected"
    assert first.reason_code == "source_artifact_mismatch"


def test_d173_owner_review_reproducibility_is_semantic_not_ticket_identity():
    first_runtime, first_store = build_runtime()
    second_runtime, second_store = build_runtime()
    first = make_service(producer=FixtureProducer(), runtime=first_runtime).process(
        semantic("system_info"), command=command(), cognitive_outcome=outcome()
    )
    second = make_service(producer=FixtureProducer(), runtime=second_runtime).process(
        semantic("system_info"), command=command(), cognitive_outcome=outcome()
    )
    assert first.status == second.status == "prepared_for_owner_review"
    assert first.reason_code == second.reason_code
    assert first_store.pending_count == second_store.pending_count == 1
    assert first.runtime.runtime.preparation.status == "pending_approval"
    assert second.runtime.runtime.preparation.status == "pending_approval"
