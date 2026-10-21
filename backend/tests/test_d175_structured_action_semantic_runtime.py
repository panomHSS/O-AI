from __future__ import annotations

from dataclasses import fields
from typing import get_args

import pytest

from app.contracts.structured_action_candidate_runtime import (
    StructuredActionCandidateRuntimeOutcome,
)
from app.contracts.structured_action_semantic_lineage import (
    StructuredActionSemanticDraft,
    StructuredActionSemanticLineageOutcome,
)
from app.contracts.structured_action_semantic_runtime import (
    D175_STRUCTURED_ACTION_SEMANTIC_RUNTIME_CONTRACT_VERSION,
    StructuredActionSemanticRuntimeOutcome,
    StructuredActionSemanticRuntimeStatus,
)
from app.services.structured_action_candidate_runtime import (
    StructuredActionCandidateRuntimeIntegration,
)
from app.services.structured_action_semantic_lineage import (
    StructuredActionSemanticLineageBinder,
)
from app.services.structured_action_semantic_runtime import (
    StructuredActionSemanticRuntimeIntegration,
)
from tests.test_d167_governed_action_runtime import build_runtime, command, outcome
from tests.test_d170_structured_action_proposal_runtime import RecordingRuntime
from tests.test_d173_structured_action_candidate_runtime import (
    FixtureProducer,
    RecordingD170,
    make_service as make_d173,
)


_UNSET = object()


def draft(
    action: str = "system_info",
    *,
    parameters: dict[str, object] | None = None,
    missing_information: tuple[str, ...] = (),
) -> StructuredActionSemanticDraft:
    return StructuredActionSemanticDraft(
        semantic_action=action,
        parameters=parameters or {},
        missing_information=missing_information,
    )


class RecordingBinder(StructuredActionSemanticLineageBinder):
    def __init__(self, forced=_UNSET) -> None:
        self.forced = forced
        self.count = 0
        self.draft_seen = None
        self.command_seen = None
        self.outcome_seen = None
        self.result = None

    def bind(self, value, *, command, cognitive_outcome):
        self.count += 1
        self.draft_seen = value
        self.command_seen = command
        self.outcome_seen = cognitive_outcome
        if self.forced is not _UNSET:
            self.result = self.forced
        else:
            self.result = super().bind(
                value,
                command=command,
                cognitive_outcome=cognitive_outcome,
            )
        return self.result


class RecordingCandidateRuntime(StructuredActionCandidateRuntimeIntegration):
    def __init__(self, *, delegate=None, forced=_UNSET) -> None:
        self.delegate = delegate or make_d173()[0]
        self.forced = forced
        self.count = 0
        self.semantic_seen = None
        self.command_seen = None
        self.outcome_seen = None
        self.result = None

    def process(self, semantic, *, command, cognitive_outcome):
        self.count += 1
        self.semantic_seen = semantic
        self.command_seen = command
        self.outcome_seen = cognitive_outcome
        if self.forced is not _UNSET:
            self.result = self.forced
        else:
            self.result = self.delegate.process(
                semantic,
                command=command,
                cognitive_outcome=cognitive_outcome,
            )
        return self.result


def make_service(*, binder=None, candidate=None):
    binder = binder or RecordingBinder()
    candidate = candidate or RecordingCandidateRuntime()
    return (
        StructuredActionSemanticRuntimeIntegration(
            lineage_binder=binder,
            candidate_runtime=candidate,
        ),
        binder,
        candidate,
    )


def test_d175_contract_exact_fields_statuses_and_version() -> None:
    assert {item.name for item in fields(StructuredActionSemanticRuntimeOutcome)} == {
        "status",
        "reason_code",
        "lineage",
        "runtime",
        "contract_version",
    }
    assert set(get_args(StructuredActionSemanticRuntimeStatus)) == {
        "not_applicable",
        "lineage_unavailable",
        "needs_clarification",
        "unsupported",
        "intent_rejected",
        "prepared_for_owner_review",
        "approval_unavailable",
    }
    result = make_service()[0].process(
        None,
        command=command(),
        cognitive_outcome=outcome(),
    )
    assert (
        result.contract_version
        == D175_STRUCTURED_ACTION_SEMANTIC_RUNTIME_CONTRACT_VERSION
    )


def test_d175_none_stops_after_exactly_one_d174_call() -> None:
    service, binder, candidate = make_service()
    current_command = command()
    current_outcome = outcome()
    result = service.process(
        None,
        command=current_command,
        cognitive_outcome=current_outcome,
    )
    assert result.status == "not_applicable"
    assert result.reason_code == "no_structured_action_semantic_draft"
    assert result.lineage is binder.result
    assert result.runtime is None
    assert binder.count == 1
    assert candidate.count == 0
    assert binder.command_seen is current_command
    assert binder.outcome_seen is current_outcome


