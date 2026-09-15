"""D54 bounded, process-local, default-deny Plugin governance."""

from __future__ import annotations

import threading

from app.contracts.plugin_candidate import (
    PLUGIN_CANDIDATE_STATUS_PROJECTED_MATCH,
    PluginDiscoveryCandidate,
)
from app.contracts.plugin_governance import (
    PLUGIN_GOVERNANCE_STATE_ADMITTED,
    PLUGIN_GOVERNANCE_STATE_REJECTED,
    PLUGIN_GOVERNANCE_STATE_REVOKED,
    PluginGovernanceDecision,
)
from app.services.plugin_candidate_discovery import PluginCandidateDiscovery


DEFAULT_MAX_GOVERNANCE_DECISIONS = 100

PLUGIN_GOVERNANCE_ERROR_CANDIDATE_RESOLUTION_FAILED = (
    "governance_candidate_resolution_failed"
)
PLUGIN_GOVERNANCE_ERROR_CANDIDATE_NOT_FOUND = (
    "governance_candidate_not_found"
)
PLUGIN_GOVERNANCE_ERROR_CANDIDATE_NOT_ELIGIBLE = (
    "governance_candidate_not_eligible"
)
PLUGIN_GOVERNANCE_ERROR_SUBJECT_MISMATCH = "governance_subject_mismatch"
PLUGIN_GOVERNANCE_ERROR_DECISION_NOT_FOUND = "governance_decision_not_found"
PLUGIN_GOVERNANCE_ERROR_INVALID_TRANSITION = "governance_invalid_transition"
PLUGIN_GOVERNANCE_ERROR_STORE_FULL = "governance_store_full"
PLUGIN_GOVERNANCE_ERROR_INVALID_PLUGIN_ID = "invalid_governance_plugin_id"
PLUGIN_GOVERNANCE_ERROR_INVALID_PLUGIN_VERSION = (
    "invalid_governance_plugin_version"
)


