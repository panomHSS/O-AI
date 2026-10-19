from __future__ import annotations

from dataclasses import replace

import pytest

from app.contracts.workspace import WorkspaceId
from app.contracts.cognitive_trusted_experience_context_projection import (
    compute_cognitive_trusted_experience_projection_fingerprint,
)
from app.services.cognitive_trusted_experience_consumption import (
    CognitiveTrustedExperienceConsumptionPolicyEvaluator,
)
from app.services.cognitive_trusted_experience_context_projection import (
    CognitiveTrustedExperienceContextProjectionService,
)
from tests.test_d150_cognitive_trusted_experience_runtime_binding import (
    bind,
    make_task,
)


def source_decision(
    *,
    tiers: tuple[int, ...] = (),
    truncated: bool = False,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
):
    binding, _ = bind(
        task=make_task(workspace_id=workspace_id),
        tiers=tiers,
        truncated=truncated,
    )
    return CognitiveTrustedExperienceConsumptionPolicyEvaluator.evaluate(
        binding=binding
    )


def project(value):
    return CognitiveTrustedExperienceContextProjectionService.project(
        decision=value
    )


def run_case(case: int) -> None:
    slot = (case - 1) % 8
    variant = (case - 1) // 8

    if slot == 0:
        source = source_decision(tiers=(variant % 4,))
        assert project(source) == project(source)
    elif slot == 1:
        tiers = (0, 1) * 8 if variant % 2 else (0, 1)
        left = source_decision(tiers=tiers, truncated=bool(variant % 2))
        right = source_decision(tiers=tiers, truncated=bool(variant % 2))
        assert project(left) == project(right)
    elif slot == 2:
        left = project(source_decision())
        right = project(source_decision())
        assert left == right
        assert left.projection_status == "empty"
    elif slot == 3:
        source = source_decision(tiers=(1,) * 16, truncated=True)
        first = project(source)
        second = project(source)
        assert first == second
        assert first.restriction_reasons == (
            "partial_relevance",
            "truncated_source",
        )
    elif slot == 4:
        personal = project(
            source_decision(
                tiers=(0,),
                workspace_id=WorkspaceId.PERSONAL,
            )
        )
        company = project(
            source_decision(
                tiers=(0,),
                workspace_id=WorkspaceId.COMPANY,
            )
        )
        assert personal.workspace_id is WorkspaceId.PERSONAL
        assert company.workspace_id is WorkspaceId.COMPANY
        assert personal.projection_fingerprint != company.projection_fingerprint
    elif slot == 5:
        one = project(source_decision(tiers=(0,)))
        many = project(source_decision(tiers=(0,) * (variant + 2)))
        assert one.projection_status == many.projection_status == "projected"
        assert one.restriction_reasons == many.restriction_reasons == ()
    elif slot == 6:
        result = project(
            source_decision(
                tiers=(3,) * (16 if variant % 2 else 1),
                truncated=bool(variant % 2),
            )
        )
        expected = compute_cognitive_trusted_experience_projection_fingerprint(
            contract_version=result.contract_version,
            reference_baseline=result.reference_baseline,
            projection_policy=result.projection_policy,
            workspace_id=result.workspace_id,
            source_consumption_status=result.source_consumption_status,
            source_policy_fingerprint=result.source_policy_fingerprint,
            source_advisory_status=result.source_advisory_status,
            source_truncated=result.source_truncated,
            projection_status=result.projection_status,
            restriction_reasons=result.restriction_reasons,
        )
        assert expected == result.projection_fingerprint
    else:
        first = project(source_decision(tiers=(2,)))
        cloned = replace(first)
        assert first == cloned
        assert first.projection_fingerprint == cloned.projection_fingerprint


@pytest.mark.parametrize(
    "case",
    range(1, 49),
    ids=[f"R{i:02d}" for i in range(1, 49)],
)
def test_d152_reproducibility_matrix(case: int) -> None:
    run_case(case)
