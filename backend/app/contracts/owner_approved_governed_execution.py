"""D181 immutable cognitive-governed execution correlation contract.

The binding records exact cognitive/approval lineage for an owner decision.
It grants no approval, authorization, execution readiness, or execution authority.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypeAlias
from uuid import UUID

from app.contracts.capability_permission import CapabilityEffect, ExecutableTargetKind
from app.contracts.governed_action import ActionRiskClass
from app.contracts.workspace import WorkspaceId

D181_OWNER_APPROVED_GOVERNED_EXECUTION_CONTRACT_VERSION = (
    "o-ai.owner-approved-governed-execution.v1"
)

CognitiveExecutionBindingStatus: TypeAlias = Literal["bound"]
_HEX = frozenset("0123456789abcdef")
_TARGETS = frozenset({"tool", "module"})
_EFFECTS = frozenset(
    {"none", "read", "write", "external_side_effect", "process_execution"}
)
_RISKS = frozenset({"R0", "R1", "R2", "R3"})


def _text(value: object, *, code: str) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > 1024
        or any(unicodedata.category(character) == "Cc" for character in value)
    ):
        raise ValueError(code)
    return value


def _digest(value: object, *, code: str) -> str:
    text = _text(value, code=code)
    if len(text) != 64 or any(character not in _HEX for character in text):
        raise ValueError(code)
    return text


@dataclass(frozen=True, slots=True)
class CognitiveExecutionBinding:
    """Correlation evidence only; never approval or execution authority."""

    workspace_id: WorkspaceId
    conversation_id: UUID
    source_turn_id: str
    source_artifact_digest: str
    intent_digest: str
    approval_id: str
    execution_request_id: str
    plan_digest: str
    target_kind: ExecutableTargetKind
    capability_id: str
    adapter_id: str
    operation: str
    effect: CapabilityEffect
    risk_class: ActionRiskClass
    expires_at: datetime
    status: CognitiveExecutionBindingStatus = "bound"
    contract_version: str = D181_OWNER_APPROVED_GOVERNED_EXECUTION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_id, WorkspaceId):
            raise ValueError("cognitive_execution_workspace_invalid")
        if not isinstance(self.conversation_id, UUID):
            raise ValueError("cognitive_execution_conversation_invalid")

        for field_name, code in (
            ("source_turn_id", "cognitive_execution_source_turn_invalid"),
            ("approval_id", "cognitive_execution_approval_id_invalid"),
            ("execution_request_id", "cognitive_execution_request_id_invalid"),
            ("capability_id", "cognitive_execution_capability_invalid"),
            ("adapter_id", "cognitive_execution_adapter_invalid"),
            ("operation", "cognitive_execution_operation_invalid"),
        ):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), code=code),
            )

        for field_name, code in (
            ("source_artifact_digest", "cognitive_execution_source_artifact_invalid"),
            ("intent_digest", "cognitive_execution_intent_digest_invalid"),
            ("plan_digest", "cognitive_execution_plan_digest_invalid"),
        ):
            object.__setattr__(
                self,
                field_name,
                _digest(getattr(self, field_name), code=code),
            )

        if self.target_kind not in _TARGETS:
            raise ValueError("cognitive_execution_target_invalid")
        if self.effect not in _EFFECTS:
            raise ValueError("cognitive_execution_effect_invalid")
        if self.risk_class not in _RISKS:
            raise ValueError("cognitive_execution_risk_invalid")
        if self.expires_at.tzinfo is None:
            raise ValueError("cognitive_execution_expiry_invalid")
        if self.status != "bound":
            raise ValueError("cognitive_execution_binding_status_invalid")
        if self.contract_version != D181_OWNER_APPROVED_GOVERNED_EXECUTION_CONTRACT_VERSION:
            raise ValueError("cognitive_execution_contract_version_invalid")

        expected_risk = {
            "R0": self.effect in {"none", "read"},
            "R1": self.effect == "write",
            "R2": self.effect == "external_side_effect",
            "R3": self.effect in {"write", "process_execution"},
        }[self.risk_class]
        if not expected_risk:
            raise ValueError("cognitive_execution_risk_semantics_invalid")


__all__ = [
    "CognitiveExecutionBinding",
    "CognitiveExecutionBindingStatus",
    "D181_OWNER_APPROVED_GOVERNED_EXECUTION_CONTRACT_VERSION",
]
