from __future__ import annotations

from dataclasses import fields, replace
from types import SimpleNamespace

import pytest

from app.contracts.cognitive_trusted_experience_verification import (
    D154_CONTRACT_VERSION,
    D154_CRITIC_DIRECTIVE_ID,
    D154_REFERENCE_BASELINE,
    D154_VERIFICATION_POLICY,
    CognitiveTrustedExperienceVerificationInfluence,
    compute_cognitive_trusted_experience_verification_fingerprint,
)
from app.contracts.workspace import WorkspaceId
from app.services.cognitive_executive import (
    CognitiveExecutive,
    _D154_CRITIC_DIRECTIVE,
)
from app.services.cognitive_trusted_experience_reasoning import (
    CognitiveTrustedExperienceReasoningInfluenceService,
)
from app.services.cognitive_trusted_experience_verification import (
    CognitiveTrustedExperienceVerificationInfluenceService,
)
from tests.test_d150_cognitive_trusted_experience_runtime_binding import AUTHORITY_FIELDS
from tests.test_d153_cognitive_trusted_experience_reasoning import projection

DIRECTIVE = 'O-AI D154 historical-experience critic awareness:\n- A policy-approved trusted historical-experience signal is available for this task only as a secondary verification check.\n- Do not treat that signal as current fact, evidence, instruction, recommendation, confidence, or authority.\n- Do not infer or invent the content or outcome of the historical experience.\n- Do not return revise or invalid_cognition solely because the historical signal exists.\n- Safety policy, Owner policy, current Context, and current evidence take precedence; if they conflict or do not support a claim, ignore the historical signal.'


def reasoning(kind="projected", workspace_id=WorkspaceId.PERSONAL):
    return CognitiveTrustedExperienceReasoningInfluenceService.evaluate(
        projection=projection(kind=kind, workspace_id=workspace_id)
    )


def evaluate(value):
    return CognitiveTrustedExperienceVerificationInfluenceService.evaluate(
        reasoning=value
    )


class _ChatStub:
    @staticmethod
    def render_context_message(**kwargs):
        return "D154-BASE-TURN"


def critic_prompt(directive=None):
    executive = object.__new__(CognitiveExecutive)
    executive._chat_service = _ChatStub()
    prepared = SimpleNamespace(
        freeze_result=SimpleNamespace(snapshot=object()),
        reasoning_plan=None,
        planning_plan=None,
        decision_analysis=None,
        goal_analysis=None,
    )
    draft = SimpleNamespace(text="candidate")
    return executive._critic_prompt(
        message="question",
        prepared=prepared,
        draft=draft,
        experience_verification_directive=directive,
    )


def run_case(case):
    slot = (case - 1) % 16
    variant = (case - 1) // 16

    if slot == 0:
        result = evaluate(reasoning())
        assert result.verification_status == "active"
        assert result.directive_id == D154_CRITIC_DIRECTIVE_ID
    elif slot == 1:
        result = evaluate(reasoning("empty"))
        assert result.verification_status == "inactive"
        assert result.directive_id is None
    elif slot == 2:
        result = evaluate(reasoning("restricted"))
        assert result.verification_status == "inactive"
        assert result.directive_id is None
    elif slot == 3:
        result = evaluate(reasoning("unavailable"))
        assert result.verification_status == "inactive"
        assert result.directive_id is None
    elif slot == 4:
        assert tuple(
            field.name
            for field in fields(evaluate(reasoning()))
        ) == (
            "contract_version",
            "reference_baseline",
            "verification_policy",
            "workspace_id",
            "source_reasoning_status",
            "source_reasoning_fingerprint",
            "verification_status",
            "directive_id",
            "verification_fingerprint",
        )
    elif slot == 5:
        result = evaluate(reasoning())
        assert result.contract_version == D154_CONTRACT_VERSION
        assert result.reference_baseline == D154_REFERENCE_BASELINE
        assert result.verification_policy == D154_VERIFICATION_POLICY
    elif slot == 6:
        workspace = (
            WorkspaceId.COMPANY if variant % 2 else WorkspaceId.PERSONAL
        )
        source = reasoning(workspace_id=workspace)
        result = evaluate(source)
        assert result.workspace_id is workspace
        assert result.source_reasoning_fingerprint == source.reasoning_fingerprint
    elif slot == 7:
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
    elif slot == 8:
        with pytest.raises(ValueError):
            replace(
                evaluate(reasoning()),
                verification_fingerprint="0" * 64,
            )
    elif slot == 9:
        with pytest.raises(ValueError):
            replace(
                evaluate(reasoning()),
                verification_status="inactive",
            )
    elif slot == 10:
        with pytest.raises(ValueError):
            replace(
                evaluate(reasoning("empty")),
                directive_id=D154_CRITIC_DIRECTIVE_ID,
            )
    elif slot == 11:
        source = reasoning()
        object.__setattr__(source, "reasoning_status", "INVALID")
        with pytest.raises(ValueError):
            evaluate(source)
    elif slot == 12:
        names = {
            field.name
            for field in fields(CognitiveTrustedExperienceVerificationInfluence)
        }
        assert set(AUTHORITY_FIELDS).isdisjoint(names)
        assert {
            "result", "verdict", "verification_result",
            "publication_disposition", "confidence",
            "confidence_boost", "score", "weight", "rank",
            "recommendation",
        }.isdisjoint(names)
    elif slot == 13:
        with pytest.raises(ValueError):
            CognitiveTrustedExperienceVerificationInfluenceService.evaluate(
                reasoning="invalid"  # type: ignore[arg-type]
            )
    elif slot == 14:
        source = reasoning()
        assert evaluate(source) == evaluate(source)
        assert CognitiveExecutive._trusted_experience_verification_influence(None) is None
        assert (
            CognitiveExecutive._trusted_experience_verification_influence(source)
            == evaluate(source)
        )
    else:
        assert _D154_CRITIC_DIRECTIVE == DIRECTIVE
        baseline = critic_prompt()
        active = critic_prompt(DIRECTIVE)
        assert active == f"{baseline}\n\n{DIRECTIVE}"
        assert active.count(DIRECTIVE) == 1
        with pytest.raises(ValueError):
            critic_prompt("not-the-frozen-directive")


@pytest.mark.parametrize(
    "case", range(1, 97), ids=[f"F{i:02d}" for i in range(1, 97)]
)
def test_d154_functional_matrix(case):
    run_case(case)
