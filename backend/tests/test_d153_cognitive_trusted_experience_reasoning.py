from __future__ import annotations

from dataclasses import fields, replace

import pytest

from app.contracts.cognitive_trusted_experience_context_projection import (
    CognitiveTrustedExperienceContextProjection,
)
from app.contracts.cognitive_trusted_experience_reasoning import (
    D153_CONTRACT_VERSION,
    D153_PRIMARY_REASONING_DIRECTIVE_ID,
    D153_REASONING_POLICY,
    D153_REFERENCE_BASELINE,
    CognitiveTrustedExperienceReasoningInfluence,
    compute_cognitive_trusted_experience_reasoning_fingerprint,
)
from app.contracts.cognitive_trusted_experience_runtime_binding import (
    CognitiveTrustedExperienceRuntimeBinding,
)
from app.contracts.workspace import WorkspaceId
from app.services.cognitive_trusted_experience_consumption import (
    CognitiveTrustedExperienceConsumptionPolicyEvaluator,
)
from app.services.cognitive_trusted_experience_context_projection import (
    CognitiveTrustedExperienceContextProjectionService,
)
from app.services.cognitive_trusted_experience_reasoning import (
    CognitiveTrustedExperienceReasoningInfluenceService,
)
from tests.test_d150_cognitive_trusted_experience_runtime_binding import (
    AUTHORITY_FIELDS,
    bind,
    make_task,
)


def projection(
    *,
    kind: str = "projected",
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
) -> CognitiveTrustedExperienceContextProjection:
    if kind == "unavailable":
        binding = CognitiveTrustedExperienceRuntimeBinding.unavailable(workspace_id)
    elif kind == "empty":
        binding, _ = bind(task=make_task(workspace_id=workspace_id), tiers=())
    elif kind == "projected":
        binding, _ = bind(task=make_task(workspace_id=workspace_id), tiers=(0,))
    elif kind == "restricted":
        binding, _ = bind(task=make_task(workspace_id=workspace_id), tiers=(1,))
    else:
        raise AssertionError(kind)
    decision = CognitiveTrustedExperienceConsumptionPolicyEvaluator.evaluate(
        binding=binding
    )
    return CognitiveTrustedExperienceContextProjectionService.project(
        decision=decision
    )


def evaluate(source: CognitiveTrustedExperienceContextProjection):
    return CognitiveTrustedExperienceReasoningInfluenceService.evaluate(
        projection=source
    )


def run_case(case: int) -> None:
    slot = (case - 1) % 16
    variant = (case - 1) // 16
    if slot == 0:
        result = evaluate(projection(kind="projected"))
        assert result.reasoning_status == "active"
        assert result.directive_id == D153_PRIMARY_REASONING_DIRECTIVE_ID
    elif slot == 1:
        result = evaluate(projection(kind="empty"))
        assert result.reasoning_status == "inactive" and result.directive_id is None
    elif slot == 2:
        result = evaluate(projection(kind="restricted"))
        assert result.reasoning_status == "inactive" and result.directive_id is None
    elif slot == 3:
        result = evaluate(projection(kind="unavailable"))
        assert result.reasoning_status == "inactive" and result.directive_id is None
    elif slot == 4:
        result = evaluate(projection())
        assert tuple(field.name for field in fields(result)) == (
            "contract_version",
            "reference_baseline",
            "reasoning_policy",
            "workspace_id",
            "source_projection_status",
            "source_projection_fingerprint",
            "reasoning_status",
            "directive_id",
            "reasoning_fingerprint",
        )
    elif slot == 5:
        result = evaluate(projection())
        assert result.contract_version == D153_CONTRACT_VERSION
        assert result.reference_baseline == D153_REFERENCE_BASELINE
        assert result.reasoning_policy == D153_REASONING_POLICY
    elif slot == 6:
        workspace = WorkspaceId.COMPANY if variant % 2 else WorkspaceId.PERSONAL
        source = projection(workspace_id=workspace)
        result = evaluate(source)
        assert result.workspace_id is workspace
        assert result.source_projection_fingerprint == source.projection_fingerprint
    elif slot == 7:
        result = evaluate(projection())
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
    elif slot == 8:
        with pytest.raises(ValueError):
            replace(evaluate(projection()), reasoning_fingerprint="0" * 64)
    elif slot == 9:
        with pytest.raises(ValueError):
            replace(evaluate(projection()), reasoning_status="inactive")
    elif slot == 10:
        with pytest.raises(ValueError):
            replace(
                evaluate(projection(kind="restricted")),
                directive_id=D153_PRIMARY_REASONING_DIRECTIVE_ID,
            )
    elif slot == 11:
        source = projection()
        object.__setattr__(source, "projection_status", "INVALID")
        with pytest.raises(ValueError):
            evaluate(source)
    elif slot == 12:
        names = {f.name for f in fields(CognitiveTrustedExperienceReasoningInfluence)}
        assert set(AUTHORITY_FIELDS).isdisjoint(names)
        assert {
            "confidence", "confidence_boost", "score", "weight", "rank",
            "recommendation", "preferred_model", "preferred_adapter",
            "preferred_profile",
        }.isdisjoint(names)
    elif slot == 13:
        with pytest.raises(ValueError):
            CognitiveTrustedExperienceReasoningInfluenceService.evaluate(
                projection="invalid"  # type: ignore[arg-type]
            )
    elif slot == 14:
        source = projection()
        assert evaluate(source) == evaluate(source)
    else:
        kind = ("projected", "empty", "restricted", "unavailable")[variant % 4]
        source = projection(kind=kind)
        result = evaluate(source)
        assert result.source_projection_status == source.projection_status
        assert (result.reasoning_status == "active") is (
            source.projection_status == "projected"
        )


@pytest.mark.parametrize(
    "case", range(1, 97), ids=[f"F{i:02d}" for i in range(1, 97)]
)
def test_d153_functional_matrix(case: int) -> None:
    run_case(case)
