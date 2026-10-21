from __future__ import annotations

from dataclasses import fields

import pytest

from app.contracts.structured_action_candidate_producer import (
    StructuredActionCandidateProductionOutcome,
    StructuredActionSemanticInput,
)
from app.contracts.structured_action_candidate_runtime import (
    D173_STRUCTURED_ACTION_CANDIDATE_RUNTIME_CONTRACT_VERSION,
    StructuredActionCandidateRuntimeOutcome,
)
from app.contracts.structured_action_intent_proposal import StructuredActionIntentCandidate
from app.contracts.structured_action_proposal_runtime import StructuredActionProposalRuntimeOutcome
from app.services.governed_action_intent_conversion import GovernedActionIntentConversionService
from app.services.structured_action_candidate_producer import StructuredActionCandidateProducer
from app.services.structured_action_candidate_runtime import StructuredActionCandidateRuntimeIntegration
from app.services.structured_action_intent_proposal import StructuredActionIntentProposalService
from app.services.structured_action_proposal_runtime import StructuredActionProposalRuntimeIntegration
from tests.test_d167_governed_action_runtime import DIGEST, TURN, build_runtime, command, outcome
from tests.test_d170_structured_action_proposal_runtime import RecordingRuntime


def semantic(action="system_info", *, parameters=None, missing_information=()):
    return StructuredActionSemanticInput(
        source_turn_id=TURN,
        source_artifact_digest=DIGEST,
        semantic_action=action,
        parameters=parameters or {},
        missing_information=missing_information,
    )


class RecordingProducer(StructuredActionCandidateProducer):
    def __init__(self):
        self.count = 0
        self.result = None

    def produce(self, source):
        self.count += 1
        self.result = super().produce(source)
        return self.result


class FixtureProducer(StructuredActionCandidateProducer):
    def __init__(self):
        self.count = 0
        self.candidate = StructuredActionIntentCandidate(
            source_turn_id=TURN,
            source_artifact_digest=DIGEST,
            target_kind="tool",
            adapter_id="tool.read",
            operation="inspect",
            parameters={},
        )

    def produce(self, source):
        self.count += 1
        return StructuredActionCandidateProductionOutcome(
            status="candidate_ready",
            reason_code="structured_action_candidate_ready",
            candidate=self.candidate,
        )


class RecordingProposal(StructuredActionIntentProposalService):
    def __init__(self):
        self.count = 0
        self.candidate = None
        self.result = None

    def propose(self, candidate):
        self.count += 1
        self.candidate = candidate
        self.result = super().propose(candidate)
        return self.result


class ForcedProposal(StructuredActionIntentProposalService):
    def __init__(self, result):
        self.result = result

    def propose(self, candidate):
        return self.result


class RecordingD170(StructuredActionProposalRuntimeIntegration):
    def __init__(self, runtime=None):
        super().__init__(
            conversion_service=GovernedActionIntentConversionService(),
            runtime_integration=runtime or RecordingRuntime(),
        )
        self.count = 0
        self.proposal = None
        self.command_seen = None
        self.outcome_seen = None

    def process(self, proposal, *, command, cognitive_outcome):
        self.count += 1
        self.proposal = proposal
        self.command_seen = command
        self.outcome_seen = cognitive_outcome
        return super().process(proposal, command=command, cognitive_outcome=cognitive_outcome)


class ForcedD170(StructuredActionProposalRuntimeIntegration):
    def __init__(self, result):
        self.result = result

    def process(self, proposal, *, command, cognitive_outcome):
        return self.result


def make_service(*, producer=None, proposal=None, runtime=None):
    producer = producer or RecordingProducer()
    proposal = proposal or RecordingProposal()
    runtime = runtime or RecordingD170()
    return (
        StructuredActionCandidateRuntimeIntegration(
            candidate_producer=producer,
            proposal_service=proposal,
            proposal_runtime=runtime,
        ),
        producer,
        proposal,
        runtime,
    )


def test_d173_outcome_contract_exact_and_versioned():
    assert {f.name for f in fields(StructuredActionCandidateRuntimeOutcome)} == {
        "status", "reason_code", "production", "proposal", "runtime", "contract_version"
    }
    result = make_service()[0].process(None, command=command(), cognitive_outcome=outcome())
    assert result.contract_version == D173_STRUCTURED_ACTION_CANDIDATE_RUNTIME_CONTRACT_VERSION


def test_d173_none_and_unsupported_stop_after_d172():
    service, producer, proposal, runtime = make_service()
    first = service.process(None, command=command(), cognitive_outcome=outcome())
    assert first.status == "no_action_semantics"
    assert proposal.count == runtime.count == 0
    second = service.process(
        semantic("not_in_catalog"), command=command(), cognitive_outcome=outcome()
    )
    assert second.status == "unsupported"
    assert proposal.count == runtime.count == 0
    assert producer.count == 2


def test_d173_clarification_uses_exact_candidate_and_stops_before_d170():
    service, producer, proposal, runtime = make_service()
    result = service.process(
        semantic("workspace_list"), command=command(), cognitive_outcome=outcome()
    )
    assert result.status == "needs_clarification"
    assert result.reason_code == "structured_action_information_missing"
    assert producer.result.candidate is proposal.candidate
    assert result.proposal is proposal.result
    assert result.proposal.missing_information == ("path",)
    assert proposal.count == 1 and runtime.count == 0


def test_d173_explicit_missing_information_survives_without_guessing():
    result = make_service()[0].process(
        semantic("echo", parameters={"value": "hello"}, missing_information=("recipient",)),
        command=command(),
        cognitive_outcome=outcome(),
    )
    assert result.status == "needs_clarification"
    assert result.production.candidate.missing_information == ("recipient",)
    assert result.proposal.missing_information == ("recipient",)


