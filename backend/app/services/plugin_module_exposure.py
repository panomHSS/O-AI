"""D56 governed Plugin Module exposure without registry or permission authority."""

from __future__ import annotations

import threading
from dataclasses import dataclass

from app.adapters.projected_plugin_module import (
    PLUGIN_MODULE_INVOCATION_ERROR_EXECUTION_FAILED,
    PLUGIN_MODULE_INVOCATION_ERROR_INACTIVE,
    PluginModuleInvocationError,
    ProjectedPluginModuleAdapter,
)
from app.contracts.plugin_candidate import PLUGIN_CANDIDATE_STATUS_PROJECTED_MATCH, PluginDiscoveryCandidate
from app.contracts.plugin_governance import PLUGIN_GOVERNANCE_STATE_ADMITTED
from app.contracts.plugin_loading import LoadedPluginRecord
from app.contracts.plugin_module_exposure import PluginModuleExposureRecord
from app.contracts.plugin_projection import PluginCapabilityProjection
from app.plugins.context import PluginExecutionContext
from app.plugins.request import PluginRequest
from app.plugins.response import PluginResult
from app.services.plugin_candidate_discovery import PluginCandidateDiscovery
from app.services.plugin_governance import PluginGovernanceService
from app.services.plugin_loading import LoadedPluginStore, PluginLoadingError, PluginLoadingService
from app.services.plugin_projection_catalog import PluginProjectionCatalog, PluginProjectionCatalogError

DEFAULT_MAX_PLUGIN_MODULE_EXPOSURES = 100
PLUGIN_MODULE_EXPOSURE_ERROR_INVALID_PLUGIN_ID = "invalid_exposure_plugin_id"
PLUGIN_MODULE_EXPOSURE_ERROR_INVALID_PLUGIN_VERSION = "invalid_exposure_plugin_version"
PLUGIN_MODULE_EXPOSURE_ERROR_INVALID_CAPABILITY_NAME = "invalid_exposure_capability_name"
PLUGIN_MODULE_EXPOSURE_ERROR_GOVERNANCE_NOT_FOUND = "exposure_governance_not_found"
PLUGIN_MODULE_EXPOSURE_ERROR_GOVERNANCE_NOT_ADMITTED = "exposure_governance_not_admitted"
PLUGIN_MODULE_EXPOSURE_ERROR_CANDIDATE_RESOLUTION_FAILED = "exposure_candidate_resolution_failed"
PLUGIN_MODULE_EXPOSURE_ERROR_CANDIDATE_NOT_FOUND = "exposure_candidate_not_found"
PLUGIN_MODULE_EXPOSURE_ERROR_CANDIDATE_NOT_ELIGIBLE = "exposure_candidate_not_eligible"
PLUGIN_MODULE_EXPOSURE_ERROR_PROJECTION_NOT_FOUND = "exposure_projection_not_found"
PLUGIN_MODULE_EXPOSURE_ERROR_PROJECTION_VERSION_MISMATCH = "exposure_projection_version_mismatch"
PLUGIN_MODULE_EXPOSURE_ERROR_PLUGIN_NOT_LOADED = "exposure_plugin_not_loaded"
PLUGIN_MODULE_EXPOSURE_ERROR_SUBJECT_MISMATCH = "exposure_subject_mismatch"
PLUGIN_MODULE_EXPOSURE_ERROR_DUPLICATE_TARGET = "exposure_duplicate_target"
PLUGIN_MODULE_EXPOSURE_ERROR_STORE_FULL = "exposure_store_full"
PLUGIN_MODULE_EXPOSURE_ERROR_BINDING_FAILED = "exposure_binding_failed"

class PluginModuleExposureError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)

def _validated_subject(plugin_id: object, plugin_version: object, capability_name: object) -> tuple[str, str, str]:
    if not isinstance(plugin_id, str) or not plugin_id or plugin_id != plugin_id.strip():
        raise PluginModuleExposureError(PLUGIN_MODULE_EXPOSURE_ERROR_INVALID_PLUGIN_ID)
    if not isinstance(plugin_version, str) or not plugin_version or plugin_version != plugin_version.strip():
        raise PluginModuleExposureError(PLUGIN_MODULE_EXPOSURE_ERROR_INVALID_PLUGIN_VERSION)
    if not isinstance(capability_name, str) or not capability_name or capability_name != capability_name.strip():
        raise PluginModuleExposureError(PLUGIN_MODULE_EXPOSURE_ERROR_INVALID_CAPABILITY_NAME)
    return plugin_id, plugin_version, capability_name

