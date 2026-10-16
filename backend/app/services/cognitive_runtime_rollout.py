"""D144 deterministic cognitive rollout / canary selection."""

from __future__ import annotations

import hashlib
from uuid import UUID

from app.contracts.cognitive_runtime_rollout import (
    D144_ROLLOUT_BUCKET_COUNT,
    D144_ROLLOUT_DOMAIN,
    CognitiveRuntimeRolloutDecision,
    rollout_bps_for_stage,
)


class CognitiveRuntimeRolloutSelector:
    """Pure, stateless exposure selection over authoritative conversation UUIDs."""

    @staticmethod
    def rollout_bps_for_stage(stage: object) -> int | None:
        return rollout_bps_for_stage(stage)

    @staticmethod
    def bucket_for_conversation(conversation_id: object) -> int | None:
        if type(conversation_id) is not UUID:
            return None
        payload = (
            D144_ROLLOUT_DOMAIN.encode("utf-8")
            + b"\x00"
            + conversation_id.bytes
        )
        digest = hashlib.sha256(payload).digest()
        return int.from_bytes(digest, "big") % D144_ROLLOUT_BUCKET_COUNT

    @classmethod
    def evaluate(
        cls, *, enabled: object, cognitive_eligible: object,
        stage: object, conversation_id: object | None,
    ) -> CognitiveRuntimeRolloutDecision:
        if type(enabled) is not bool or type(cognitive_eligible) is not bool:
            return CognitiveRuntimeRolloutDecision(
                disposition="control", reason_code="invalid_rollout_stage",
                stage=None, rollout_bps=None,
            )
        if not enabled:
            return CognitiveRuntimeRolloutDecision(
                disposition="not_applicable",
                reason_code="cognitive_runtime_disabled",
                stage=None, rollout_bps=None,
            )
        if not cognitive_eligible:
            return CognitiveRuntimeRolloutDecision(
                disposition="not_applicable",
                reason_code="not_cognitive_eligible",
                stage=None, rollout_bps=None,
            )
        rollout_bps = rollout_bps_for_stage(stage)
        if rollout_bps is None:
            return CognitiveRuntimeRolloutDecision(
                disposition="control", reason_code="invalid_rollout_stage",
                stage=None, rollout_bps=None,
            )
        if type(conversation_id) is not UUID:
            return CognitiveRuntimeRolloutDecision(
                disposition="control",
                reason_code="missing_conversation_identity",
                stage=stage, rollout_bps=rollout_bps,
            )
        if stage == "control_only":
            return CognitiveRuntimeRolloutDecision(
                disposition="control", reason_code="rollout_control_only",
                stage=stage, rollout_bps=rollout_bps,
            )
        if stage == "full":
            return CognitiveRuntimeRolloutDecision(
                disposition="cognitive", reason_code="rollout_full",
                stage=stage, rollout_bps=rollout_bps,
            )
        bucket = cls.bucket_for_conversation(conversation_id)
        if bucket is None:
            return CognitiveRuntimeRolloutDecision(
                disposition="control",
                reason_code="missing_conversation_identity",
                stage=stage, rollout_bps=rollout_bps,
            )
        return CognitiveRuntimeRolloutDecision(
            disposition=("cognitive" if bucket < rollout_bps else "control"),
            reason_code=(
                "rollout_bucket_cognitive"
                if bucket < rollout_bps
                else "rollout_bucket_control"
            ),
            stage=stage,
            rollout_bps=rollout_bps,
        )
