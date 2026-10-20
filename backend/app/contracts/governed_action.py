"""D166 immutable governed Brain -> Hands boundary contracts."""

from __future__ import annotations

import math
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal, TypeAlias

from app.contracts.capability_permission import (
    CapabilityDataClass,
    CapabilityEffect,
    ExecutableTargetKind,
)
from app.contracts.execution_approval import ExecutionApprovalProposalOutcome


D166_GOVERNED_ACTION_CONTRACT_VERSION = "o-ai.governed-action.v1"

ActionRiskClass: TypeAlias = Literal["R0", "R1", "R2", "R3"]
GovernedActionStatus: TypeAlias = Literal[
    "pending_approval", "rejected", "unavailable"
]
VerificationStatus: TypeAlias = Literal[
    "not_attempted", "failed", "unverified", "verified"
]
SideEffectState: TypeAlias = Literal[
    "no_side_effect",
    "partial_or_unknown_side_effect",
    "completed_side_effect",
]
RecoveryDisposition: TypeAlias = Literal[
    "not_required",
    "rollback_available",
    "manual_recovery_required",
]

_RISK_CLASSES = frozenset({"R0", "R1", "R2", "R3"})
_GOVERNED_STATUSES = frozenset(
    {"pending_approval", "rejected", "unavailable"}
)
_VERIFICATION_STATUSES = frozenset(
    {"not_attempted", "failed", "unverified", "verified"}
)
_SIDE_EFFECT_STATES = frozenset(
    {
        "no_side_effect",
        "partial_or_unknown_side_effect",
        "completed_side_effect",
    }
)
_RECOVERY_DISPOSITIONS = frozenset(
    {
        "not_required",
        "rollback_available",
        "manual_recovery_required",
    }
)
_TARGET_KINDS = frozenset({"tool", "module"})
_HEX = frozenset("0123456789abcdef")
_MAX_TEXT_BYTES = 1024
_MAX_PARAMETER_DEPTH = 16
_MAX_SEQUENCE_ITEMS = 256
_MAX_MAPPING_ITEMS = 256


def _text(value: object, *, code: str) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > _MAX_TEXT_BYTES
        or any(unicodedata.category(character) == "Cc" for character in value)
    ):
        raise ValueError(code)
    return value


def _digest(value: object, *, code: str) -> str:
    text = _text(value, code=code)
    if len(text) != 64 or any(character not in _HEX for character in text):
        raise ValueError(code)
    return text


def _freeze_value(value: object, *, depth: int = 0) -> object:
    if depth > _MAX_PARAMETER_DEPTH:
        raise ValueError("governed_action_parameters_invalid")
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("governed_action_parameters_invalid")
        return value
    if isinstance(value, Mapping):
        if len(value) > _MAX_MAPPING_ITEMS:
            raise ValueError("governed_action_parameters_invalid")
        normalized: dict[str, object] = {}
        for key, item in value.items():
            key_text = _text(key, code="governed_action_parameters_invalid")
            if key_text in normalized:
                raise ValueError("governed_action_parameters_invalid")
            normalized[key_text] = _freeze_value(item, depth=depth + 1)
        return MappingProxyType(
            {key: normalized[key] for key in sorted(normalized)}
        )
    if (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes, bytearray))
    ):
        if len(value) > _MAX_SEQUENCE_ITEMS:
            raise ValueError("governed_action_parameters_invalid")
        return tuple(
            _freeze_value(item, depth=depth + 1)
            for item in value
        )
    raise ValueError("governed_action_parameters_invalid")


def freeze_parameters(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError("governed_action_parameters_invalid")
    frozen = _freeze_value(value)
    if not isinstance(frozen, Mapping):
        raise ValueError("governed_action_parameters_invalid")
    return frozen


@dataclass(frozen=True, slots=True)
class ActionIntent:
    """Non-authoritative Brain action intent; never permission or execution."""

    source_turn_id: str
    source_artifact_digest: str
    target_kind: ExecutableTargetKind
    adapter_id: str
    operation: str
    parameters: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_turn_id",
            _text(
                self.source_turn_id,
                code="governed_action_source_turn_id_invalid",
            ),
        )
        object.__setattr__(
            self,
            "source_artifact_digest",
            _digest(
                self.source_artifact_digest,
                code="governed_action_source_artifact_digest_invalid",
            ),
        )
        if self.target_kind not in _TARGET_KINDS:
            raise ValueError("governed_action_target_kind_invalid")
        object.__setattr__(
            self,
            "adapter_id",
            _text(
                self.adapter_id,
                code="governed_action_adapter_id_invalid",
            ),
        )
        object.__setattr__(
            self,
            "operation",
            _text(
                self.operation,
                code="governed_action_operation_invalid",
            ),
        )
        object.__setattr__(
            self,
            "parameters",
            freeze_parameters(self.parameters),
        )


