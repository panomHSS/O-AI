"""D54 immutable contracts for Plugin governance admission state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


PLUGIN_GOVERNANCE_STATE_ADMITTED = "admitted"
PLUGIN_GOVERNANCE_STATE_REJECTED = "rejected"
PLUGIN_GOVERNANCE_STATE_REVOKED = "revoked"
PLUGIN_GOVERNANCE_STATES = frozenset(
    {
        PLUGIN_GOVERNANCE_STATE_ADMITTED,
        PLUGIN_GOVERNANCE_STATE_REJECTED,
        PLUGIN_GOVERNANCE_STATE_REVOKED,
    }
)
PluginGovernanceState = Literal[
    "admitted",
    "rejected",
    "revoked",
]

PLUGIN_GOVERNANCE_CONTRACT_ERROR_INVALID_PLUGIN_ID = (
    "invalid_governance_plugin_id"
)
PLUGIN_GOVERNANCE_CONTRACT_ERROR_INVALID_PLUGIN_VERSION = (
    "invalid_governance_plugin_version"
)
PLUGIN_GOVERNANCE_CONTRACT_ERROR_INVALID_CAPABILITIES = (
    "invalid_governance_capabilities"
)
PLUGIN_GOVERNANCE_CONTRACT_ERROR_INVALID_STATE = (
    "invalid_governance_state"
)


class PluginGovernanceContractError(ValueError):
    """Safe D54 governance-contract error with a stable reason code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _validated_text(value: object, *, code: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise PluginGovernanceContractError(code)
    return value


@dataclass(frozen=True, slots=True)
class PluginGovernanceDecision:
    """Exact Plugin id/version/capability subject with a governance state."""

    plugin_id: str
    plugin_version: str
    projected_capability_names: tuple[str, ...]
    state: PluginGovernanceState

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "plugin_id",
            _validated_text(
                self.plugin_id,
                code=PLUGIN_GOVERNANCE_CONTRACT_ERROR_INVALID_PLUGIN_ID,
            ),
        )
        object.__setattr__(
            self,
            "plugin_version",
            _validated_text(
                self.plugin_version,
                code=PLUGIN_GOVERNANCE_CONTRACT_ERROR_INVALID_PLUGIN_VERSION,
            ),
        )

        if not isinstance(self.projected_capability_names, tuple):
            raise PluginGovernanceContractError(
                PLUGIN_GOVERNANCE_CONTRACT_ERROR_INVALID_CAPABILITIES
            )
        capabilities = tuple(
            _validated_text(
                capability,
                code=PLUGIN_GOVERNANCE_CONTRACT_ERROR_INVALID_CAPABILITIES,
            )
            for capability in self.projected_capability_names
        )
        if not capabilities or len(set(capabilities)) != len(capabilities):
            raise PluginGovernanceContractError(
                PLUGIN_GOVERNANCE_CONTRACT_ERROR_INVALID_CAPABILITIES
            )
        object.__setattr__(
            self,
            "projected_capability_names",
            tuple(sorted(capabilities)),
        )

        if self.state not in PLUGIN_GOVERNANCE_STATES:
            raise PluginGovernanceContractError(
                PLUGIN_GOVERNANCE_CONTRACT_ERROR_INVALID_STATE
            )
