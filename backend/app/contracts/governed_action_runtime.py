"""D167 immutable governed Brain -> Hands runtime outcome."""

from dataclasses import dataclass
from typing import Literal, TypeAlias
import unicodedata

from app.contracts.governed_action import GovernedActionPreparation

GovernedActionRuntimeStatus: TypeAlias = Literal[
    "no_action_intent",
    "intent_rejected",
    "prepared_for_owner_review",
    "approval_unavailable",
]
_STATUSES = frozenset({
    "no_action_intent", "intent_rejected",
    "prepared_for_owner_review", "approval_unavailable",
})
_HEX = frozenset("0123456789abcdef")


def _text(value: object, code: str) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > 1024
        or any(unicodedata.category(c) == "Cc" for c in value)
    ):
        raise ValueError(code)
    return value


def _digest(value: object) -> str | None:
    if value is None:
        return None
    text = _text(value, "governed_action_runtime_intent_digest_invalid")
    if len(text) != 64 or any(c not in _HEX for c in text):
        raise ValueError("governed_action_runtime_intent_digest_invalid")
    return text


@dataclass(frozen=True, slots=True)
class GovernedActionRuntimeOutcome:
    """Preparation result only; never permission or execution authority."""

    status: GovernedActionRuntimeStatus
    reason_code: str
    intent_digest: str | None = None
    preparation: GovernedActionPreparation | None = None

    def __post_init__(self) -> None:
        if self.status not in _STATUSES:
            raise ValueError("governed_action_runtime_status_invalid")
        object.__setattr__(
            self, "reason_code",
            _text(self.reason_code, "governed_action_runtime_reason_invalid"),
        )
        object.__setattr__(self, "intent_digest", _digest(self.intent_digest))

        if self.status == "no_action_intent":
            if (
                self.reason_code != "no_action_intent"
                or self.intent_digest is not None
                or self.preparation is not None
            ):
                raise ValueError("governed_action_runtime_no_intent_invalid")
            return

        if self.intent_digest is None:
            raise ValueError("governed_action_runtime_intent_digest_required")

        expected = {
            "prepared_for_owner_review": "pending_approval",
            "approval_unavailable": "unavailable",
        }.get(self.status)
        if expected is not None:
            if self.preparation is None or self.preparation.status != expected:
                raise ValueError("governed_action_runtime_preparation_invalid")
        elif (
            self.preparation is not None
            and self.preparation.status != "rejected"
        ):
            raise ValueError("governed_action_runtime_rejection_invalid")

        if (
            self.preparation is not None
            and self.preparation.intent_digest != self.intent_digest
        ):
            raise ValueError("governed_action_runtime_digest_mismatch")