def test_d175_lineage_unavailable_stops_before_d173() -> None:
    service, binder, candidate = make_service()
    result = service.process(
        draft(),
        command=command(name="tool.execute"),
        cognitive_outcome=outcome(),
    )
    assert result.status == "lineage_unavailable"
    assert result.reason_code == "current_cognitive_publication_unavailable"
    assert result.lineage is binder.result
    assert result.runtime is None
    assert binder.count == 1
    assert candidate.count == 0


def test_d175_semantic_ready_preserves_exact_objects_into_d173() -> None:
    service, binder, candidate = make_service()
    value = draft("system_info")
    current_command = command()
    current_outcome = outcome()
    result = service.process(
        value,
        command=current_command,
        cognitive_outcome=current_outcome,
    )
    assert binder.count == candidate.count == 1
    assert binder.draft_seen is value
    assert binder.command_seen is candidate.command_seen is current_command
    assert binder.outcome_seen is candidate.outcome_seen is current_outcome
    assert candidate.semantic_seen is binder.result.semantic
    assert result.lineage is binder.result
    assert result.runtime is candidate.result
    assert result.status == candidate.result.status
    assert result.reason_code == candidate.result.reason_code


def test_d175_unsupported_is_preserved_exactly() -> None:
    service, binder, candidate = make_service()
    result = service.process(
        draft("future_semantic"),
        command=command(),
        cognitive_outcome=outcome(),
    )
    assert result.status == "unsupported"
    assert result.reason_code == "structured_action_semantic_unsupported"
    assert result.lineage is binder.result
    assert result.runtime is candidate.result


def test_d175_needs_clarification_is_preserved_exactly() -> None:
    service, binder, candidate = make_service()
    result = service.process(
        draft("workspace_list"),
        command=command(),
        cognitive_outcome=outcome(),
    )
    assert result.status == "needs_clarification"
    assert result.reason_code == "structured_action_information_missing"
    assert result.lineage is binder.result
    assert result.runtime is candidate.result


def test_d175_intent_rejected_is_preserved_exactly() -> None:
    service, binder, candidate = make_service()
    result = service.process(
        draft("system_info"),
        command=command(),
        cognitive_outcome=outcome(),
    )
    assert result.status == "intent_rejected"
    assert result.lineage is binder.result
    assert result.runtime is candidate.result


def test_d175_prepared_for_owner_review_is_preserved_not_upgraded() -> None:
    governed_runtime, store = build_runtime()
    d173 = make_d173(
        producer=FixtureProducer(),
        runtime=RecordingD170(governed_runtime),
    )[0]
    candidate = RecordingCandidateRuntime(delegate=d173)
    service, binder, candidate = make_service(candidate=candidate)
    result = service.process(
        draft("system_info"),
        command=command(),
        cognitive_outcome=outcome(),
    )
    assert result.status == "prepared_for_owner_review"
    assert result.lineage is binder.result
    assert result.runtime is candidate.result
    assert result.runtime.runtime.runtime.preparation.status == "pending_approval"
    assert store.pending_count == 1


def test_d175_approval_unavailable_is_preserved_exactly() -> None:
    d173 = make_d173(
        producer=FixtureProducer(),
        runtime=RecordingD170(
            RecordingRuntime(mode="approval_unavailable")
        ),
    )[0]
    candidate = RecordingCandidateRuntime(delegate=d173)
    service, binder, candidate = make_service(candidate=candidate)
    result = service.process(
        draft("system_info"),
        command=command(),
        cognitive_outcome=outcome(),
    )
    assert result.status == "approval_unavailable"
    assert result.reason_code == "approval_service_unavailable"
    assert result.lineage is binder.result
    assert result.runtime is candidate.result


@pytest.mark.parametrize(
    ("draft_value", "command_value", "outcome_value", "match"),
    (
        (object(), command(), outcome(), "draft"),
        (None, object(), outcome(), "command"),
        (None, command(), object(), "cognitive_outcome"),
    ),
)
def test_d175_malformed_inputs_fail_before_orchestration(
    draft_value,
    command_value,
    outcome_value,
    match: str,
) -> None:
    service, binder, candidate = make_service()
    with pytest.raises(TypeError, match=match):
        service.process(
            draft_value,  # type: ignore[arg-type]
            command=command_value,  # type: ignore[arg-type]
            cognitive_outcome=outcome_value,  # type: ignore[arg-type]
        )
    assert binder.count == candidate.count == 0


