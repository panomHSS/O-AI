"""D55 fail-closed controlled Plugin loading boundary."""

from __future__ import annotations

import threading
from dataclasses import dataclass

from app.contracts.plugin_candidate import (
    PLUGIN_CANDIDATE_STATUS_PROJECTED_MATCH,
)
from app.contracts.plugin_governance import (
    PLUGIN_GOVERNANCE_STATE_ADMITTED,
)
from app.contracts.plugin_loading import LoadedPluginRecord
from app.plugins.base import Plugin
from app.plugins.explicit_plugin_factory_loader import (
    PLUGIN_FACTORY_LOADER_ERROR_UNSUPPORTED_MANIFEST,
    ExplicitPluginFactoryLoaderError,
)
from app.plugins.plugin_loader import PluginLoader
from app.plugins.plugin_manifest import PluginManifest
from app.services.plugin_candidate_discovery import PluginCandidateDiscovery
from app.services.plugin_governance import PluginGovernanceService


DEFAULT_MAX_LOADED_PLUGINS = 100

PLUGIN_LOADING_ERROR_INVALID_PLUGIN_ID = "invalid_loading_plugin_id"
PLUGIN_LOADING_ERROR_INVALID_PLUGIN_VERSION = "invalid_loading_plugin_version"
PLUGIN_LOADING_ERROR_GOVERNANCE_NOT_FOUND = "loading_governance_not_found"
PLUGIN_LOADING_ERROR_GOVERNANCE_NOT_ADMITTED = (
    "loading_governance_not_admitted"
)
PLUGIN_LOADING_ERROR_CANDIDATE_RESOLUTION_FAILED = (
    "loading_candidate_resolution_failed"
)
PLUGIN_LOADING_ERROR_CANDIDATE_NOT_FOUND = "loading_candidate_not_found"
PLUGIN_LOADING_ERROR_CANDIDATE_NOT_ELIGIBLE = (
    "loading_candidate_not_eligible"
)
PLUGIN_LOADING_ERROR_SUBJECT_MISMATCH = "loading_subject_mismatch"
PLUGIN_LOADING_ERROR_MANIFEST_NOT_SUPPORTED = "loader_manifest_not_supported"
PLUGIN_LOADING_ERROR_LOAD_FAILED = "plugin_load_failed"
PLUGIN_LOADING_ERROR_PLUGIN_INVALID = "loaded_plugin_invalid"
PLUGIN_LOADING_ERROR_IDENTITY_MISMATCH = "loaded_plugin_identity_mismatch"
PLUGIN_LOADING_ERROR_STORE_FULL = "plugin_load_store_full"


class PluginLoadingError(ValueError):
    """Safe D55 loading error with a stable reason code."""

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
        raise PluginLoadingError(PLUGIN_LOADING_ERROR_INVALID_PLUGIN_ID)
    if (
        not isinstance(plugin_version, str)
        or not plugin_version
        or plugin_version != plugin_version.strip()
    ):
        raise PluginLoadingError(
            PLUGIN_LOADING_ERROR_INVALID_PLUGIN_VERSION
        )
    return plugin_id, plugin_version


@dataclass(slots=True)
class _LoadedPluginEntry:
    record: LoadedPluginRecord
    plugin: Plugin


class LoadedPluginStoreFullError(RuntimeError):
    """Internal signal that the bounded loaded-Plugin store has no capacity."""


class LoadedPluginStore:
    """Thread-safe bounded process-local store that does not expose Plugin objects."""

    def __init__(
        self,
        *,
        max_loaded: int = DEFAULT_MAX_LOADED_PLUGINS,
    ) -> None:
        if (
            isinstance(max_loaded, bool)
            or not isinstance(max_loaded, int)
            or max_loaded < 1
        ):
            raise ValueError("max_loaded must be a positive integer.")
        self._max_loaded = max_loaded
        self._items: dict[tuple[str, str], _LoadedPluginEntry] = {}
        self._lock = threading.Lock()

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._items)

    def resolve_record(
        self,
        plugin_id: str,
        plugin_version: str,
    ) -> LoadedPluginRecord | None:
        key = (plugin_id, plugin_version)
        with self._lock:
            entry = self._items.get(key)
            return entry.record if entry is not None else None

    def list_records(self) -> tuple[LoadedPluginRecord, ...]:
        with self._lock:
            return tuple(
                sorted(
                    (entry.record for entry in self._items.values()),
                    key=lambda record: (
                        record.plugin_id,
                        record.plugin_version,
                    ),
                )
            )

    def has_capacity_for(
        self,
        plugin_id: str,
        plugin_version: str,
    ) -> bool:
        key = (plugin_id, plugin_version)
        with self._lock:
            return key in self._items or len(self._items) < self._max_loaded

    def add(
        self,
        *,
        record: LoadedPluginRecord,
        plugin: Plugin,
    ) -> LoadedPluginRecord:
        key = (record.plugin_id, record.plugin_version)
        with self._lock:
            existing = self._items.get(key)
            if existing is not None:
                if existing.record != record:
                    raise PluginLoadingError(
                        PLUGIN_LOADING_ERROR_SUBJECT_MISMATCH
                    )
                return existing.record
            if len(self._items) >= self._max_loaded:
                raise LoadedPluginStoreFullError()
            self._items[key] = _LoadedPluginEntry(
                record=record,
                plugin=plugin,
            )
            return record

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


