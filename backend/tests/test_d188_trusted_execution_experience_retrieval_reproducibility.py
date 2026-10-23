from __future__ import annotations

from dataclasses import replace

from app.contracts.governed_execution_experience_retrieval import (
    TrustedExecutionExperienceEvidenceSet,
    compute_trusted_execution_experience_evidence_set_fingerprint,
)
from tests.test_d188_trusted_execution_experience_retrieval import (
    add_record,
    ids,
    query,
    service_context,
)


def snapshot(order: tuple[int, ...] = (1, 2, 3)):
    with service_context() as (session, _repository, service):
        for number in order:
            add_record(session, number, updated_seconds=number)
        session.commit()
        return service.retrieve(query())


def test_d188_identical_data_and_query_are_reproducible():
    left = snapshot()
    right = snapshot()
    assert left == right
    assert left.evidence_set_fingerprint == right.evidence_set_fingerprint


def test_d188_insertion_order_does_not_change_selection():
    left = snapshot((1, 2, 3))
    right = snapshot((3, 1, 2))
    assert ids(left) == ids(right) == [3, 2, 1]
    assert left.evidence_set_fingerprint == right.evidence_set_fingerprint


def test_d188_query_change_changes_evidence_set_fingerprint():
    with service_context() as (_session, _repository, service):
        left = service.retrieve(query(adapter_id="adapter-a"))
        right = service.retrieve(query(adapter_id="adapter-b"))
        assert left.evidence == right.evidence == ()
        assert left.evidence_set_fingerprint != right.evidence_set_fingerprint


def test_d188_ordered_evidence_identity_is_fingerprint_input():
    value = snapshot()
    reordered = tuple(reversed(value.evidence))
    changed = compute_trusted_execution_experience_evidence_set_fingerprint(
        query=value.query,
        evidence=reordered,
    )
    assert changed != value.evidence_set_fingerprint


def test_d188_non_identity_projection_change_does_not_enter_set_fingerprint():
    value = snapshot()
    first = value.evidence[0]
    changed = replace(first, adapter_id="different-adapter")
    altered = (changed,) + value.evidence[1:]
    assert (
        compute_trusted_execution_experience_evidence_set_fingerprint(
            query=value.query,
            evidence=altered,
        )
        == value.evidence_set_fingerprint
    )
    altered_set = TrustedExecutionExperienceEvidenceSet(
        workspace_id=value.workspace_id,
        query=value.query,
        evidence=altered,
        selected_count=value.selected_count,
        truncated=value.truncated,
        evidence_set_fingerprint=value.evidence_set_fingerprint,
    )
    assert altered_set.evidence[0].adapter_id == "different-adapter"
