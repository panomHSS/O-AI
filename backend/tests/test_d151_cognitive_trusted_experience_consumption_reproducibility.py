from __future__ import annotations

from dataclasses import replace

import pytest

from app.contracts.cognitive_trusted_experience_consumption import (
    compute_cognitive_trusted_experience_consumption_policy_fingerprint,
)
from app.contracts.workspace import WorkspaceId
from app.services.cognitive_trusted_experience_consumption import (
    CognitiveTrustedExperienceConsumptionPolicyEvaluator,
)
from tests.test_d150_cognitive_trusted_experience_runtime_binding import (
    bind,
    make_task,
)


def evaluate(binding):
    return CognitiveTrustedExperienceConsumptionPolicyEvaluator.evaluate(
        binding=binding
    )


def run_case(case: int) -> None:
    slot = (case - 1) % 8
    variant = (case - 1) // 8

    if slot == 0:
        binding, _ = bind(tiers=(variant % 4,))
        assert evaluate(binding) == evaluate(binding)
    elif slot == 1:
        tiers = (0, 1) * 8 if variant % 2 else (0, 1)
        left, _ = bind(tiers=tiers, truncated=bool(variant % 2))
        right, _ = bind(tiers=tiers, truncated=bool(variant % 2))
        assert evaluate(left) == evaluate(right)
    elif slot == 2:
        left, _ = bind()
        right, _ = bind()
        assert evaluate(left) == evaluate(right)
        assert evaluate(left).consumption_status == "allowed"
    elif slot == 3:
        binding, _ = bind(tiers=(1,) * 16, truncated=True)
        result = evaluate(binding)
        assert result.restriction_reasons == (
            "partial_relevance",
            "truncated_source",
        )
    elif slot == 4:
        personal, _ = bind(
            task=make_task(workspace_id=WorkspaceId.PERSONAL),
            tiers=(0,),
        )
        company, _ = bind(
            task=make_task(workspace_id=WorkspaceId.COMPANY),
            tiers=(0,),
        )
        left = evaluate(personal)
        right = evaluate(company)
        assert left.workspace_id is WorkspaceId.PERSONAL
        assert right.workspace_id is WorkspaceId.COMPANY
        assert left.policy_fingerprint != right.policy_fingerprint
    elif slot == 5:
        one, _ = bind(tiers=(0,))
        many, _ = bind(tiers=(0,) * (variant + 2))
        left = evaluate(one)
        right = evaluate(many)
        assert left.consumption_status == right.consumption_status == "allowed"
        assert left.restriction_reasons == right.restriction_reasons == ()
    elif slot == 6:
        binding, _ = bind(tiers=(3,) * (16 if variant % 2 else 1), truncated=bool(variant % 2))
        result = evaluate(binding)
        expected = compute_cognitive_trusted_experience_consumption_policy_fingerprint(
            contract_version=result.contract_version,
            reference_baseline=result.reference_baseline,
            consumption_policy=result.consumption_policy,
            workspace_id=result.workspace_id,
            source_binding_status=result.source_binding_status,
            source_advisory_status=result.source_advisory_status,
            source_advisory_fingerprint=result.source_advisory_fingerprint,
            source_truncated=result.source_truncated,
            consumption_status=result.consumption_status,
            restriction_reasons=result.restriction_reasons,
        )
        assert expected == result.policy_fingerprint
    else:
        binding, _ = bind(tiers=(2,))
        first = evaluate(binding)
        cloned = replace(first)
        assert first == cloned
        assert first.policy_fingerprint == cloned.policy_fingerprint


@pytest.mark.parametrize(
    "case",
    range(1, 49),
    ids=[f"R{i:02d}" for i in range(1, 49)],
)
def test_d151_reproducibility_matrix(case: int) -> None:
    run_case(case)