class PluginLoadingService:
    """Gate explicit Plugin construction behind D53 + D54 exact subject checks.

    Public methods return metadata only. The loaded Plugin object remains held
    inside LoadedPluginStore and is not exposed through this service.
    """

    def __init__(
        self,
        *,
        candidate_discovery: PluginCandidateDiscovery,
        governance: PluginGovernanceService,
        loader: PluginLoader,
        store: LoadedPluginStore,
    ) -> None:
        self._candidate_discovery = candidate_discovery
        self._governance = governance
        self._loader = loader
        self._store = store
        self._load_lock = threading.Lock()

    def load(
        self,
        plugin_id: str,
        plugin_version: str,
    ) -> LoadedPluginRecord:
        plugin_id, plugin_version = _validated_subject(
            plugin_id,
            plugin_version,
        )

        # Serialize v1 load attempts so duplicate calls through this service
        # cannot instantiate the same exact Plugin more than once.
        with self._load_lock:
            decision = self._governance.resolve(plugin_id, plugin_version)
            if decision is None:
                raise PluginLoadingError(
                    PLUGIN_LOADING_ERROR_GOVERNANCE_NOT_FOUND
                )
            if decision.state != PLUGIN_GOVERNANCE_STATE_ADMITTED:
                raise PluginLoadingError(
                    PLUGIN_LOADING_ERROR_GOVERNANCE_NOT_ADMITTED
                )

            try:
                candidates = self._candidate_discovery.discover_candidates()
            except Exception:
                raise PluginLoadingError(
                    PLUGIN_LOADING_ERROR_CANDIDATE_RESOLUTION_FAILED
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
                raise PluginLoadingError(
                    PLUGIN_LOADING_ERROR_CANDIDATE_NOT_FOUND
                )
            if candidate.status != PLUGIN_CANDIDATE_STATUS_PROJECTED_MATCH:
                raise PluginLoadingError(
                    PLUGIN_LOADING_ERROR_CANDIDATE_NOT_ELIGIBLE
                )
            if (
                candidate.projected_capability_names
                != decision.projected_capability_names
            ):
                raise PluginLoadingError(
                    PLUGIN_LOADING_ERROR_SUBJECT_MISMATCH
                )

            existing = self._store.resolve_record(plugin_id, plugin_version)
            if existing is not None:
                if (
                    existing.projected_capability_names
                    != candidate.projected_capability_names
                ):
                    raise PluginLoadingError(
                        PLUGIN_LOADING_ERROR_SUBJECT_MISMATCH
                    )
                return existing

            if not self._store.has_capacity_for(plugin_id, plugin_version):
                raise PluginLoadingError(PLUGIN_LOADING_ERROR_STORE_FULL)

            manifest = PluginManifest(
                plugin_id=plugin_id,
                version=plugin_version,
            )
            try:
                plugin = self._loader.load(manifest)
            except ExplicitPluginFactoryLoaderError as error:
                if (
                    error.code
                    == PLUGIN_FACTORY_LOADER_ERROR_UNSUPPORTED_MANIFEST
                ):
                    raise PluginLoadingError(
                        PLUGIN_LOADING_ERROR_MANIFEST_NOT_SUPPORTED
                    ) from None
                raise PluginLoadingError(
                    PLUGIN_LOADING_ERROR_LOAD_FAILED
                ) from None
            except Exception:
                raise PluginLoadingError(
                    PLUGIN_LOADING_ERROR_LOAD_FAILED
                ) from None

            plugin_name = self._validate_loaded_plugin(
                plugin,
                plugin_id=plugin_id,
                plugin_version=plugin_version,
            )
            record = LoadedPluginRecord(
                plugin_id=plugin_id,
                plugin_version=plugin_version,
                plugin_name=plugin_name,
                projected_capability_names=(
                    candidate.projected_capability_names
                ),
            )
            try:
                return self._store.add(record=record, plugin=plugin)
            except LoadedPluginStoreFullError:
                raise PluginLoadingError(
                    PLUGIN_LOADING_ERROR_STORE_FULL
                ) from None

    def resolve(
        self,
        plugin_id: str,
        plugin_version: str,
    ) -> LoadedPluginRecord | None:
        plugin_id, plugin_version = _validated_subject(
            plugin_id,
            plugin_version,
        )
        return self._store.resolve_record(plugin_id, plugin_version)

    def list_loaded(self) -> tuple[LoadedPluginRecord, ...]:
        return self._store.list_records()

    @staticmethod
    def _validate_loaded_plugin(
        plugin: object,
        *,
        plugin_id: str,
        plugin_version: str,
    ) -> str:
        try:
            loaded_id = plugin.id
            loaded_version = plugin.version
            loaded_name = plugin.name
            execute = plugin.execute
        except Exception:
            raise PluginLoadingError(
                PLUGIN_LOADING_ERROR_PLUGIN_INVALID
            ) from None

        if loaded_id != plugin_id or loaded_version != plugin_version:
            raise PluginLoadingError(
                PLUGIN_LOADING_ERROR_IDENTITY_MISMATCH
            )
        if (
            not isinstance(loaded_name, str)
            or not loaded_name
            or loaded_name != loaded_name.strip()
            or not callable(execute)
        ):
            raise PluginLoadingError(
                PLUGIN_LOADING_ERROR_PLUGIN_INVALID
            )
        return loaded_name
