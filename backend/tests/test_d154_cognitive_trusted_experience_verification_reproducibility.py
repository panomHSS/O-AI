from __future__ import annotations

from dataclasses import replace

import pytest

from app.contracts.cognitive_trusted_experience_verification import (
    compute_cognitive_trusted_experience_verification_fingerprint,
)
from app.contracts.workspace import WorkspaceId
from tests.test_d154_cognitive_trusted_experience_verification import (
    DIRECTIVE,
    critic_prompt,
    evaluate,
    reasoning,
)


def run_case(case):
    slot = (case - 1) % 8
    variant = (case - 1) // 8

    if slot == 0:
        source = reasoning()
        assert evaluate(source) == evaluate(source)
    elif slot == 1:
        kind = ("projected", "empty", "restricted", "unavailable")[variant % 4]
        assert evaluate(reasoning(kind)) == evaluate(reasoning(kind))
    elif slot == 2:
        personal = evaluate(
            reasoning(workspace_id=WorkspaceId.PERSONAL)
        )
        company = evaluate(
            reasoning(workspace_id=WorkspaceId.COMPANY)
        )
        assert personal.verification_fingerprint != company.verification_fingerprint
    elif slot == 3:
        first = critic_prompt(DIRECTIVE)
        second = critic_prompt(DIRECTIVE)
        assert first == second
        assert first.count(DIRECTIVE) == 1
    elif slot == 4:
        assert critic_prompt() == critic_prompt()
        assert DIRECTIVE not in critic_prompt()
    elif slot == 5:
        result = evaluate(reasoning())
        expected = compute_cognitive_trusted_experience_verification_fingerprint(
            contract_version=result.contract_version,
            reference_baseline=result.reference_baseline,
            verification_policy=result.verification_policy,
            workspace_id=result.workspace_id,
            source_reasoning_status=result.source_reasoning_status,
            source_reasoning_fingerprint=result.source_reasoning_fingerprint,
            verification_status=result.verification_status,
            directive_id=result.directive_id,
        )
        assert result.verification_fingerprint == expected
    elif slot == 6:
        result = evaluate(reasoning())
        assert result == replace(result)
    else:
        assert tuple(
            evaluate(reasoning(kind)).verification_status
            for kind in ("projected", "empty", "restricted", "unavailable")
        ) == ("active", "inactive", "inactive", "inactive")


@pytest.mark.parametrize(
    "case", range(1, 49), ids=[f"R{i:02d}" for i in range(1, 49)]
)
def test_d154_reproducibility_matrix(case):
    run_case(case)