@pytest.mark.parametrize("dependency", ("binder", "runtime"))
def test_d175_constructor_rejects_invalid_dependencies(dependency: str) -> None:
    binder = (
        object()
        if dependency == "binder"
        else StructuredActionSemanticLineageBinder()
    )
    runtime = (
        object()
        if dependency == "runtime"
        else make_d173()[0]
    )
    with pytest.raises(TypeError, match=("lineage_binder|candidate_runtime")):
        StructuredActionSemanticRuntimeIntegration(
            lineage_binder=binder,  # type: ignore[arg-type]
            candidate_runtime=runtime,  # type: ignore[arg-type]
        )


def test_d175_wrong_d174_object_fails_closed() -> None:
    service, binder, candidate = make_service(
        binder=RecordingBinder(forced=object())
    )
    with pytest.raises(RuntimeError, match="lineage_invalid"):
        service.process(
            draft(),
            command=command(),
            cognitive_outcome=outcome(),
        )
    assert binder.count == 1
    assert candidate.count == 0


def test_d175_semantic_ready_without_semantic_fails_closed() -> None:
    lineage = StructuredActionSemanticLineageBinder().bind(
        draft(),
        command=command(),
        cognitive_outcome=outcome(),
    )
    object.__setattr__(lineage, "semantic", None)
    service, binder, candidate = make_service(
        binder=RecordingBinder(forced=lineage)
    )
    with pytest.raises(RuntimeError, match="semantic_missing"):
        service.process(
            draft(),
            command=command(),
            cognitive_outcome=outcome(),
        )
    assert binder.count == 1
    assert candidate.count == 0


def test_d175_unknown_d174_status_fails_closed() -> None:
    lineage = StructuredActionSemanticLineageBinder().bind(
        draft(),
        command=command(),
        cognitive_outcome=outcome(),
    )
    object.__setattr__(lineage, "status", "unknown")
    service, _, candidate = make_service(
        binder=RecordingBinder(forced=lineage)
    )
    with pytest.raises(RuntimeError, match="lineage_status_invalid"):
        service.process(
            draft(),
            command=command(),
            cognitive_outcome=outcome(),
        )
    assert candidate.count == 0


def test_d175_wrong_d173_object_fails_closed() -> None:
    candidate = RecordingCandidateRuntime(forced=object())
    service, _, candidate = make_service(candidate=candidate)
    with pytest.raises(RuntimeError, match="downstream_invalid"):
        service.process(
            draft(),
            command=command(),
            cognitive_outcome=outcome(),
        )
    assert candidate.count == 1


def test_d175_no_action_semantics_after_semantic_ready_is_impossible() -> None:
    impossible = make_d173()[0].process(
        None,
        command=command(),
        cognitive_outcome=outcome(),
    )
    assert impossible.status == "no_action_semantics"
    candidate = RecordingCandidateRuntime(forced=impossible)
    service, _, candidate = make_service(candidate=candidate)
    with pytest.raises(RuntimeError, match="downstream_invariant"):
        service.process(
            draft(),
            command=command(),
            cognitive_outcome=outcome(),
        )
    assert candidate.count == 1


def test_d175_unknown_d173_status_fails_closed() -> None:
    runtime = make_d173()[0].process(
        StructuredActionSemanticLineageBinder()
        .bind(
            draft("future_semantic"),
            command=command(),
            cognitive_outcome=outcome(),
        )
        .semantic,
        command=command(),
        cognitive_outcome=outcome(),
    )
    assert runtime.status == "unsupported"
    object.__setattr__(runtime, "status", "unknown")
    candidate = RecordingCandidateRuntime(forced=runtime)
    service, _, _ = make_service(candidate=candidate)
    with pytest.raises(RuntimeError, match="downstream_status_invalid"):
        service.process(
            draft(),
            command=command(),
            cognitive_outcome=outcome(),
        )


def test_d175_outcome_contract_rejects_incoherent_states() -> None:
    lineage_none = StructuredActionSemanticLineageBinder().bind(
        None,
        command=command(),
        cognitive_outcome=outcome(),
    )
    with pytest.raises(ValueError, match="not_applicable_invalid"):
        StructuredActionSemanticRuntimeOutcome(
            status="not_applicable",
            reason_code="no_structured_action_semantic_draft",
            lineage=lineage_none,
            runtime=make_d173()[0].process(
                None,
                command=command(),
                cognitive_outcome=outcome(),
            ),
        )

    lineage_ready = StructuredActionSemanticLineageBinder().bind(
        draft(),
        command=command(),
        cognitive_outcome=outcome(),
    )
    with pytest.raises(ValueError, match="downstream_invalid"):
        StructuredActionSemanticRuntimeOutcome(
            status="intent_rejected",
            reason_code="source_artifact_mismatch",
            lineage=lineage_ready,
        )

    with pytest.raises(ValueError, match="version_invalid"):
        StructuredActionSemanticRuntimeOutcome(
            status="not_applicable",
            reason_code="no_structured_action_semantic_draft",
            lineage=lineage_none,
            contract_version="wrong",
        )
