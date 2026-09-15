"""D57 fail-closed Plugin capability / permission intent binding."""

from __future__ import annotations

import threading
from collections.abc import Iterable

from app.contracts.capability_permission import ExecutableCapabilityPermission
from app.contracts.plugin_module_exposure import PluginModuleExposureRecord
from app.contracts.plugin_permission_binding import (
    PluginCapabilityPermissionBinding,
    PluginCapabilityPermissionProfile,
)
from app.services.plugin_module_exposure import (
    PluginModuleExposureError,
    PluginModuleExposureService,
)

DEFAULT_MAX_PLUGIN_PERMISSION_BINDINGS = 100

PLUGIN_PERMISSION_BINDING_ERROR_INVALID_PLUGIN_ID = "invalid_binding_plugin_id"
PLUGIN_PERMISSION_BINDING_ERROR_INVALID_PLUGIN_VERSION = "invalid_binding_plugin_version"
PLUGIN_PERMISSION_BINDING_ERROR_INVALID_CAPABILITY_NAME = "invalid_binding_capability_name"
PLUGIN_PERMISSION_BINDING_ERROR_EXPOSURE_NOT_FOUND = "binding_exposure_not_found"
PLUGIN_PERMISSION_BINDING_ERROR_EXPOSURE_INACTIVE = "binding_exposure_inactive"
PLUGIN_PERMISSION_BINDING_ERROR_EXPOSURE_RESOLUTION_FAILED = "binding_exposure_resolution_failed"
PLUGIN_PERMISSION_BINDING_ERROR_PROFILE_NOT_FOUND = "binding_profile_not_found"
PLUGIN_PERMISSION_BINDING_ERROR_PROFILE_TARGET_MISMATCH = "binding_profile_target_mismatch"
PLUGIN_PERMISSION_BINDING_ERROR_CAPABILITY_ID_RESERVED = "binding_capability_id_reserved"
PLUGIN_PERMISSION_BINDING_ERROR_ROUTE_RESERVED = "binding_route_reserved"
PLUGIN_PERMISSION_BINDING_ERROR_DUPLICATE_CAPABILITY_ID = "binding_duplicate_capability_id"
PLUGIN_PERMISSION_BINDING_ERROR_DUPLICATE_ROUTE = "binding_duplicate_route"
PLUGIN_PERMISSION_BINDING_ERROR_SUBJECT_MISMATCH = "binding_subject_mismatch"
PLUGIN_PERMISSION_BINDING_ERROR_STORE_FULL = "binding_store_full"

PLUGIN_PERMISSION_PROFILE_ERROR_NOT_FOUND = "permission_profile_not_found"
PLUGIN_PERMISSION_PROFILE_ERROR_DUPLICATE_SOURCE = "duplicate_permission_profile_source"
PLUGIN_PERMISSION_PROFILE_ERROR_DUPLICATE_CAPABILITY_ID = "duplicate_permission_profile_capability_id"
PLUGIN_PERMISSION_PROFILE_ERROR_DUPLICATE_ROUTE = "duplicate_permission_profile_route"


class PluginPermissionBindingError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class PluginPermissionProfileCatalogError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _validated_subject(plugin_id: object, plugin_version: object, capability_name: object) -> tuple[str, str, str]:
    if not isinstance(plugin_id, str) or not plugin_id or plugin_id != plugin_id.strip():
        raise PluginPermissionBindingError(PLUGIN_PERMISSION_BINDING_ERROR_INVALID_PLUGIN_ID)
    if not isinstance(plugin_version, str) or not plugin_version or plugin_version != plugin_version.strip():
        raise PluginPermissionBindingError(PLUGIN_PERMISSION_BINDING_ERROR_INVALID_PLUGIN_VERSION)
    if not isinstance(capability_name, str) or not capability_name or capability_name != capability_name.strip():
        raise PluginPermissionBindingError(PLUGIN_PERMISSION_BINDING_ERROR_INVALID_CAPABILITY_NAME)
    return plugin_id, plugin_version, capability_name


PRODUCTION_PLUGIN_CAPABILITY_PERMISSION_PROFILES: tuple[PluginCapabilityPermissionProfile, ...] = ()


