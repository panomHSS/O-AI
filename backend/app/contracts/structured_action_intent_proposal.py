"""D168 immutable structured action intent proposal contracts.

These contracts carry non-authoritative semantic proposal data only. They grant
no permission, approval, authorization, persistence, connector, tool/module,
scheduler, provider, or execution authority.
"""

from __future__ import annotations

import math
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal, TypeAlias

from app.contracts.capability_permission import ExecutableTargetKind


D168_STRUCTURED_ACTION_INTENT_PROPOSAL_CONTRACT_VERSION = (
    "o-ai.structured-action-intent-proposal.v1"
)

StructuredActionIntentProposalStatus: TypeAlias = Literal[
    "not_applicable",
    "needs_clarification",
    "unsupported",
    "proposal_ready",
]

_STATUSES = frozenset(
    {
        "not_applicable",
        "needs_clarification",
        "unsupported",
        "proposal_ready",
    }
)
_TARGET_KINDS = frozenset({"tool", "module"})
_HEX = frozenset("0123456789abcdef")
_CODE_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_")
_MAX_TEXT_BYTES = 1024
_MAX_CODE_BYTES = 128
_MAX_MISSING_INFORMATION = 32
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


def _optional_text(value: object, *, code: str) -> str | None:
    if value is None:
        return None
    return _text(value, code=code)


def _digest(value: object, *, code: str) -> str:
    text = _text(value, code=code)
    if len(text) != 64 or any(character not in _HEX for character in text):
        raise ValueError(code)
    return text


def _optional_digest(value: object, *, code: str) -> str | None:
    if value is None:
        return None
    return _digest(value, code=code)


def _code(value: object, *, error: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(error)
    try:
        encoded = value.encode("ascii")
    except UnicodeEncodeError:
        raise ValueError(error) from None
    if (
        len(encoded) > _MAX_CODE_BYTES
        or value[0] not in frozenset("abcdefghijklmnopqrstuvwxyz")
        or any(character not in _CODE_CHARS for character in value)
    ):
        raise ValueError(error)
    return value


def _normalize_missing_information(value: object) -> tuple[str, ...]:
    if (
        isinstance(value, (str, bytes, bytearray))
        or not isinstance(value, Sequence)
        or len(value) > _MAX_MISSING_INFORMATION
    ):
        raise ValueError("structured_action_missing_information_invalid")
    normalized = tuple(
        _code(item, error="structured_action_missing_information_invalid")
        for item in value
    )
    if len(normalized) != len(set(normalized)):
        raise ValueError("structured_action_missing_information_invalid")
    return tuple(sorted(normalized))


def _freeze_value(value: object, *, depth: int = 0) -> object:
    if depth > _MAX_PARAMETER_DEPTH:
        raise ValueError("structured_action_parameters_invalid")
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("structured_action_parameters_invalid")
        return value
    if isinstance(value, Mapping):
        if len(value) > _MAX_MAPPING_ITEMS:
            raise ValueError("structured_action_parameters_invalid")
        normalized: dict[str, object] = {}
        for key, item in value.items():
            key_text = _text(
                key,
                code="structured_action_parameters_invalid",
            )
            if key_text in normalized:
                raise ValueError("structured_action_parameters_invalid")
            normalized[key_text] = _freeze_value(item, depth=depth + 1)
        return MappingProxyType(
            {key: normalized[key] for key in sorted(normalized)}
        )
    if (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes, bytearray))
    ):
        if len(value) > _MAX_SEQUENCE_ITEMS:
            raise ValueError("structured_action_parameters_invalid")
        return tuple(
            _freeze_value(item, depth=depth + 1)
            for item in value
        )
    raise ValueError("structured_action_parameters_invalid")


def freeze_structured_action_parameters(
    value: object,
) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError("structured_action_parameters_invalid")
    frozen = _freeze_value(value)
    if not isinstance(frozen, Mapping):
        raise ValueError("structured_action_parameters_invalid")
    return frozen


@dataclass(frozen=True, slots=True)
class StructuredActionIntentCandidate:
    """Already-structured non-authoritative candidate supplied to D168."""

    source_turn_id: str
    source_artifact_digest: str
    target_kind: str | None = None
    adapter_id: str | None = None
    operation: str | None = None
    parameters: Mapping[str, object] = field(default_factory=dict)
    missing_information: tuple[str, ...] | Sequence[str] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_turn_id",
            _text(
                self.source_turn_id,
                code="structured_action_source_turn_id_invalid",
            ),
        )
        object.__setattr__(
            self,
            "source_artifact_digest",
            _digest(
                self.source_artifact_digest,
                code="structured_action_source_artifact_digest_invalid",
            ),
        )
        object.__setattr__(
            self,
            "target_kind",
            _optional_text(
                self.target_kind,
                code="structured_action_target_kind_invalid",
            ),
        )
        object.__setattr__(
            self,
            "adapter_id",
            _optional_text(
                self.adapter_id,
                code="structured_action_adapter_id_invalid",
            ),
        )
        object.__setattr__(
            self,
            "operation",
            _optional_text(
                self.operation,
                code="structured_action_operation_invalid",
            ),
        )
        object.__setattr__(
            self,
            "parameters",
            freeze_structured_action_parameters(self.parameters),
        )
        object.__setattr__(
            self,
            "missing_information",
            _normalize_missing_information(self.missing_information),
        )


