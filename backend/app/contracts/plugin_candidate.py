"""D53 immutable contracts for Plugin discovery candidate reconciliation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


PLUGIN_CANDIDATE_STATUS_PROJECTED_MATCH = "projected_match"
PLUGIN_CANDIDATE_STATUS_UNPROJECTED = "unprojected"
PLUGIN_CANDIDATE_STATUS_VERSION_MISMATCH = "version_mismatch"
PLUGIN_CANDIDATE_STATUSES = frozenset(
    {
        PLUGIN_CANDIDATE_STATUS_PROJECTED_MATCH,
        PLUGIN_CANDIDATE_STATUS_UNPROJECTED,
        PLUGIN_CANDIDATE_STATUS_VERSION_MISMATCH,
    }
)
PluginCandidateStatus = Literal[
    "projected_match",
    "unprojected",
    "version_mismatch",
]

PLUGIN_CANDIDATE_REASON_PROJECTION_MATCH = "projection_match"
PLUGIN_CANDIDATE_REASON_PROJECTION_MISSING = "projection_missing"
PLUGIN_CANDIDATE_REASON_VERSION_MISMATCH = "projection_version_mismatch"

PLUGIN_CANDIDATE_ERROR_INVALID_PLUGIN_ID = "invalid_plugin_id"
PLUGIN_CANDIDATE_ERROR_INVALID_PLUGIN_VERSION = "invalid_plugin_version"
PLUGIN_CANDIDATE_ERROR_INVALID_STATUS = "invalid_candidate_status"
PLUGIN_CANDIDATE_ERROR_INVALID_CAPABILITIES = "invalid_projected_capabilities"
PLUGIN_CANDIDATE_ERROR_INVALID_REASON = "invalid_candidate_reason"


class PluginCandidateContractError(ValueError):
    """Safe D53 candidate-contract error with a stable reason code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _validated_text(value: object, *, code: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise PluginCandidateContractError(code)
    return value


@dataclass(frozen=True, slots=True)
class PluginDiscoveryCandidate:
    """Read-only reconciliation result for one discovered Plugin manifest."""

    plugin_id: str
    plugin_version: str
    status: PluginCandidateStatus
    projected_capability_names: tuple[str, ...]
    reason_code: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "plugin_id",
            _validated_text(
                self.plugin_id,
                code=PLUGIN_CANDIDATE_ERROR_INVALID_PLUGIN_ID,
            ),
        )
        object.__setattr__(
            self,
            "plugin_version",
            _validated_text(
                self.plugin_version,
                code=PLUGIN_CANDIDATE_ERROR_INVALID_PLUGIN_VERSION,
            ),
        )
        if self.status not in PLUGIN_CANDIDATE_STATUSES:
            raise PluginCandidateContractError(
                PLUGIN_CANDIDATE_ERROR_INVALID_STATUS
            )
        if not isinstance(self.projected_capability_names, tuple):
            raise PluginCandidateContractError(
                PLUGIN_CANDIDATE_ERROR_INVALID_CAPABILITIES
            )
        capabilities = tuple(
            _validated_text(
                capability,
                code=PLUGIN_CANDIDATE_ERROR_INVALID_CAPABILITIES,
            )
            for capability in self.projected_capability_names
        )
        if len(set(capabilities)) != len(capabilities):
            raise PluginCandidateContractError(
                PLUGIN_CANDIDATE_ERROR_INVALID_CAPABILITIES
            )
        capabilities = tuple(sorted(capabilities))

        expected_reason = {
            PLUGIN_CANDIDATE_STATUS_PROJECTED_MATCH: (
                PLUGIN_CANDIDATE_REASON_PROJECTION_MATCH
            ),
            PLUGIN_CANDIDATE_STATUS_UNPROJECTED: (
                PLUGIN_CANDIDATE_REASON_PROJECTION_MISSING
            ),
            PLUGIN_CANDIDATE_STATUS_VERSION_MISMATCH: (
                PLUGIN_CANDIDATE_REASON_VERSION_MISMATCH
            ),
        }[self.status]
        if self.reason_code != expected_reason:
            raise PluginCandidateContractError(
                PLUGIN_CANDIDATE_ERROR_INVALID_REASON
            )

        if self.status == PLUGIN_CANDIDATE_STATUS_PROJECTED_MATCH:
            if not capabilities:
                raise PluginCandidateContractError(
                    PLUGIN_CANDIDATE_ERROR_INVALID_CAPABILITIES
                )
        elif capabilities:
            raise PluginCandidateContractError(
                PLUGIN_CANDIDATE_ERROR_INVALID_CAPABILITIES
            )

        object.__setattr__(
            self,
            "projected_capability_names",
            capabilities,
        )