class PluginGovernanceError(ValueError):
    """Safe D54 governance error with a stable reason code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _validated_subject(
    plugin_id: object,
    plugin_version: object,
) -> tuple[str, str]:
    if (
        not isinstance(plugin_id, str)
        or not plugin_id
        or plugin_id != plugin_id.strip()
    ):
        raise PluginGovernanceError(
            PLUGIN_GOVERNANCE_ERROR_INVALID_PLUGIN_ID
        )
    if (
        not isinstance(plugin_version, str)
        or not plugin_version
        or plugin_version != plugin_version.strip()
    ):
        raise PluginGovernanceError(
            PLUGIN_GOVERNANCE_ERROR_INVALID_PLUGIN_VERSION
        )
    return plugin_id, plugin_version


class PluginGovernanceDecisionStore:
    """Thread-safe bounded process-local governance decision snapshot.

    The store never evicts decisions silently. It stores governance state only;
    it does not load Plugins or mutate any Plugin/Adapter registry.
    """

    def __init__(
        self,
        *,
        max_decisions: int = DEFAULT_MAX_GOVERNANCE_DECISIONS,
    ) -> None:
        if (
            isinstance(max_decisions, bool)
            or not isinstance(max_decisions, int)
            or max_decisions < 1
        ):
            raise ValueError("max_decisions must be a positive integer.")
        self._max_decisions = max_decisions
        self._items: dict[
            tuple[str, str],
            PluginGovernanceDecision,
        ] = {}
        self._lock = threading.Lock()

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._items)

    def resolve(
        self,
        plugin_id: str,
        plugin_version: str,
    ) -> PluginGovernanceDecision | None:
        key = (plugin_id, plugin_version)
        with self._lock:
            return self._items.get(key)

    def list_decisions(self) -> tuple[PluginGovernanceDecision, ...]:
        with self._lock:
            return tuple(
                sorted(
                    self._items.values(),
                    key=lambda decision: (
                        decision.plugin_id,
                        decision.plugin_version,
                    ),
                )
            )

    def record(
        self,
        decision: PluginGovernanceDecision,
        *,
        allowed_existing_states: frozenset[str],
    ) -> PluginGovernanceDecision:
        """Atomically create/transition one exact governance subject."""

        key = (decision.plugin_id, decision.plugin_version)
        with self._lock:
            existing = self._items.get(key)
            if existing is not None:
                if (
                    existing.projected_capability_names
                    != decision.projected_capability_names
                ):
                    raise PluginGovernanceError(
                        PLUGIN_GOVERNANCE_ERROR_SUBJECT_MISMATCH
                    )
                if existing.state == decision.state:
                    return existing
                if existing.state not in allowed_existing_states:
                    raise PluginGovernanceError(
                        PLUGIN_GOVERNANCE_ERROR_INVALID_TRANSITION
                    )
                self._items[key] = decision
                return decision

            if len(self._items) >= self._max_decisions:
                raise PluginGovernanceError(
                    PLUGIN_GOVERNANCE_ERROR_STORE_FULL
                )
            self._items[key] = decision
            return decision

    def revoke(
        self,
        plugin_id: str,
        plugin_version: str,
    ) -> PluginGovernanceDecision:
        """Revoke an admitted subject without consulting discovery."""

        key = (plugin_id, plugin_version)
        with self._lock:
            existing = self._items.get(key)
            if existing is None:
                raise PluginGovernanceError(
                    PLUGIN_GOVERNANCE_ERROR_DECISION_NOT_FOUND
                )
            if existing.state == PLUGIN_GOVERNANCE_STATE_REVOKED:
                return existing
            if existing.state != PLUGIN_GOVERNANCE_STATE_ADMITTED:
                raise PluginGovernanceError(
                    PLUGIN_GOVERNANCE_ERROR_INVALID_TRANSITION
                )

            revoked = PluginGovernanceDecision(
                plugin_id=existing.plugin_id,
                plugin_version=existing.plugin_version,
                projected_capability_names=(
                    existing.projected_capability_names
                ),
                state=PLUGIN_GOVERNANCE_STATE_REVOKED,
            )
            self._items[key] = revoked
            return revoked

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


class PluginGovernanceService:
    """Owner-governed admission metadata without loading/execution authority."""

    def __init__(
        self,
        *,
        candidate_discovery: PluginCandidateDiscovery,
        store: PluginGovernanceDecisionStore,
    ) -> None:
        self._candidate_discovery = candidate_discovery
        self._store = store

    def admit(
        self,
        plugin_id: str,
        plugin_version: str,
    ) -> PluginGovernanceDecision:
        candidate = self._resolve_eligible_candidate(
            plugin_id,
            plugin_version,
        )
        decision = self._decision_from_candidate(
            candidate,
            state=PLUGIN_GOVERNANCE_STATE_ADMITTED,
        )
        return self._store.record(
            decision,
            allowed_existing_states=frozenset(
                {
                    PLUGIN_GOVERNANCE_STATE_REJECTED,
                    PLUGIN_GOVERNANCE_STATE_REVOKED,
                }
            ),
        )

    def reject(
        self,
        plugin_id: str,
        plugin_version: str,
    ) -> PluginGovernanceDecision:
        candidate = self._resolve_eligible_candidate(
            plugin_id,
            plugin_version,
        )
        decision = self._decision_from_candidate(
            candidate,
            state=PLUGIN_GOVERNANCE_STATE_REJECTED,
        )
        return self._store.record(
            decision,
            allowed_existing_states=frozenset(),
        )

    def revoke(
        self,
        plugin_id: str,
        plugin_version: str,
    ) -> PluginGovernanceDecision:
        plugin_id, plugin_version = _validated_subject(
            plugin_id,
            plugin_version,
        )
        return self._store.revoke(plugin_id, plugin_version)

    def resolve(
        self,
        plugin_id: str,
        plugin_version: str,
    ) -> PluginGovernanceDecision | None:
        plugin_id, plugin_version = _validated_subject(
            plugin_id,
            plugin_version,
        )
        return self._store.resolve(plugin_id, plugin_version)

    def list_decisions(self) -> tuple[PluginGovernanceDecision, ...]:
        return self._store.list_decisions()

    def _resolve_eligible_candidate(
        self,
        plugin_id: str,
        plugin_version: str,
    ) -> PluginDiscoveryCandidate:
        plugin_id, plugin_version = _validated_subject(
            plugin_id,
            plugin_version,
        )

        try:
            candidates = self._candidate_discovery.discover_candidates()
        except Exception:
            raise PluginGovernanceError(
                PLUGIN_GOVERNANCE_ERROR_CANDIDATE_RESOLUTION_FAILED
            ) from None

        candidate = next(
            (
                item
                for item in candidates
                if item.plugin_id == plugin_id
                and item.plugin_version == plugin_version
            ),
            None,
        )
        if candidate is None:
            raise PluginGovernanceError(
                PLUGIN_GOVERNANCE_ERROR_CANDIDATE_NOT_FOUND
            )
        if candidate.status != PLUGIN_CANDIDATE_STATUS_PROJECTED_MATCH:
            raise PluginGovernanceError(
                PLUGIN_GOVERNANCE_ERROR_CANDIDATE_NOT_ELIGIBLE
            )
        return candidate

    @staticmethod
    def _decision_from_candidate(
        candidate: PluginDiscoveryCandidate,
        *,
        state: str,
    ) -> PluginGovernanceDecision:
        return PluginGovernanceDecision(
            plugin_id=candidate.plugin_id,
            plugin_version=candidate.plugin_version,
            projected_capability_names=(
                candidate.projected_capability_names
            ),
            state=state,  # type: ignore[arg-type]
        )
