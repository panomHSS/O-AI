from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest

from app.contracts.cognitive_trusted_experience_retrieval import (
    CognitiveTrustedExperienceEvidenceSet,
    compute_cognitive_trusted_experience_evidence_set_fingerprint,
)
from app.contracts.task_aware_ai_routing import AITaskKind
from tests.test_d148_cognitive_trusted_experience_retrieval import (
    BASE_TIME,
    add_record,
    ids,
    query,
    service_context,
)


def snapshot(order: tuple[int, ...] = (1, 2, 3)):
    with service_context() as (session, _repo, service):
        for number in order:
            add_record(
                session,
                number,
                updated_seconds=number,
                proposal_seed=f"stable-{number}",
            )
        session.commit()
        return service.retrieve(query())


def run_case(case: int) -> None:
    slot = (case - 1) % 8
    variant = (case - 1) // 8

    if slot == 0:
        left = snapshot()
        right = snapshot()
        assert left == right
        assert left.evidence_set_fingerprint == right.evidence_set_fingerprint
    elif slot == 1:
        assert snapshot((1, 2, 3)) == snapshot((3, 1, 2))
    elif slot == 2:
        value = snapshot()
        assert value.evidence_set_fingerprint == (
            compute_cognitive_trusted_experience_evidence_set_fingerprint(
                query=value.query,
                evidence=value.evidence,
            )
        )
    elif slot == 3:
        with service_context() as (_session, _repo, service):
            left = service.retrieve(query(interaction_intent="chat"))
            right = service.retrieve(query(interaction_intent="action_request"))
            assert left.evidence_set_fingerprint != right.evidence_set_fingerprint
    elif slot == 4:
        with service_context() as (_session, _repo, service):
            left = service.retrieve(query(cognitive_intent="general"))
            right = service.retrieve(query(cognitive_intent="comparison"))
            assert left.evidence_set_fingerprint != right.evidence_set_fingerprint
    elif slot == 5:
        with service_context() as (_session, _repo, service):
            left = service.retrieve(query(task_kind=AITaskKind.GENERAL_CHAT))
            right = service.retrieve(query(task_kind=AITaskKind.SOFTWARE_ENGINEERING))
            assert left.evidence_set_fingerprint != right.evidence_set_fingerprint
    elif slot == 6:
        value = snapshot()
        first = value.evidence[0]
        changed = replace(
            first,
            authorized_model_id=f"alternate-model-{variant}",
        )
        altered_items = (changed,) + value.evidence[1:]
        assert (
            compute_cognitive_trusted_experience_evidence_set_fingerprint(
                query=value.query,
                evidence=altered_items,
            )
            == value.evidence_set_fingerprint
        )
        altered_set = CognitiveTrustedExperienceEvidenceSet(
            workspace_id=value.workspace_id,
            query=value.query,
            evidence=altered_items,
            selected_count=value.selected_count,
            truncated=value.truncated,
            evidence_set_fingerprint=value.evidence_set_fingerprint,
        )
        assert altered_set.evidence[0].authorized_model_id == f"alternate-model-{variant}"
    else:
        with service_context() as (session, _repo, service):
            moment = BASE_TIME + timedelta(seconds=variant)
            add_record(session, 3, fixed_updated_at=moment)
            add_record(session, 1, fixed_updated_at=moment)
            add_record(session, 2, fixed_updated_at=moment)
            session.commit()
            left = service.retrieve(query())
            right = service.retrieve(query())
            assert ids(left) == [1, 2, 3]
            assert left == right


@pytest.mark.parametrize("case", range(1, 49), ids=[f"R{i:02d}" for i in range(1, 49)])
def test_d148_reproducibility_matrix(case: int) -> None:
    run_case(case)