class PluginPermissionProfileCatalog:
    """Immutable exact-match O-AI-controlled permission-profile snapshot."""

    def __init__(self, profiles: Iterable[PluginCapabilityPermissionProfile] = ()) -> None:
        by_source: dict[tuple[str, str, str], PluginCapabilityPermissionProfile] = {}
        capability_ids: set[str] = set()
        routes: set[tuple[str, str]] = set()
        for profile in profiles:
            if not isinstance(profile, PluginCapabilityPermissionProfile):
                raise TypeError("D57 profiles must be PluginCapabilityPermissionProfile values.")
            source = (profile.plugin_id, profile.plugin_version, profile.capability_name)
            route = (profile.module_adapter_id, profile.operation)
            if source in by_source:
                raise PluginPermissionProfileCatalogError(PLUGIN_PERMISSION_PROFILE_ERROR_DUPLICATE_SOURCE)
            if profile.capability_id in capability_ids:
                raise PluginPermissionProfileCatalogError(PLUGIN_PERMISSION_PROFILE_ERROR_DUPLICATE_CAPABILITY_ID)
            if route in routes:
                raise PluginPermissionProfileCatalogError(PLUGIN_PERMISSION_PROFILE_ERROR_DUPLICATE_ROUTE)
            by_source[source] = profile
            capability_ids.add(profile.capability_id)
            routes.add(route)
        self._by_source = by_source
        self._profiles = tuple(sorted(by_source.values(), key=lambda p: (p.plugin_id, p.plugin_version, p.capability_name)))

    @property
    def profiles(self) -> tuple[PluginCapabilityPermissionProfile, ...]:
        return self._profiles

    def resolve(self, plugin_id: str, plugin_version: str, capability_name: str) -> PluginCapabilityPermissionProfile:
        profile = self._by_source.get((plugin_id, plugin_version, capability_name))
        if profile is None:
            raise PluginPermissionProfileCatalogError(PLUGIN_PERMISSION_PROFILE_ERROR_NOT_FOUND)
        return profile


class PluginPermissionBindingStore:
    """Bounded process-local metadata-only binding store."""

    def __init__(self, *, max_bindings: int = DEFAULT_MAX_PLUGIN_PERMISSION_BINDINGS) -> None:
        if isinstance(max_bindings, bool) or not isinstance(max_bindings, int) or max_bindings < 1:
            raise ValueError("max_bindings must be a positive integer.")
        self._max_bindings = max_bindings
        self._items: dict[tuple[str, str, str], PluginCapabilityPermissionBinding] = {}
        self._capability_ids: dict[str, tuple[str, str, str]] = {}
        self._routes: dict[tuple[str, str], tuple[str, str, str]] = {}
        self._lock = threading.Lock()

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._items)

    def resolve(self, plugin_id: str, plugin_version: str, capability_name: str) -> PluginCapabilityPermissionBinding | None:
        with self._lock:
            return self._items.get((plugin_id, plugin_version, capability_name))

    def list_bindings(self) -> tuple[PluginCapabilityPermissionBinding, ...]:
        with self._lock:
            return tuple(self._items[key] for key in sorted(self._items))

    def has_capacity_for(self, plugin_id: str, plugin_version: str, capability_name: str) -> bool:
        key = (plugin_id, plugin_version, capability_name)
        with self._lock:
            return key in self._items or len(self._items) < self._max_bindings

    def add(self, binding: PluginCapabilityPermissionBinding) -> PluginCapabilityPermissionBinding:
        if not isinstance(binding, PluginCapabilityPermissionBinding):
            raise TypeError("D57 store accepts PluginCapabilityPermissionBinding values only.")
        key = (binding.plugin_id, binding.plugin_version, binding.capability_name)
        route = (binding.module_adapter_id, binding.operation)
        with self._lock:
            existing = self._items.get(key)
            if existing is not None:
                if existing != binding:
                    raise PluginPermissionBindingError(PLUGIN_PERMISSION_BINDING_ERROR_SUBJECT_MISMATCH)
                return existing
            capability_owner = self._capability_ids.get(binding.capability_id)
            if capability_owner is not None and capability_owner != key:
                raise PluginPermissionBindingError(PLUGIN_PERMISSION_BINDING_ERROR_DUPLICATE_CAPABILITY_ID)
            route_owner = self._routes.get(route)
            if route_owner is not None and route_owner != key:
                raise PluginPermissionBindingError(PLUGIN_PERMISSION_BINDING_ERROR_DUPLICATE_ROUTE)
            if len(self._items) >= self._max_bindings:
                raise PluginPermissionBindingError(PLUGIN_PERMISSION_BINDING_ERROR_STORE_FULL)
            self._items[key] = binding
            self._capability_ids[binding.capability_id] = key
            self._routes[route] = key
            return binding

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._capability_ids.clear()
            self._routes.clear()


