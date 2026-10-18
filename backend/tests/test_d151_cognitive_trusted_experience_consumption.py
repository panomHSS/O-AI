from __future__ import annotations

from dataclasses import fields, replace

import pytest

from app.contracts.cognitive_trusted_experience_consumption import (
    D151_CONSUMPTION_POLICY,
    D151_CONTRACT_VERSION,
    D151_REFERENCE_BASELINE,
    CognitiveTrustedExperienceConsumptionDecision,
    compute_cognitive_trusted_experience_consumption_policy_fingerprint,
)
from app.contracts.cognitive_trusted_experience_runtime_binding import (
    CognitiveTrustedExperienceRuntimeBinding,
)
from app.contracts.workspace import WorkspaceId
from app.services.cognitive_trusted_experience_consumption import (
    CognitiveTrustedExperienceConsumptionPolicyEvaluator,
)
from tests.test_d150_cognitive_trusted_experience_runtime_binding import (
    AUTHORITY_FIELDS,
    bind,
    make_task,
)


def evaluate(binding: CognitiveTrustedExperienceRuntimeBinding):
    return CognitiveTrustedExperienceConsumptionPolicyEvaluator.evaluate(
        binding=binding
    )


def policy(
    *,
    tiers: tuple[int, ...] = (),
    truncated: bool = False,
):
    binding, _ = bind(tiers=tiers, truncated=truncated)
    return evaluate(binding), binding


def run_case(case: int) -> None:
    slot = (case - 1) % 16
    variant = (case - 1) // 16

    if slot == 0:
        binding = CognitiveTrustedExperienceRuntimeBinding.unavailable(
            make_task().envelope.workspace_id
        )
        result = evaluate(binding)
        assert result.consumption_status == "denied"
        assert result.restriction_reasons == ("binding_unavailable",)
        assert result.source_advisory_status is None
        assert result.source_advisory_fingerprint is None
        assert result.source_truncated is None
    elif slot == 1:
        result, _ = policy()
        assert result.source_advisory_status == "no_evidence"
        assert result.consumption_status == "allowed"
        assert result.restriction_reasons == ()
    elif slot == 2:
        result, _ = policy(tiers=(0,) * (variant + 1))
        assert result.source_advisory_status == "exact_match"
        assert result.consumption_status == "allowed"
        assert result.restriction_reasons == ()
    elif slot == 3:
        result, _ = policy(tiers=(0,) * 16, truncated=True)
        assert result.consumption_status == "restricted"
        assert result.restriction_reasons == ("truncated_source",)
    elif slot == 4:
        result, _ = policy(tiers=(1,) * (variant + 1))
        assert result.source_advisory_status == "partial_match"
        assert result.consumption_status == "restricted"
        assert result.restriction_reasons == ("partial_relevance",)
    elif slot == 5:
        result, _ = policy(tiers=(2,) * 16, truncated=True)
        assert result.source_advisory_status == "partial_match"
        assert result.restriction_reasons == (
            "partial_relevance",
            "truncated_source",
        )
    elif slot == 6:
        result, _ = policy(tiers=(3,) * (16 if variant % 2 else 1), truncated=bool(variant % 2))
        expected = (
            ("task_only_relevance", "truncated_source")
            if variant % 2
            else ("task_only_relevance",)
        )
        assert result.consumption_status == "restricted"
        assert result.restriction_reasons == expected
    elif slot == 7:
        result, _ = policy(tiers=((0, 1) * 8 if variant % 2 else (0, 1)), truncated=bool(variant % 2))
        expected = (
            ("mixed_relevance", "truncated_source")
            if variant % 2
            else ("mixed_relevance",)
        )
        assert result.source_advisory_status == "mixed_relevance"
        assert result.restriction_reasons == expected
    elif slot == 8:
        result, _ = policy(tiers=(0,))
        names = tuple(field.name for field in fields(result))
        assert names == (
            "contract_version",
            "reference_baseline",
            "consumption_policy",
            "workspace_id",
            "source_binding_status",
            "source_advisory_status",
            "source_advisory_fingerprint",
            "source_truncated",
            "consumption_status",
            "restriction_reasons",
            "policy_fingerprint",
        )
    elif slot == 9:
        result, _ = policy(tiers=(variant % 4,))
        names = {field.name for field in fields(result)}
        assert "source_selected_count" not in names
        assert "best_relevance_tier" not in names
        assert "confidence" not in names
        assert "score" not in names
        assert "weight" not in names
    elif slot == 10:
        result, binding = policy(tiers=(0, 1) * 8, truncated=True)
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
        assert result.source_advisory_fingerprint == binding.advisory_fingerprint
    elif slot == 11:
        workspace = WorkspaceId.COMPANY if variant % 2 else WorkspaceId.PERSONAL
        binding, _ = bind(task=make_task(workspace_id=workspace), tiers=(0,))
        result = evaluate(binding)
        assert result.workspace_id is workspace
    elif slot == 12:
        binding, _ = bind(tiers=(0,))
        object.__setattr__(binding, "advisory_status", "INVALID")
        with pytest.raises(ValueError):
            evaluate(binding)
    elif slot == 13:
        result, _ = policy(tiers=(0,))
        with pytest.raises(ValueError):
            replace(result, policy_fingerprint="0" * 64)
    elif slot == 14:
        result, _ = policy(tiers=(1,) * 16, truncated=True)
        assert result.restriction_reasons == (
            "partial_relevance",
            "truncated_source",
        )
        with pytest.raises(ValueError):
            replace(
                result,
                restriction_reasons=(
                    "truncated_source",
                    "partial_relevance",
                ),
            )
    else:
        result, _ = policy(tiers=(0,))
        assert result.contract_version == D151_CONTRACT_VERSION
        assert result.reference_baseline == D151_REFERENCE_BASELINE
        assert result.consumption_policy == D151_CONSUMPTION_POLICY
        names = {field.name for field in fields(result)}
        assert set(AUTHORITY_FIELDS).isdisjoint(names)


@pytest.mark.parametrize(
    "case",
    range(1, 97),
    ids=[f"F{i:02d}" for i in range(1, 97)],
)
def test_d151_functional_matrix(case: int) -> None:
    run_case(case)