@dataclass(slots=True)
class _PluginModuleExposureEntry:
    record: PluginModuleExposureRecord
    adapter: ProjectedPluginModuleAdapter

class PluginModuleExposureStore:
    def __init__(self, *, max_exposures: int = DEFAULT_MAX_PLUGIN_MODULE_EXPOSURES) -> None:
        if isinstance(max_exposures, bool) or not isinstance(max_exposures, int) or max_exposures < 1:
            raise ValueError("max_exposures must be a positive integer.")
        self._max_exposures = max_exposures
        self._items: dict[tuple[str, str, str], _PluginModuleExposureEntry] = {}
        self._targets: dict[tuple[str, str], tuple[str, str, str]] = {}
        self._lock = threading.Lock()

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._items)

    def resolve_record(self, plugin_id: str, plugin_version: str, capability_name: str) -> PluginModuleExposureRecord | None:
        key = (plugin_id, plugin_version, capability_name)
        with self._lock:
            entry = self._items.get(key)
            return entry.record if entry is not None else None

    def list_records(self) -> tuple[PluginModuleExposureRecord, ...]:
        with self._lock:
            return tuple(sorted((entry.record for entry in self._items.values()), key=lambda r: (r.plugin_id, r.plugin_version, r.capability_name)))
    def has_capacity_for(self, plugin_id: str, plugin_version: str, capability_name: str) -> bool:
        key = (plugin_id, plugin_version, capability_name)
        with self._lock:
            return key in self._items or len(self._items) < self._max_exposures

    def target_owner(self, module_adapter_id: str, operation: str) -> tuple[str, str, str] | None:
        with self._lock:
            return self._targets.get((module_adapter_id, operation))

    def add(self, *, record: PluginModuleExposureRecord, adapter: ProjectedPluginModuleAdapter) -> PluginModuleExposureRecord:
        key = (record.plugin_id, record.plugin_version, record.capability_name)
        target = (record.module_adapter_id, record.operation)
        with self._lock:
            existing = self._items.get(key)
            if existing is not None:
                if existing.record != record:
                    raise PluginModuleExposureError(PLUGIN_MODULE_EXPOSURE_ERROR_SUBJECT_MISMATCH)
                return existing.record
            owner = self._targets.get(target)
            if owner is not None and owner != key:
                raise PluginModuleExposureError(PLUGIN_MODULE_EXPOSURE_ERROR_DUPLICATE_TARGET)
            if len(self._items) >= self._max_exposures:
                raise PluginModuleExposureError(PLUGIN_MODULE_EXPOSURE_ERROR_STORE_FULL)
            self._items[key] = _PluginModuleExposureEntry(record=record, adapter=adapter)
            self._targets[target] = key
            return record

    def _resolve_adapter(self, plugin_id: str, plugin_version: str, capability_name: str) -> ProjectedPluginModuleAdapter | None:
        key = (plugin_id, plugin_version, capability_name)
        with self._lock:
            entry = self._items.get(key)
            return entry.adapter if entry is not None else None

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._targets.clear()

@dataclass(frozen=True, slots=True)
class _CurrentExposureSubject:
    candidate: PluginDiscoveryCandidate
    loaded: LoadedPluginRecord
    projection: PluginCapabilityProjection
    record: PluginModuleExposureRecord

