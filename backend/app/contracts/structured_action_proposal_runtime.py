"""D170 immutable structured action proposal runtime outcome."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.governed_action_intent_conversion import (
    GovernedActionIntentConversionOutcome,
)
from app.contracts.governed_action_runtime import GovernedActionRuntimeOutcome


D170_STRUCTURED_ACTION_PROPOSAL_RUNTIME_CONTRACT_VERSION = (
    "o-ai.structured-action-proposal-runtime.v1"
)

StructuredActionProposalRuntimeStatus: TypeAlias = Literal[
    "no_action_proposal",
    "proposal_not_convertible",
    "intent_rejected",
    "prepared_for_owner_review",
    "approval_unavailable",
]

_STATUSES = frozenset(
    {
        "no_action_proposal",
        "proposal_not_convertible",
        "intent_rejected",
        "prepared_for_owner_review",
        "approval_unavailable",
    }
)
_NONCONVERTIBLE_REASONS = frozenset(
    {
        "proposal_not_applicable",
        "proposal_needs_clarification",
        "proposal_unsupported",
    }
)


def _reason(value: object) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > 1024
        or any(unicodedata.category(character) == "Cc" for character in value)
    ):
        raise ValueError("structured_action_runtime_reason_invalid")
    return value


@dataclass(frozen=True, slots=True)
class StructuredActionProposalRuntimeOutcome:
    """D170 orchestration result only; never approval or execution authority."""

    status: StructuredActionProposalRuntimeStatus
    reason_code: str
    conversion: GovernedActionIntentConversionOutcome | None = None
    runtime: GovernedActionRuntimeOutcome | None = None
    contract_version: str = (
        D170_STRUCTURED_ACTION_PROPOSAL_RUNTIME_CONTRACT_VERSION
    )

    def __post_init__(self) -> None:
        if self.status not in _STATUSES:
            raise ValueError("structured_action_runtime_status_invalid")
        object.__setattr__(self, "reason_code", _reason(self.reason_code))
        if (
            self.contract_version
            != D170_STRUCTURED_ACTION_PROPOSAL_RUNTIME_CONTRACT_VERSION
        ):
            raise ValueError("structured_action_runtime_contract_version_invalid")

        if self.status == "no_action_proposal":
            if (
                self.reason_code != "no_structured_action_proposal"
                or self.conversion is not None
                or self.runtime is not None
            ):
                raise ValueError("structured_action_runtime_no_proposal_invalid")
            return

        if not isinstance(
            self.conversion,
            GovernedActionIntentConversionOutcome,
        ):
            raise ValueError("structured_action_runtime_conversion_required")

        if self.status == "proposal_not_convertible":
            if (
                self.conversion.status != "not_convertible"
                or self.conversion.reason_code not in _NONCONVERTIBLE_REASONS
                or self.reason_code != self.conversion.reason_code
                or self.runtime is not None
            ):
                raise ValueError(
                    "structured_action_runtime_not_convertible_invalid"
                )
            return

        if (
            self.conversion.status != "converted_for_lineage_validation"
            or self.conversion.action_intent is None
            or not isinstance(self.runtime, GovernedActionRuntimeOutcome)
            or self.runtime.status != self.status
            or self.reason_code != self.runtime.reason_code
        ):
            raise ValueError("structured_action_runtime_downstream_invalid")


__all__ = [
    "D170_STRUCTURED_ACTION_PROPOSAL_RUNTIME_CONTRACT_VERSION",
    "StructuredActionProposalRuntimeOutcome",
    "StructuredActionProposalRuntimeStatus",
]