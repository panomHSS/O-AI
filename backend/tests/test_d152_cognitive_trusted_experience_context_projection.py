from __future__ import annotations

from dataclasses import fields, replace

import pytest

from app.contracts.cognitive_trusted_experience_consumption import (
    CognitiveTrustedExperienceConsumptionDecision,
)
from app.contracts.cognitive_trusted_experience_context_projection import (
    D152_CONTRACT_VERSION,
    D152_PROJECTION_POLICY,
    D152_REFERENCE_BASELINE,
    CognitiveTrustedExperienceContextProjection,
    compute_cognitive_trusted_experience_projection_fingerprint,
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
from tests.test_d150_cognitive_trusted_experience_runtime_binding import (
    AUTHORITY_FIELDS,
    bind,
    make_task,
)


def decision(
    *,
    tiers: tuple[int, ...] = (),
    truncated: bool = False,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
) -> CognitiveTrustedExperienceConsumptionDecision:
    binding, _ = bind(
        task=make_task(workspace_id=workspace_id),
        tiers=tiers,
        truncated=truncated,
    )
    return CognitiveTrustedExperienceConsumptionPolicyEvaluator.evaluate(
        binding=binding
    )


def denied_decision() -> CognitiveTrustedExperienceConsumptionDecision:
    binding = CognitiveTrustedExperienceRuntimeBinding.unavailable(
        make_task().envelope.workspace_id
    )
    return CognitiveTrustedExperienceConsumptionPolicyEvaluator.evaluate(
        binding=binding
    )


def project(
    value: CognitiveTrustedExperienceConsumptionDecision,
) -> CognitiveTrustedExperienceContextProjection:
    return CognitiveTrustedExperienceContextProjectionService.project(
        decision=value
    )


def run_case(case: int) -> None:
    slot = (case - 1) % 16
    variant = (case - 1) // 16

    if slot == 0:
        result = project(denied_decision())
        assert result.projection_status == "unavailable"
        assert result.restriction_reasons == ("binding_unavailable",)
        assert result.source_advisory_status is None
        assert result.source_truncated is None
    elif slot == 1:
        source = decision()
        result = project(source)
        assert source.consumption_status == "allowed"
        assert source.source_advisory_status == "no_evidence"
        assert result.projection_status == "empty"
        assert result.restriction_reasons == ()
    elif slot == 2:
        source = decision(tiers=(0,) * (variant + 1))
        result = project(source)
        assert source.source_advisory_status == "exact_match"
        assert result.projection_status == "projected"
        assert result.restriction_reasons == ()
    elif slot == 3:
        result = project(decision(tiers=(0,) * 16, truncated=True))
        assert result.projection_status == "restricted"
        assert result.restriction_reasons == ("truncated_source",)
    elif slot == 4:
        result = project(decision(tiers=(1,) * (variant + 1)))
        assert result.source_advisory_status == "partial_match"
        assert result.projection_status == "restricted"
        assert result.restriction_reasons == ("partial_relevance",)
    elif slot == 5:
        result = project(decision(tiers=(2,) * 16, truncated=True))
        assert result.restriction_reasons == (
            "partial_relevance",
            "truncated_source",
        )
    elif slot == 6:
        result = project(
            decision(
                tiers=(3,) * (16 if variant % 2 else 1),
                truncated=bool(variant % 2),
            )
        )
        expected = (
            ("task_only_relevance", "truncated_source")
            if variant % 2
            else ("task_only_relevance",)
        )
        assert result.projection_status == "restricted"
        assert result.restriction_reasons == expected
    elif slot == 7:
        result = project(
            decision(
                tiers=((0, 1) * 8 if variant % 2 else (0, 1)),
                truncated=bool(variant % 2),
            )
        )
        expected = (
            ("mixed_relevance", "truncated_source")
            if variant % 2
            else ("mixed_relevance",)
        )
        assert result.source_advisory_status == "mixed_relevance"
        assert result.restriction_reasons == expected
    elif slot == 8:
        result = project(decision(tiers=(0,)))
        names = tuple(field.name for field in fields(result))
        assert names == (
            "contract_version",
            "reference_baseline",
            "projection_policy",
            "workspace_id",
            "source_consumption_status",
            "source_policy_fingerprint",
            "source_advisory_status",
            "source_truncated",
            "projection_status",
            "restriction_reasons",
            "projection_fingerprint",
        )
    elif slot == 9:
        result = project(decision(tiers=(variant % 4,)))
        names = {field.name for field in fields(result)}
        assert {
            "source_selected_count", "best_relevance_tier",
            "authorized_adapter_id", "authorized_model_id",
            "authorized_profile_id", "preferred_model", "preferred_adapter",
            "preferred_profile", "score", "rank", "weight", "confidence",
            "confidence_boost",
        }.isdisjoint(names)
    elif slot == 10:
        result = project(decision(tiers=(0, 1) * 8, truncated=True))
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
        assert result.projection_fingerprint == expected
    elif slot == 11:
        workspace = WorkspaceId.COMPANY if variant % 2 else WorkspaceId.PERSONAL
        source = decision(tiers=(0,), workspace_id=workspace)
        result = project(source)
        assert result.workspace_id is workspace
        assert result.source_policy_fingerprint == source.policy_fingerprint
    elif slot == 12:
        source = decision(tiers=(0,))
        object.__setattr__(source, "consumption_status", "INVALID")
        with pytest.raises(ValueError):
            project(source)
    elif slot == 13:
        result = project(decision(tiers=(0,)))
        with pytest.raises(ValueError):
            replace(result, projection_fingerprint="0" * 64)
    elif slot == 14:
        result = project(decision(tiers=(1,) * 16, truncated=True))
        with pytest.raises(ValueError):
            replace(
                result,
                restriction_reasons=("truncated_source", "partial_relevance"),
            )
    else:
        result = project(decision(tiers=(0,)))
        assert result.contract_version == D152_CONTRACT_VERSION
        assert result.reference_baseline == D152_REFERENCE_BASELINE
        assert result.projection_policy == D152_PROJECTION_POLICY
        names = {field.name for field in fields(result)}
        assert set(AUTHORITY_FIELDS).isdisjoint(names)


@pytest.mark.parametrize(
    "case",
    range(1, 97),
    ids=[f"F{i:02d}" for i in range(1, 97)],
)
def test_d152_functional_matrix(case: int) -> None:
    run_case(case)
