\
from __future__ import annotations

from dataclasses import replace

import pytest

from app.contracts.workspace import WorkspaceId
from app.services.cognitive_trusted_experience_runtime_binding import (
    CognitiveTrustedExperienceRuntimeBinder,
)
from tests.test_d150_cognitive_trusted_experience_runtime_binding import (
    StubRetrieval,
    bind,
    make_set,
    make_task,
)


def run_case(case: int) -> None:
    slot = (case - 1) % 8
    variant = (case - 1) // 8

    if slot == 0:
        task = make_task()
        retrieval = StubRetrieval(lambda query: make_set(query, (variant % 4,)))
        binder = CognitiveTrustedExperienceRuntimeBinder(retrieval)
        first = binder.bind(task=task)
        second = binder.bind(task=task)
        assert first == second
    elif slot == 1:
        task = make_task()
        left = CognitiveTrustedExperienceRuntimeBinder(
            StubRetrieval(lambda query: make_set(query, (0, 1)))
        ).bind(task=task)
        right = CognitiveTrustedExperienceRuntimeBinder(
            StubRetrieval(lambda query: make_set(query, (0, 1)))
        ).bind(task=task)
        assert left == right
    elif slot == 2:
        one, _ = bind(tiers=(0,))
        many, _ = bind(tiers=(0,) * (variant + 2))
        assert one.advisory_status == many.advisory_status == "exact_match"
        assert one.best_relevance_tier == many.best_relevance_tier == 0
        assert one.source_selected_count != many.source_selected_count
        assert (
            one.source_evidence_set_fingerprint
            != many.source_evidence_set_fingerprint
        )
    elif slot == 3:
        def left_factory(query):
            return make_set(query, (0,), model="historical-a")
        def right_factory(query):
            source = make_set(query, (0,), model="historical-b")
            original = source.evidence[0]
            changed = replace(
                original,
                authorized_adapter_id=f"adapter-{variant}",
                authorized_model_id=f"model-{variant}",
                authorized_profile_id=f"profile-{variant}",
            )
            object.__setattr__(source, "evidence", (changed,))
            return source
        task = make_task()
        left = CognitiveTrustedExperienceRuntimeBinder(
            StubRetrieval(left_factory)
        ).bind(task=task)
        right = CognitiveTrustedExperienceRuntimeBinder(
            StubRetrieval(right_factory)
        ).bind(task=task)
        assert left == right
    elif slot == 4:
        normal, _ = bind(tiers=(0,) * 16, truncated=False)
        truncated, _ = bind(tiers=(0,) * 16, truncated=True)
        assert normal.advisory_status == truncated.advisory_status
        assert normal.best_relevance_tier == truncated.best_relevance_tier
        assert (
            normal.source_evidence_set_fingerprint
            == truncated.source_evidence_set_fingerprint
        )
        assert normal.source_truncated is False
        assert truncated.source_truncated is True
        assert normal.advisory_fingerprint != truncated.advisory_fingerprint
    elif slot == 5:
        workspace = WorkspaceId.COMPANY if variant % 2 else WorkspaceId.PERSONAL
        task = make_task(workspace_id=workspace)
        first, first_retrieval = bind(task=task, tiers=(0,))
        second, second_retrieval = bind(task=task, tiers=(0,))
        assert first == second
        assert first_retrieval.queries == second_retrieval.queries
    elif slot == 6:
        retrieval = StubRetrieval(lambda query: make_set(query, (0, 1, 3)))
        binder = CognitiveTrustedExperienceRuntimeBinder(retrieval)
        task = make_task()
        before = dict(vars(retrieval))
        first = binder.bind(task=task)
        second = binder.bind(task=task)
        assert first == second
        assert vars(binder) == {"_retrieval_service": retrieval}
        assert retrieval.calls == before["calls"] + 2
    else:
        left = CognitiveTrustedExperienceRuntimeBinder(
            StubRetrieval(error=RuntimeError(f"x-{variant}"))
        ).bind(task=make_task())
        right = CognitiveTrustedExperienceRuntimeBinder(
            StubRetrieval(error=ValueError(f"y-{variant}"))
        ).bind(task=make_task())
        assert left == right
        assert left.binding_status == "unavailable"


@pytest.mark.parametrize(
    "case",
    range(1, 49),
    ids=[f"R{i:02d}" for i in range(1, 49)],
)
def test_d150_reproducibility_matrix(case: int) -> None:
    run_case(case)