def test_d173_ready_preserves_candidate_proposal_command_and_outcome_identity():
    service, producer, proposal, runtime = make_service()
    current_command, current_outcome = command(), outcome()
    result = service.process(
        semantic(), command=current_command, cognitive_outcome=current_outcome
    )
    assert producer.result.candidate is proposal.candidate
    assert proposal.result is runtime.proposal is result.proposal
    assert runtime.command_seen is current_command
    assert runtime.outcome_seen is current_outcome
    assert proposal.count == runtime.count == 1
    assert result.status == "intent_rejected"
    assert result.reason_code == "source_artifact_mismatch"


def test_d173_preserves_owner_review_and_approval_unavailable():
    governed_runtime, store = build_runtime()
    first = make_service(
        producer=FixtureProducer(), runtime=RecordingD170(governed_runtime)
    )[0].process(semantic(), command=command(), cognitive_outcome=outcome())
    assert first.status == "prepared_for_owner_review"
    assert first.runtime.runtime.preparation.status == "pending_approval"
    assert store.pending_count == 1

    second = make_service(
        producer=FixtureProducer(), runtime=RecordingD170(RecordingRuntime(mode="approval_unavailable"))
    )[0].process(semantic(), command=command(), cognitive_outcome=outcome())
    assert second.status == "approval_unavailable"
    assert second.reason_code == "approval_service_unavailable"


@pytest.mark.parametrize(
    ("action", "parameters"),
    (
        ("system_info", {}),
        ("system_health", {}),
        ("workspace_overview", {}),
        ("project_snapshot", {"project_id": "12345678-1234-5678-1234-567812345678"}),
        ("echo", {"value": "hello"}),
        ("workspace_list", {"path": "docs"}),
        ("workspace_stat", {"path": "docs/ARCHITECTURE.md"}),
        ("workspace_read_text", {"path": "docs/ARCHITECTURE.md"}),
    ),
)
def test_d173_all_eight_d172_routes_reach_ready_seam_without_remap(action, parameters):
    service, producer, proposal, runtime = make_service()
    result = service.process(
        semantic(action, parameters=parameters), command=command(), cognitive_outcome=outcome()
    )
    assert producer.result.status == "candidate_ready"
    assert producer.result.candidate is proposal.candidate
    assert proposal.result is runtime.proposal
    assert result.status == "intent_rejected"


@pytest.mark.parametrize(
    ("semantic_value", "command_value", "outcome_value", "match"),
    (
        (object(), command(), outcome(), "semantic"),
        (None, object(), outcome(), "command"),
        (None, command(), object(), "cognitive_outcome"),
    ),
)
def test_d173_malformed_inputs_fail_closed(semantic_value, command_value, outcome_value, match):
    with pytest.raises(TypeError, match=match):
        make_service()[0].process(
            semantic_value, command=command_value, cognitive_outcome=outcome_value
        )


def test_d173_constructor_rejects_invalid_dependencies():
    with pytest.raises(TypeError, match="candidate_producer"):
        StructuredActionCandidateRuntimeIntegration(
            candidate_producer=object(),
            proposal_service=StructuredActionIntentProposalService(),
            proposal_runtime=RecordingD170(),
        )
    with pytest.raises(TypeError, match="proposal_service"):
        StructuredActionCandidateRuntimeIntegration(
            candidate_producer=StructuredActionCandidateProducer(),
            proposal_service=object(),
            proposal_runtime=RecordingD170(),
        )
    with pytest.raises(TypeError, match="proposal_runtime"):
        StructuredActionCandidateRuntimeIntegration(
            candidate_producer=StructuredActionCandidateProducer(),
            proposal_service=StructuredActionIntentProposalService(),
            proposal_runtime=object(),
        )


def test_d173_clarification_and_ready_mismatches_fail_closed():
    ready = StructuredActionIntentProposalService().propose(
        StructuredActionIntentCandidate(
            source_turn_id=TURN,
            source_artifact_digest=DIGEST,
            target_kind="tool",
            adapter_id="tool.system.info",
            operation="get_info",
            parameters={},
        )
    )
    with pytest.raises(RuntimeError, match="clarification_mismatch"):
        make_service(proposal=ForcedProposal(ready))[0].process(
            semantic("workspace_list"), command=command(), cognitive_outcome=outcome()
        )

    not_applicable = StructuredActionIntentProposalService().propose(None)
    with pytest.raises(RuntimeError, match="proposal_not_ready"):
        make_service(proposal=ForcedProposal(not_applicable))[0].process(
            semantic(), command=command(), cognitive_outcome=outcome()
        )


@pytest.mark.parametrize("mode", ("no_action_proposal", "proposal_not_convertible"))
def test_d173_ready_proposal_rejects_impossible_d170_nonterminal(mode):
    if mode == "no_action_proposal":
        impossible = StructuredActionProposalRuntimeOutcome(
            status="no_action_proposal", reason_code="no_structured_action_proposal"
        )
    else:
        conversion = GovernedActionIntentConversionService().convert(
            StructuredActionIntentProposalService().propose(None)
        )
        impossible = StructuredActionProposalRuntimeOutcome(
            status="proposal_not_convertible",
            reason_code=conversion.reason_code,
            conversion=conversion,
        )
    with pytest.raises(RuntimeError, match="downstream_invariant"):
        make_service(runtime=ForcedD170(impossible))[0].process(
            semantic(), command=command(), cognitive_outcome=outcome()
        )


def test_d173_invalid_downstream_object_fails_closed():
    with pytest.raises(RuntimeError, match="downstream_invalid"):
        make_service(runtime=ForcedD170(object()))[0].process(
            semantic(), command=command(), cognitive_outcome=outcome()
        )
