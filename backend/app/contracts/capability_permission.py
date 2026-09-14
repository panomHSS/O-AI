"""D44 immutable Tool/Module capability-permission contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias


ExecutableTargetKind: TypeAlias = Literal["tool", "module"]
CapabilityEffect: TypeAlias = Literal[
    "none",
    "read",
    "write",
    "external_side_effect",
    "process_execution",
]
CapabilityDataClass: TypeAlias = Literal[
    "none",
    "system_metadata",
    "workspace_metadata",
    "workspace_content",
    "owner_data",
    "external_data",
]

_TARGET_KINDS = frozenset({"tool", "module"})
_EFFECTS = frozenset(
    {"none", "read", "write", "external_side_effect", "process_execution"}
)
_DATA_CLASSES = frozenset(
    {
        "none",
        "system_metadata",
        "workspace_metadata",
        "workspace_content",
        "owner_data",
        "external_data",
    }
)


def _text(value: str, *, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{label} must be a non-empty trimmed string.")
    return value


@dataclass(frozen=True, slots=True)
class ExecutableCapabilityPermission:
    """One exact central policy grant for a Tool/Module operation."""

    capability_id: str
    target_kind: ExecutableTargetKind
    adapter_id: str
    operation: str
    effect: CapabilityEffect
    data_class: CapabilityDataClass
    owner_approval_required: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "capability_id",
            _text(self.capability_id, label="capability_id"),
        )
        object.__setattr__(
            self,
            "adapter_id",
            _text(self.adapter_id, label="adapter_id"),
        )
        object.__setattr__(
            self,
            "operation",
            _text(self.operation, label="operation"),
        )
        if self.target_kind not in _TARGET_KINDS:
            raise ValueError(
                f"Unsupported executable target kind: {self.target_kind!r}."
            )
        if self.effect not in _EFFECTS:
            raise ValueError(f"Unsupported capability effect: {self.effect!r}.")
        if self.data_class not in _DATA_CLASSES:
            raise ValueError(
                f"Unsupported capability data class: {self.data_class!r}."
            )
        if type(self.owner_approval_required) is not bool:
            raise ValueError(
                "owner_approval_required must be an exact bool."
            )