class PluginModuleExposureService:
    def __init__(self, *, projection_catalog: PluginProjectionCatalog, candidate_discovery: PluginCandidateDiscovery, governance: PluginGovernanceService, loading: PluginLoadingService, loaded_store: LoadedPluginStore, exposure_store: PluginModuleExposureStore) -> None:
        self._projection_catalog = projection_catalog
        self._candidate_discovery = candidate_discovery
        self._governance = governance
        self._loading = loading
        self._loaded_store = loaded_store
        self._store = exposure_store
        self._exposure_lock = threading.Lock()

    def expose(self, plugin_id: str, plugin_version: str, capability_name: str) -> PluginModuleExposureRecord:
        plugin_id, plugin_version, capability_name = _validated_subject(plugin_id, plugin_version, capability_name)
        with self._exposure_lock:
            current = self._resolve_current_subject(plugin_id, plugin_version, capability_name)
            existing = self._store.resolve_record(plugin_id, plugin_version, capability_name)
            if existing is not None:
                if existing != current.record:
                    raise PluginModuleExposureError(PLUGIN_MODULE_EXPOSURE_ERROR_SUBJECT_MISMATCH)
                return existing
            owner = self._store.target_owner(current.record.module_adapter_id, current.record.operation)
            if owner is not None and owner != (plugin_id, plugin_version, capability_name):
                raise PluginModuleExposureError(PLUGIN_MODULE_EXPOSURE_ERROR_DUPLICATE_TARGET)
            if not self._store.has_capacity_for(plugin_id, plugin_version, capability_name):
                raise PluginModuleExposureError(PLUGIN_MODULE_EXPOSURE_ERROR_STORE_FULL)
            adapter = ProjectedPluginModuleAdapter(
                plugin_id=plugin_id,
                plugin_version=plugin_version,
                projected_capability_names=current.record.projected_capability_names,
                capability_name=capability_name,
                adapter_id=current.record.module_adapter_id,
                module_name=current.record.module_name,
                operation=current.record.operation,
                invoker=self._invoke_active_exposure,
            )
            return self._store.add(record=current.record, adapter=adapter)

    def resolve(self, plugin_id: str, plugin_version: str, capability_name: str) -> PluginModuleExposureRecord | None:
        plugin_id, plugin_version, capability_name = _validated_subject(plugin_id, plugin_version, capability_name)
        return self._store.resolve_record(plugin_id, plugin_version, capability_name)

    def list_exposures(self) -> tuple[PluginModuleExposureRecord, ...]:
        return self._store.list_records()
    def _resolve_active_record_for_binding(
        self,
        plugin_id: str,
        plugin_version: str,
        capability_name: str,
    ) -> PluginModuleExposureRecord | None:
        """Package-private metadata-only freshness seam for D57."""
        plugin_id, plugin_version, capability_name = _validated_subject(
            plugin_id, plugin_version, capability_name
        )
        stored = self._store.resolve_record(plugin_id, plugin_version, capability_name)
        if stored is None:
            return None
        current = self._resolve_current_subject(plugin_id, plugin_version, capability_name)
        if stored != current.record:
            raise PluginModuleExposureError(PLUGIN_MODULE_EXPOSURE_ERROR_SUBJECT_MISMATCH)
        return stored

    def _resolve_current_subject(self, plugin_id: str, plugin_version: str, capability_name: str) -> _CurrentExposureSubject:
        try:
            decision = self._governance.resolve(plugin_id, plugin_version)
        except Exception:
            raise PluginModuleExposureError(PLUGIN_MODULE_EXPOSURE_ERROR_BINDING_FAILED) from None
        if decision is None:
            raise PluginModuleExposureError(PLUGIN_MODULE_EXPOSURE_ERROR_GOVERNANCE_NOT_FOUND)
        if decision.state != PLUGIN_GOVERNANCE_STATE_ADMITTED:
            raise PluginModuleExposureError(PLUGIN_MODULE_EXPOSURE_ERROR_GOVERNANCE_NOT_ADMITTED)
        try:
            candidates = self._candidate_discovery.discover_candidates()
        except Exception:
            raise PluginModuleExposureError(PLUGIN_MODULE_EXPOSURE_ERROR_CANDIDATE_RESOLUTION_FAILED) from None
        candidate = next((item for item in candidates if item.plugin_id == plugin_id and item.plugin_version == plugin_version), None)
        if candidate is None:
            raise PluginModuleExposureError(PLUGIN_MODULE_EXPOSURE_ERROR_CANDIDATE_NOT_FOUND)
        if candidate.status != PLUGIN_CANDIDATE_STATUS_PROJECTED_MATCH:
            raise PluginModuleExposureError(PLUGIN_MODULE_EXPOSURE_ERROR_CANDIDATE_NOT_ELIGIBLE)
        if candidate.projected_capability_names != decision.projected_capability_names or capability_name not in candidate.projected_capability_names:
            raise PluginModuleExposureError(PLUGIN_MODULE_EXPOSURE_ERROR_SUBJECT_MISMATCH)
        try:
            loaded = self._loading.resolve(plugin_id, plugin_version)
        except Exception:
            raise PluginModuleExposureError(PLUGIN_MODULE_EXPOSURE_ERROR_BINDING_FAILED) from None
        if loaded is None:
            raise PluginModuleExposureError(PLUGIN_MODULE_EXPOSURE_ERROR_PLUGIN_NOT_LOADED)
        if loaded.projected_capability_names != candidate.projected_capability_names:
            raise PluginModuleExposureError(PLUGIN_MODULE_EXPOSURE_ERROR_SUBJECT_MISMATCH)
        try:
            projection = self._projection_catalog.resolve(plugin_id, capability_name)
        except PluginProjectionCatalogError:
            raise PluginModuleExposureError(PLUGIN_MODULE_EXPOSURE_ERROR_PROJECTION_NOT_FOUND) from None
        except Exception:
            raise PluginModuleExposureError(PLUGIN_MODULE_EXPOSURE_ERROR_BINDING_FAILED) from None
        if projection.plugin_version != plugin_version:
            raise PluginModuleExposureError(PLUGIN_MODULE_EXPOSURE_ERROR_PROJECTION_VERSION_MISMATCH)
        record = PluginModuleExposureRecord(
            plugin_id=plugin_id,
            plugin_version=plugin_version,
            capability_name=capability_name,
            projected_capability_names=candidate.projected_capability_names,
            module_adapter_id=projection.module_adapter_id,
            module_name=self._module_name_from_adapter_id(projection.module_adapter_id),
            operation=projection.operation,
        )
        return _CurrentExposureSubject(candidate=candidate, loaded=loaded, projection=projection, record=record)

    @staticmethod
    def _module_name_from_adapter_id(module_adapter_id: str) -> str:
        prefix = "module."
        if not isinstance(module_adapter_id, str) or not module_adapter_id.startswith(prefix) or len(module_adapter_id) == len(prefix):
            raise PluginModuleExposureError(PLUGIN_MODULE_EXPOSURE_ERROR_BINDING_FAILED)
        return module_adapter_id[len(prefix):]

    def _invoke_active_exposure(self, plugin_id: str, plugin_version: str, projected_capability_names: tuple[str, ...], capability_name: str, module_adapter_id: str, operation: str, content: str) -> PluginResult:
        try:
            current = self._resolve_current_subject(plugin_id, plugin_version, capability_name)
            if current.record.projected_capability_names != projected_capability_names or current.record.module_adapter_id != module_adapter_id or current.record.operation != operation:
                raise PluginModuleExposureError(PLUGIN_MODULE_EXPOSURE_ERROR_SUBJECT_MISMATCH)
            stored = self._store.resolve_record(plugin_id, plugin_version, capability_name)
            if stored is None or stored != current.record:
                raise PluginModuleExposureError(PLUGIN_MODULE_EXPOSURE_ERROR_SUBJECT_MISMATCH)
            return self._loaded_store._invoke_loaded_for_module(
                plugin_id=plugin_id,
                plugin_version=plugin_version,
                projected_capability_names=projected_capability_names,
                context=PluginExecutionContext(),
                request=PluginRequest(content=content),
            )
        except PluginModuleExposureError:
            raise PluginModuleInvocationError(PLUGIN_MODULE_INVOCATION_ERROR_INACTIVE) from None
        except PluginLoadingError:
            raise PluginModuleInvocationError(PLUGIN_MODULE_INVOCATION_ERROR_INACTIVE) from None
        except Exception:
            raise PluginModuleInvocationError(PLUGIN_MODULE_INVOCATION_ERROR_EXECUTION_FAILED) from None
