"""D144 immutable owner-controlled cognitive rollout contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

D144_REFERENCE_BASELINE = "9f6fa3557e3c9b91a3549c1175b8273c24fad20c"
D144_ROLLOUT_BUCKET_COUNT = 10_000
D144_RATE_SCALE_BPS = 10_000
D144_ROLLOUT_DOMAIN = "O-AI:D144:COGNITIVE-ROLLOUT:V1"
D144_SELECTION_SCOPE = "d140_cognitive_eligible_turns"
D144_SELECTION_STRATEGY = "sha256_server_bound_conversation_uuid_v1"

CognitiveRuntimeRolloutStage: TypeAlias = Literal[
    "control_only", "canary_1", "canary_5", "canary_10",
    "canary_25", "canary_50", "full",
]
CognitiveRuntimeRolloutDisposition: TypeAlias = Literal[
    "not_applicable", "control", "cognitive",
]
CognitiveRuntimeRolloutReasonCode: TypeAlias = Literal[
    "cognitive_runtime_disabled",
    "not_cognitive_eligible",
    "rollout_control_only",
    "rollout_bucket_control",
    "rollout_bucket_cognitive",
    "rollout_full",
    "missing_conversation_identity",
    "invalid_rollout_stage",
]

D144_STAGE_BPS: dict[str, int] = {
    "control_only": 0,
    "canary_1": 100,
    "canary_5": 500,
    "canary_10": 1_000,
    "canary_25": 2_500,
    "canary_50": 5_000,
    "full": 10_000,
}


def rollout_bps_for_stage(stage: object) -> int | None:
    if type(stage) is not str:
        return None
    return D144_STAGE_BPS.get(stage)


@dataclass(frozen=True, slots=True)
class CognitiveRuntimeRolloutDecision:
    """One bounded D144 exposure decision; never control authority."""

    disposition: CognitiveRuntimeRolloutDisposition
    reason_code: CognitiveRuntimeRolloutReasonCode
    stage: CognitiveRuntimeRolloutStage | None
    rollout_bps: int | None
    reference_baseline: str = D144_REFERENCE_BASELINE
    promotion_authority: Literal[False] = False
    rollback_authority: Literal[False] = False
    execution_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    configuration_authority: Literal[False] = False
    automatic_stage_increase: Literal[False] = False
    automatic_stage_decrease: Literal[False] = False

    def __post_init__(self) -> None:
        if self.reference_baseline != D144_REFERENCE_BASELINE:
            raise ValueError("cognitive_runtime_rollout_baseline_invalid")
        if self.stage is None:
            if self.rollout_bps is not None:
                raise ValueError("cognitive_runtime_rollout_stage_bps_invalid")
            if self.reason_code not in {
                "cognitive_runtime_disabled",
                "not_cognitive_eligible",
                "invalid_rollout_stage",
            }:
                raise ValueError("cognitive_runtime_rollout_stage_missing")
        else:
            expected_bps = rollout_bps_for_stage(self.stage)
            if expected_bps is None or self.rollout_bps != expected_bps:
                raise ValueError("cognitive_runtime_rollout_stage_bps_invalid")

        expected_disposition = {
            "cognitive_runtime_disabled": "not_applicable",
            "not_cognitive_eligible": "not_applicable",
            "rollout_control_only": "control",
            "rollout_bucket_control": "control",
            "rollout_bucket_cognitive": "cognitive",
            "rollout_full": "cognitive",
            "missing_conversation_identity": "control",
            "invalid_rollout_stage": "control",
        }[self.reason_code]
        if self.disposition != expected_disposition:
            raise ValueError("cognitive_runtime_rollout_disposition_invalid")
        if self.reason_code == "rollout_control_only" and self.stage != "control_only":
            raise ValueError("cognitive_runtime_rollout_control_stage_invalid")
        if self.reason_code == "rollout_full" and self.stage != "full":
            raise ValueError("cognitive_runtime_rollout_full_stage_invalid")
        if self.reason_code in {"rollout_bucket_control", "rollout_bucket_cognitive"} and self.stage not in {
            "canary_1", "canary_5", "canary_10", "canary_25", "canary_50"
        }:
            raise ValueError("cognitive_runtime_rollout_canary_stage_invalid")
        for name in (
            "promotion_authority", "rollback_authority", "execution_authority",
            "routing_authority", "configuration_authority",
            "automatic_stage_increase", "automatic_stage_decrease",
        ):
            if getattr(self, name) is not False:
                raise ValueError(f"cognitive_runtime_rollout_{name}_invalid")
