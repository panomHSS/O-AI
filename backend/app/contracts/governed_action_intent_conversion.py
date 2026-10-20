"""D169 immutable governed proposal -> ActionIntent conversion contracts.

The outcome records deterministic conversion only. It does not grant permission,
approval, authorization, execution readiness, or execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.governed_action import ActionIntent


D169_GOVERNED_ACTION_INTENT_CONVERSION_CONTRACT_VERSION = (
    "o-ai.governed-action-intent-conversion.v1"
)

GovernedActionIntentConversionStatus: TypeAlias = Literal[
    "not_convertible",
    "converted_for_lineage_validation",
]

_STATUSES = frozenset({"not_convertible", "converted_for_lineage_validation"})
_NOT_CONVERTIBLE_REASONS = frozenset(
    {
        "proposal_not_applicable",
        "proposal_needs_clarification",
        "proposal_unsupported",
    }
)
_CONVERTED_REASON = "proposal_converted_for_lineage_validation"


@dataclass(frozen=True, slots=True)
class GovernedActionIntentConversionOutcome:
    """Conversion result only; never permission, approval, or execution."""

    status: GovernedActionIntentConversionStatus
    reason_code: str
    action_intent: ActionIntent | None = None
    contract_version: str = (
        D169_GOVERNED_ACTION_INTENT_CONVERSION_CONTRACT_VERSION
    )

    def __post_init__(self) -> None:
        if self.status not in _STATUSES:
            raise ValueError("governed_action_intent_conversion_status_invalid")
        if (
            type(self.reason_code) is not str
            or not self.reason_code
            or self.reason_code != self.reason_code.strip()
        ):
            raise ValueError("governed_action_intent_conversion_reason_invalid")
        if (
            self.contract_version
            != D169_GOVERNED_ACTION_INTENT_CONVERSION_CONTRACT_VERSION
        ):
            raise ValueError(
                "governed_action_intent_conversion_contract_version_invalid"
            )

        if self.status == "not_convertible":
            if (
                self.reason_code not in _NOT_CONVERTIBLE_REASONS
                or self.action_intent is not None
            ):
                raise ValueError(
                    "governed_action_intent_conversion_not_convertible_invalid"
                )
            return

        if (
            self.reason_code != _CONVERTED_REASON
            or not isinstance(self.action_intent, ActionIntent)
        ):
            raise ValueError(
                "governed_action_intent_conversion_converted_invalid"
            )


__all__ = [
    "D169_GOVERNED_ACTION_INTENT_CONVERSION_CONTRACT_VERSION",
    "GovernedActionIntentConversionOutcome",
    "GovernedActionIntentConversionStatus",
]