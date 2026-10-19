from __future__ import annotations

from dataclasses import replace

import pytest

from app.contracts.cognitive_trusted_experience_reasoning import (
    compute_cognitive_trusted_experience_reasoning_fingerprint,
)
from app.contracts.workspace import WorkspaceId
from app.services.cognitive_trusted_experience_reasoning import (
    CognitiveTrustedExperienceReasoningInfluenceService,
)
from tests.test_d153_cognitive_trusted_experience_reasoning import projection


def evaluate(source):
    return CognitiveTrustedExperienceReasoningInfluenceService.evaluate(
        projection=source
    )


def run_case(case: int) -> None:
    slot = (case - 1) % 8
    variant = (case - 1) // 8
    if slot == 0:
        source = projection(kind="projected")
        assert evaluate(source) == evaluate(source)
    elif slot == 1:
        kind = ("projected", "empty", "restricted", "unavailable")[variant % 4]
        assert evaluate(projection(kind=kind)) == evaluate(projection(kind=kind))
    elif slot == 2:
        personal = evaluate(projection(workspace_id=WorkspaceId.PERSONAL))
        company = evaluate(projection(workspace_id=WorkspaceId.COMPANY))
        assert personal.reasoning_fingerprint != company.reasoning_fingerprint
    elif slot == 3:
        result = evaluate(projection(kind="empty"))
        assert result.reasoning_status == "inactive" and result.directive_id is None
    elif slot == 4:
        result = evaluate(projection(kind="restricted"))
        assert result.reasoning_status == "inactive" and result.directive_id is None
    elif slot == 5:
        result = evaluate(projection(kind="projected"))
        expected = compute_cognitive_trusted_experience_reasoning_fingerprint(
            contract_version=result.contract_version,
            reference_baseline=result.reference_baseline,
            reasoning_policy=result.reasoning_policy,
            workspace_id=result.workspace_id,
            source_projection_status=result.source_projection_status,
            source_projection_fingerprint=result.source_projection_fingerprint,
            reasoning_status=result.reasoning_status,
            directive_id=result.directive_id,
        )
        assert result.reasoning_fingerprint == expected
    elif slot == 6:
        first = evaluate(projection(kind="projected"))
        assert first == replace(first)
    else:
        statuses = tuple(
            evaluate(projection(kind=kind)).reasoning_status
            for kind in ("projected", "empty", "restricted", "unavailable")
        )
        assert statuses == ("active", "inactive", "inactive", "inactive")


@pytest.mark.parametrize(
    "case", range(1, 49), ids=[f"R{i:02d}" for i in range(1, 49)]
)
def test_d153_reproducibility_matrix(case: int) -> None:
    run_case(case)