@dataclass(frozen=True, slots=True)
class RiskClassification:
    """Deterministic, non-authoritative risk projection."""

    capability_id: str
    effect: CapabilityEffect
    risk_class: ActionRiskClass
    reversible: bool
    reason_code: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "capability_id",
            _text(
                self.capability_id,
                code="governed_action_capability_id_invalid",
            ),
        )
        if self.risk_class not in _RISK_CLASSES:
            raise ValueError("governed_action_risk_class_invalid")
        if self.effect not in {
            "none",
            "read",
            "write",
            "external_side_effect",
            "process_execution",
        }:
            raise ValueError("governed_action_effect_invalid")
        if type(self.reversible) is not bool:
            raise ValueError("governed_action_reversible_invalid")
        object.__setattr__(
            self,
            "reason_code",
            _text(
                self.reason_code,
                code="governed_action_risk_reason_invalid",
            ),
        )

        expected = {
            "R0": self.effect in {"none", "read"} and not self.reversible,
            "R1": self.effect == "write" and self.reversible,
            "R2": self.effect == "external_side_effect" and not self.reversible,
            "R3": (
                self.effect in {"write", "process_execution"}
                and not self.reversible
            ),
        }[self.risk_class]
        if not expected:
            raise ValueError("governed_action_risk_semantics_invalid")


@dataclass(frozen=True, slots=True)
class GovernedActionPreparation:
    """Preparation outcome that may expose approval, never execution."""

    intent_digest: str
    status: GovernedActionStatus
    reason_code: str
    capability_id: str | None = None
    effect: CapabilityEffect | None = None
    data_class: CapabilityDataClass | None = None
    risk: RiskClassification | None = None
    confirmation_required: bool | None = None
    approval: ExecutionApprovalProposalOutcome | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "intent_digest",
            _digest(
                self.intent_digest,
                code="governed_action_intent_digest_invalid",
            ),
        )
        if self.status not in _GOVERNED_STATUSES:
            raise ValueError("governed_action_status_invalid")
        object.__setattr__(
            self,
            "reason_code",
            _text(
                self.reason_code,
                code="governed_action_reason_code_invalid",
            ),
        )
        if self.capability_id is not None:
            object.__setattr__(
                self,
                "capability_id",
                _text(
                    self.capability_id,
                    code="governed_action_capability_id_invalid",
                ),
            )
        if self.confirmation_required is not None and type(
            self.confirmation_required
        ) is not bool:
            raise ValueError("governed_action_confirmation_invalid")

        if self.status == "pending_approval":
            if (
                self.capability_id is None
                or self.effect is None
                or self.data_class is None
                or self.risk is None
                or self.confirmation_required is not True
                or self.approval is None
                or self.approval.status != "pending"
                or self.approval.proposal is None
            ):
                raise ValueError("governed_action_pending_invalid")
        elif self.approval is not None:
            raise ValueError("governed_action_nonpending_approval_invalid")


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """Execution success and result verification are separate facts."""

    status: VerificationStatus
    execution_attempted: bool
    execution_succeeded: bool
    reason_code: str
    verification_evidence_id: str | None = None

    def __post_init__(self) -> None:
        if self.status not in _VERIFICATION_STATUSES:
            raise ValueError("governed_action_verification_status_invalid")
        if (
            type(self.execution_attempted) is not bool
            or type(self.execution_succeeded) is not bool
        ):
            raise ValueError("governed_action_verification_flags_invalid")
        object.__setattr__(
            self,
            "reason_code",
            _text(
                self.reason_code,
                code="governed_action_verification_reason_invalid",
            ),
        )
        if self.verification_evidence_id is not None:
            object.__setattr__(
                self,
                "verification_evidence_id",
                _text(
                    self.verification_evidence_id,
                    code="governed_action_verification_evidence_invalid",
                ),
            )

        if self.status == "not_attempted":
            valid = (
                not self.execution_attempted
                and not self.execution_succeeded
                and self.verification_evidence_id is None
            )
        elif self.status == "failed":
            valid = (
                self.execution_attempted
                and not self.execution_succeeded
                and self.verification_evidence_id is None
            )
        elif self.status == "unverified":
            valid = (
                self.execution_attempted
                and self.execution_succeeded
                and self.verification_evidence_id is None
            )
        else:
            valid = (
                self.execution_attempted
                and self.execution_succeeded
                and self.verification_evidence_id is not None
            )
        if not valid:
            raise ValueError("governed_action_verification_semantics_invalid")


@dataclass(frozen=True, slots=True)
class RecoveryState:
    """Descriptive recovery state with no retry/rollback authority."""

    side_effect_state: SideEffectState
    rollback_available: bool
    disposition: RecoveryDisposition
    reason_code: str

    def __post_init__(self) -> None:
        if self.side_effect_state not in _SIDE_EFFECT_STATES:
            raise ValueError("governed_action_side_effect_state_invalid")
        if type(self.rollback_available) is not bool:
            raise ValueError("governed_action_rollback_flag_invalid")
        if self.disposition not in _RECOVERY_DISPOSITIONS:
            raise ValueError("governed_action_recovery_disposition_invalid")
        object.__setattr__(
            self,
            "reason_code",
            _text(
                self.reason_code,
                code="governed_action_recovery_reason_invalid",
            ),
        )

        if self.side_effect_state == "no_side_effect":
            valid = (
                not self.rollback_available
                and self.disposition == "not_required"
            )
        elif self.rollback_available:
            valid = self.disposition == "rollback_available"
        else:
            valid = self.disposition == "manual_recovery_required"

        if not valid:
            raise ValueError("governed_action_recovery_semantics_invalid")