@dataclass(frozen=True, slots=True)
class StructuredActionGovernanceRequirements:
    """Mandatory downstream governance gates; never evidence of authorization."""

    owner_approval_required: bool = True
    execution_authority_required: bool = True
    capability_validation_required: bool = True

    def __post_init__(self) -> None:
        if (
            self.owner_approval_required is not True
            or self.execution_authority_required is not True
            or self.capability_validation_required is not True
        ):
            raise ValueError("structured_action_governance_requirements_invalid")


@dataclass(frozen=True, slots=True)
class StructuredActionIntentProposal:
    """Deterministic proposal only; never permission, approval, or execution."""

    status: StructuredActionIntentProposalStatus
    reason_code: str
    source_turn_id: str | None = None
    source_artifact_digest: str | None = None
    target_kind: ExecutableTargetKind | None = None
    adapter_id: str | None = None
    operation: str | None = None
    parameters: Mapping[str, object] = field(default_factory=dict)
    missing_information: tuple[str, ...] | Sequence[str] = ()
    governance_requirements: StructuredActionGovernanceRequirements | None = None
    contract_version: str = D168_STRUCTURED_ACTION_INTENT_PROPOSAL_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.status not in _STATUSES:
            raise ValueError("structured_action_proposal_status_invalid")
        object.__setattr__(
            self,
            "reason_code",
            _code(
                self.reason_code,
                error="structured_action_proposal_reason_invalid",
            ),
        )
        object.__setattr__(
            self,
            "source_turn_id",
            _optional_text(
                self.source_turn_id,
                code="structured_action_source_turn_id_invalid",
            ),
        )
        object.__setattr__(
            self,
            "source_artifact_digest",
            _optional_digest(
                self.source_artifact_digest,
                code="structured_action_source_artifact_digest_invalid",
            ),
        )
        if self.target_kind is not None and self.target_kind not in _TARGET_KINDS:
            raise ValueError("structured_action_proposal_target_kind_invalid")
        object.__setattr__(
            self,
            "adapter_id",
            _optional_text(
                self.adapter_id,
                code="structured_action_adapter_id_invalid",
            ),
        )
        object.__setattr__(
            self,
            "operation",
            _optional_text(
                self.operation,
                code="structured_action_operation_invalid",
            ),
        )
        object.__setattr__(
            self,
            "parameters",
            freeze_structured_action_parameters(self.parameters),
        )
        object.__setattr__(
            self,
            "missing_information",
            _normalize_missing_information(self.missing_information),
        )

        if self.contract_version != D168_STRUCTURED_ACTION_INTENT_PROPOSAL_CONTRACT_VERSION:
            raise ValueError("structured_action_proposal_contract_version_invalid")

        if self.status == "not_applicable":
            valid = (
                self.reason_code == "no_structured_action_candidate"
                and self.source_turn_id is None
                and self.source_artifact_digest is None
                and self.target_kind is None
                and self.adapter_id is None
                and self.operation is None
                and not self.parameters
                and not self.missing_information
                and self.governance_requirements is None
            )
            if not valid:
                raise ValueError("structured_action_not_applicable_invalid")
            return

        if (
            self.source_turn_id is None
            or self.source_artifact_digest is None
            or not isinstance(
                self.governance_requirements,
                StructuredActionGovernanceRequirements,
            )
        ):
            raise ValueError("structured_action_proposal_lineage_invalid")

        if self.status == "unsupported":
            valid = (
                self.reason_code == "unsupported_target_kind"
                and self.target_kind is None
                and self.adapter_id is None
                and self.operation is None
                and not self.parameters
                and not self.missing_information
            )
            if not valid:
                raise ValueError("structured_action_unsupported_invalid")
            return

        structural_pairs = (
            ("target_kind", self.target_kind),
            ("adapter_id", self.adapter_id),
            ("operation", self.operation),
        )
        structural_missing = {
            code for code, value in structural_pairs if value is None
        }
        structural_claimed_missing = {
            code
            for code, value in structural_pairs
            if code in self.missing_information and value is not None
        }

        if self.status == "needs_clarification":
            if (
                self.reason_code != "structured_action_information_missing"
                or not self.missing_information
                or not structural_missing.issubset(
                    set(self.missing_information)
                )
                or structural_claimed_missing
            ):
                raise ValueError("structured_action_clarification_invalid")
            return

        if (
            self.reason_code != "structured_action_proposal_ready"
            or structural_missing
            or self.missing_information
        ):
            raise ValueError("structured_action_ready_invalid")


__all__ = [
    "D168_STRUCTURED_ACTION_INTENT_PROPOSAL_CONTRACT_VERSION",
    "StructuredActionGovernanceRequirements",
    "StructuredActionIntentCandidate",
    "StructuredActionIntentProposal",
    "StructuredActionIntentProposalStatus",
    "freeze_structured_action_parameters",
]