class PluginPermissionBindingService:
    """Bind active D56 exposure metadata to explicit permission intent only."""

    def __init__(
        self,
        *,
        exposure_service: PluginModuleExposureService,
        profile_catalog: PluginPermissionProfileCatalog,
        store: PluginPermissionBindingStore,
        reserved_permissions: Iterable[ExecutableCapabilityPermission] = (),
    ) -> None:
        self._exposure_service = exposure_service
        self._profile_catalog = profile_catalog
        self._store = store
        reserved_capability_ids: set[str] = set()
        reserved_routes: set[tuple[str, str]] = set()
        for permission in reserved_permissions:
            if not isinstance(permission, ExecutableCapabilityPermission):
                raise TypeError("D57 reserved permissions must be ExecutableCapabilityPermission values.")
            reserved_capability_ids.add(permission.capability_id)
            if permission.target_kind == "module":
                reserved_routes.add((permission.adapter_id, permission.operation))
        self._reserved_capability_ids = frozenset(reserved_capability_ids)
        self._reserved_routes = frozenset(reserved_routes)
        self._bind_lock = threading.Lock()

    def bind(self, plugin_id: str, plugin_version: str, capability_name: str) -> PluginCapabilityPermissionBinding:
        plugin_id, plugin_version, capability_name = _validated_subject(plugin_id, plugin_version, capability_name)
        with self._bind_lock:
            exposure = self._resolve_active_exposure(plugin_id, plugin_version, capability_name)
            profile = self._resolve_profile(plugin_id, plugin_version, capability_name)
            if profile.module_adapter_id != exposure.module_adapter_id or profile.operation != exposure.operation:
                raise PluginPermissionBindingError(PLUGIN_PERMISSION_BINDING_ERROR_PROFILE_TARGET_MISMATCH)
            self._validate_reserved(profile)
            binding = PluginCapabilityPermissionBinding(
                plugin_id=plugin_id,
                plugin_version=plugin_version,
                capability_name=capability_name,
                projected_capability_names=exposure.projected_capability_names,
                capability_id=profile.capability_id,
                module_adapter_id=profile.module_adapter_id,
                operation=profile.operation,
                effect=profile.effect,
                data_class=profile.data_class,
                owner_approval_required=profile.owner_approval_required,
            )
            existing = self._store.resolve(plugin_id, plugin_version, capability_name)
            if existing is not None:
                if existing != binding:
                    raise PluginPermissionBindingError(PLUGIN_PERMISSION_BINDING_ERROR_SUBJECT_MISMATCH)
                return existing
            if not self._store.has_capacity_for(plugin_id, plugin_version, capability_name):
                raise PluginPermissionBindingError(PLUGIN_PERMISSION_BINDING_ERROR_STORE_FULL)
            return self._store.add(binding)

    def resolve(self, plugin_id: str, plugin_version: str, capability_name: str) -> PluginCapabilityPermissionBinding | None:
        plugin_id, plugin_version, capability_name = _validated_subject(plugin_id, plugin_version, capability_name)
        return self._store.resolve(plugin_id, plugin_version, capability_name)

    def list_bindings(self) -> tuple[PluginCapabilityPermissionBinding, ...]:
        return self._store.list_bindings()

    def _resolve_active_exposure(self, plugin_id: str, plugin_version: str, capability_name: str) -> PluginModuleExposureRecord:
        try:
            exposure = self._exposure_service._resolve_active_record_for_binding(plugin_id, plugin_version, capability_name)
        except PluginModuleExposureError:
            raise PluginPermissionBindingError(PLUGIN_PERMISSION_BINDING_ERROR_EXPOSURE_INACTIVE) from None
        except Exception:
            raise PluginPermissionBindingError(PLUGIN_PERMISSION_BINDING_ERROR_EXPOSURE_RESOLUTION_FAILED) from None
        if exposure is None:
            raise PluginPermissionBindingError(PLUGIN_PERMISSION_BINDING_ERROR_EXPOSURE_NOT_FOUND)
        return exposure

    def _resolve_profile(self, plugin_id: str, plugin_version: str, capability_name: str) -> PluginCapabilityPermissionProfile:
        try:
            return self._profile_catalog.resolve(plugin_id, plugin_version, capability_name)
        except PluginPermissionProfileCatalogError:
            raise PluginPermissionBindingError(PLUGIN_PERMISSION_BINDING_ERROR_PROFILE_NOT_FOUND) from None
        except Exception:
            raise PluginPermissionBindingError(PLUGIN_PERMISSION_BINDING_ERROR_PROFILE_NOT_FOUND) from None

    def _validate_reserved(self, profile: PluginCapabilityPermissionProfile) -> None:
        if profile.capability_id in self._reserved_capability_ids:
            raise PluginPermissionBindingError(PLUGIN_PERMISSION_BINDING_ERROR_CAPABILITY_ID_RESERVED)
        if (profile.module_adapter_id, profile.operation) in self._reserved_routes:
            raise PluginPermissionBindingError(PLUGIN_PERMISSION_BINDING_ERROR_ROUTE_RESERVED)
