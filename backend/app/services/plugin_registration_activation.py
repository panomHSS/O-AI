"""D58 controlled Plugin registration and D44 permission activation."""

from __future__ import annotations

import threading
from collections.abc import Iterable
from dataclasses import dataclass, field

from app.adapters.activated_plugin_module import ActivatedPluginModuleAdapter
from app.contracts.capability_permission import ExecutableCapabilityPermission
from app.contracts.plugin_permission_binding import PluginCapabilityPermissionBinding
from app.contracts.plugin_registration_activation import (
    PluginRegistrationActivationRecord,
)
from app.contracts.tool_module import ModuleAdapter
from app.services.plugin_module_exposure import (
    PluginModuleExposureError,
    PluginModuleExposureService,
)
from app.services.plugin_permission_binding import (
    PluginPermissionBindingError,
    PluginPermissionBindingService,
)

DEFAULT_MAX_PLUGIN_REGISTRATION_ACTIVATIONS = 100

PLUGIN_REGISTRATION_ACTIVATION_ERROR_INVALID_PLUGIN_ID = "invalid_activation_plugin_id"
PLUGIN_REGISTRATION_ACTIVATION_ERROR_INVALID_PLUGIN_VERSION = "invalid_activation_plugin_version"
PLUGIN_REGISTRATION_ACTIVATION_ERROR_INVALID_CAPABILITY_NAME = "invalid_activation_capability_name"
PLUGIN_REGISTRATION_ACTIVATION_ERROR_BINDING_NOT_FOUND = "activation_binding_not_found"
PLUGIN_REGISTRATION_ACTIVATION_ERROR_BINDING_INACTIVE = "activation_binding_inactive"
PLUGIN_REGISTRATION_ACTIVATION_ERROR_BINDING_RESOLUTION_FAILED = "activation_binding_resolution_failed"
PLUGIN_REGISTRATION_ACTIVATION_ERROR_EXPOSURE_NOT_FOUND = "activation_exposure_not_found"
PLUGIN_REGISTRATION_ACTIVATION_ERROR_EXPOSURE_INACTIVE = "activation_exposure_inactive"
PLUGIN_REGISTRATION_ACTIVATION_ERROR_ADAPTER_RESOLUTION_FAILED = "activation_adapter_resolution_failed"
PLUGIN_REGISTRATION_ACTIVATION_ERROR_SUBJECT_MISMATCH = "activation_subject_mismatch"
PLUGIN_REGISTRATION_ACTIVATION_ERROR_ADAPTER_ID_RESERVED = "activation_adapter_id_reserved"
PLUGIN_REGISTRATION_ACTIVATION_ERROR_CAPABILITY_ID_RESERVED = "activation_capability_id_reserved"
PLUGIN_REGISTRATION_ACTIVATION_ERROR_ROUTE_RESERVED = "activation_route_reserved"
PLUGIN_REGISTRATION_ACTIVATION_ERROR_DUPLICATE_ADAPTER_ID = "activation_duplicate_adapter_id"
PLUGIN_REGISTRATION_ACTIVATION_ERROR_DUPLICATE_CAPABILITY_ID = "activation_duplicate_capability_id"
PLUGIN_REGISTRATION_ACTIVATION_ERROR_DUPLICATE_ROUTE = "activation_duplicate_route"
PLUGIN_REGISTRATION_ACTIVATION_ERROR_STORE_FULL = "activation_store_full"
PLUGIN_REGISTRATION_ACTIVATION_ERROR_NOT_FOUND = "activation_not_found"


class PluginRegistrationActivationError(ValueError):
    """Safe D58 activation failure with a stable reason code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _validated_subject(
    plugin_id: object,
    plugin_version: object,
    capability_name: object,
) -> tuple[str, str, str]:
    if not isinstance(plugin_id, str) or not plugin_id or plugin_id != plugin_id.strip():
        raise PluginRegistrationActivationError(
            PLUGIN_REGISTRATION_ACTIVATION_ERROR_INVALID_PLUGIN_ID
        )
    if not isinstance(plugin_version, str) or not plugin_version or plugin_version != plugin_version.strip():
        raise PluginRegistrationActivationError(
            PLUGIN_REGISTRATION_ACTIVATION_ERROR_INVALID_PLUGIN_VERSION
        )
    if not isinstance(capability_name, str) or not capability_name or capability_name != capability_name.strip():
        raise PluginRegistrationActivationError(
            PLUGIN_REGISTRATION_ACTIVATION_ERROR_INVALID_CAPABILITY_NAME
        )
    return plugin_id, plugin_version, capability_name


@dataclass(frozen=True, slots=True)
class PluginRuntimeActivationSnapshot:
    """One coherent immutable D58 adapter + permission snapshot."""

    adapters: tuple[ModuleAdapter, ...] = field(default_factory=tuple)
    permissions: tuple[ExecutableCapabilityPermission, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.adapters, tuple):
            raise TypeError("D58 snapshot adapters must be a tuple.")
        if not isinstance(self.permissions, tuple):
            raise TypeError("D58 snapshot permissions must be a tuple.")


@dataclass(slots=True)
class _ActivationEntry:
    token: object
    record: PluginRegistrationActivationRecord
    adapter: ActivatedPluginModuleAdapter
    permission: ExecutableCapabilityPermission


class PluginRegistrationActivationStore:
    """Bounded process-local D58 activation authority store."""

    def __init__(self, *, max_activations: int = DEFAULT_MAX_PLUGIN_REGISTRATION_ACTIVATIONS) -> None:
        if isinstance(max_activations, bool) or not isinstance(max_activations, int) or max_activations < 1:
            raise ValueError("max_activations must be a positive integer.")
        self._max_activations = max_activations
        self._items: dict[tuple[str, str, str], _ActivationEntry] = {}
        self._adapter_ids: dict[str, tuple[str, str, str]] = {}
        self._capability_ids: dict[str, tuple[str, str, str]] = {}
        self._routes: dict[tuple[str, str], tuple[str, str, str]] = {}
        self._lock = threading.Lock()

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._items)

    def resolve_record(self, plugin_id: str, plugin_version: str, capability_name: str) -> PluginRegistrationActivationRecord | None:
        key = (plugin_id, plugin_version, capability_name)
        with self._lock:
            entry = self._items.get(key)
            return entry.record if entry is not None else None

    def list_records(self) -> tuple[PluginRegistrationActivationRecord, ...]:
        with self._lock:
            return tuple(self._items[key].record for key in sorted(self._items))

    def has_capacity_for(self, plugin_id: str, plugin_version: str, capability_name: str) -> bool:
        key = (plugin_id, plugin_version, capability_name)
        with self._lock:
            return key in self._items or len(self._items) < self._max_activations

    def add(
        self,
        *,
        token: object,
        record: PluginRegistrationActivationRecord,
        adapter: ActivatedPluginModuleAdapter,
        permission: ExecutableCapabilityPermission,
    ) -> PluginRegistrationActivationRecord:
        key = (record.plugin_id, record.plugin_version, record.capability_name)
        route = (record.module_adapter_id, record.operation)
        with self._lock:
            existing = self._items.get(key)
            if existing is not None:
                if existing.record != record:
                    raise PluginRegistrationActivationError(
                        PLUGIN_REGISTRATION_ACTIVATION_ERROR_SUBJECT_MISMATCH
                    )
                return existing.record
            adapter_owner = self._adapter_ids.get(record.module_adapter_id)
            if adapter_owner is not None and adapter_owner != key:
                raise PluginRegistrationActivationError(
                    PLUGIN_REGISTRATION_ACTIVATION_ERROR_DUPLICATE_ADAPTER_ID
                )
            capability_owner = self._capability_ids.get(record.capability_id)
            if capability_owner is not None and capability_owner != key:
                raise PluginRegistrationActivationError(
                    PLUGIN_REGISTRATION_ACTIVATION_ERROR_DUPLICATE_CAPABILITY_ID
                )
            route_owner = self._routes.get(route)
            if route_owner is not None and route_owner != key:
                raise PluginRegistrationActivationError(
                    PLUGIN_REGISTRATION_ACTIVATION_ERROR_DUPLICATE_ROUTE
                )
            if len(self._items) >= self._max_activations:
                raise PluginRegistrationActivationError(
                    PLUGIN_REGISTRATION_ACTIVATION_ERROR_STORE_FULL
                )
            self._items[key] = _ActivationEntry(
                token=token,
                record=record,
                adapter=adapter,
                permission=permission,
            )
            self._adapter_ids[record.module_adapter_id] = key
            self._capability_ids[record.capability_id] = key
            self._routes[route] = key
            return record

    def remove(self, plugin_id: str, plugin_version: str, capability_name: str) -> PluginRegistrationActivationRecord | None:
        key = (plugin_id, plugin_version, capability_name)
        with self._lock:
            entry = self._items.pop(key, None)
            if entry is None:
                return None
            self._drop_indexes(entry.record, key)
            return entry.record

    def remove_if_matches(self, record: PluginRegistrationActivationRecord, token: object) -> bool:
        key = (record.plugin_id, record.plugin_version, record.capability_name)
        with self._lock:
            entry = self._items.get(key)
            if entry is None or entry.record != record or entry.token is not token:
                return False
            del self._items[key]
            self._drop_indexes(record, key)
            return True

    def is_current_token(self, record: PluginRegistrationActivationRecord, token: object) -> bool:
        key = (record.plugin_id, record.plugin_version, record.capability_name)
        with self._lock:
            entry = self._items.get(key)
            return entry is not None and entry.record == record and entry.token is token

    def _validation_handles(self) -> tuple[tuple[PluginRegistrationActivationRecord, object], ...]:
        with self._lock:
            return tuple(
                (self._items[key].record, self._items[key].token)
                for key in sorted(self._items)
            )

    def _runtime_snapshot(self) -> PluginRuntimeActivationSnapshot:
        with self._lock:
            entries = tuple(self._items[key] for key in sorted(self._items))
            return PluginRuntimeActivationSnapshot(
                adapters=tuple(entry.adapter for entry in entries),
                permissions=tuple(entry.permission for entry in entries),
            )

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._adapter_ids.clear()
            self._capability_ids.clear()
            self._routes.clear()

    def _drop_indexes(self, record: PluginRegistrationActivationRecord, key: tuple[str, str, str]) -> None:
        if self._adapter_ids.get(record.module_adapter_id) == key:
            self._adapter_ids.pop(record.module_adapter_id, None)
        if self._capability_ids.get(record.capability_id) == key:
            self._capability_ids.pop(record.capability_id, None)
        route = (record.module_adapter_id, record.operation)
        if self._routes.get(route) == key:
            self._routes.pop(route, None)


class PluginRegistrationActivationService:
    """Activate exact current D56+D57 subjects into D31/D44 snapshots."""

    def __init__(
        self,
        *,
        binding_service: PluginPermissionBindingService,
        exposure_service: PluginModuleExposureService,
        store: PluginRegistrationActivationStore,
        reserved_adapter_ids: Iterable[str] = (),
        reserved_permissions: Iterable[ExecutableCapabilityPermission] = (),
    ) -> None:
        adapter_ids: set[str] = set()
        for adapter_id in reserved_adapter_ids:
            if not isinstance(adapter_id, str) or not adapter_id or adapter_id != adapter_id.strip():
                raise ValueError("D58 reserved adapter IDs must be non-empty trimmed strings.")
            adapter_ids.add(adapter_id)
        capability_ids: set[str] = set()
        routes: set[tuple[str, str]] = set()
        for permission in reserved_permissions:
            if not isinstance(permission, ExecutableCapabilityPermission):
                raise TypeError("D58 reserved permissions must be ExecutableCapabilityPermission values.")
            capability_ids.add(permission.capability_id)
            if permission.target_kind == "module":
                routes.add((permission.adapter_id, permission.operation))
        self._binding_service = binding_service
        self._exposure_service = exposure_service
        self._store = store
        self._reserved_adapter_ids = frozenset(adapter_ids)
        self._reserved_capability_ids = frozenset(capability_ids)
        self._reserved_routes = frozenset(routes)
        self._activation_lock = threading.Lock()

    def activate(self, plugin_id: str, plugin_version: str, capability_name: str) -> PluginRegistrationActivationRecord:
        plugin_id, plugin_version, capability_name = _validated_subject(plugin_id, plugin_version, capability_name)
        with self._activation_lock:
            record, delegate, permission = self._resolve_current_materialization(
                plugin_id, plugin_version, capability_name
            )
            existing = self._store.resolve_record(plugin_id, plugin_version, capability_name)
            if existing is not None:
                if existing != record:
                    raise PluginRegistrationActivationError(
                        PLUGIN_REGISTRATION_ACTIVATION_ERROR_SUBJECT_MISMATCH
                    )
                return existing
            if not self._store.has_capacity_for(plugin_id, plugin_version, capability_name):
                raise PluginRegistrationActivationError(
                    PLUGIN_REGISTRATION_ACTIVATION_ERROR_STORE_FULL
                )
            token = object()
            wrapper = ActivatedPluginModuleAdapter(
                record=record,
                activation_token=token,
                delegate=delegate,
                checker=self._is_activation_current,
            )
            return self._store.add(
                token=token,
                record=record,
                adapter=wrapper,
                permission=permission,
            )

    def deactivate(self, plugin_id: str, plugin_version: str, capability_name: str) -> PluginRegistrationActivationRecord | None:
        plugin_id, plugin_version, capability_name = _validated_subject(plugin_id, plugin_version, capability_name)
        with self._activation_lock:
            return self._store.remove(plugin_id, plugin_version, capability_name)

    def resolve(self, plugin_id: str, plugin_version: str, capability_name: str) -> PluginRegistrationActivationRecord | None:
        plugin_id, plugin_version, capability_name = _validated_subject(plugin_id, plugin_version, capability_name)
        return self._store.resolve_record(plugin_id, plugin_version, capability_name)

    def list_activations(self) -> tuple[PluginRegistrationActivationRecord, ...]:
        return self._store.list_records()

    def runtime_snapshot(self) -> PluginRuntimeActivationSnapshot:
        """Prune stale subjects then capture adapters+permissions under one lock."""
        for record, token in self._store._validation_handles():
            self._is_activation_current(record, token)
        return self._store._runtime_snapshot()

    def _resolve_current_materialization(
        self,
        plugin_id: str,
        plugin_version: str,
        capability_name: str,
    ) -> tuple[PluginRegistrationActivationRecord, ModuleAdapter, ExecutableCapabilityPermission]:
        binding = self._resolve_active_binding(plugin_id, plugin_version, capability_name)
        delegate = self._resolve_active_adapter(plugin_id, plugin_version, capability_name)
        if (
            delegate.adapter_id != binding.module_adapter_id
            or not isinstance(delegate.module_name, str)
            or not delegate.module_name
            or delegate.module_name != delegate.module_name.strip()
        ):
            raise PluginRegistrationActivationError(
                PLUGIN_REGISTRATION_ACTIVATION_ERROR_SUBJECT_MISMATCH
            )
        self._validate_reserved(binding)
        record = PluginRegistrationActivationRecord(
            plugin_id=binding.plugin_id,
            plugin_version=binding.plugin_version,
            capability_name=binding.capability_name,
            projected_capability_names=binding.projected_capability_names,
            capability_id=binding.capability_id,
            module_adapter_id=binding.module_adapter_id,
            module_name=delegate.module_name,
            operation=binding.operation,
            effect=binding.effect,
            data_class=binding.data_class,
            owner_approval_required=binding.owner_approval_required,
        )
        permission = ExecutableCapabilityPermission(
            capability_id=binding.capability_id,
            target_kind="module",
            adapter_id=binding.module_adapter_id,
            operation=binding.operation,
            effect=binding.effect,  # type: ignore[arg-type]
            data_class=binding.data_class,  # type: ignore[arg-type]
            owner_approval_required=binding.owner_approval_required,
        )
        return record, delegate, permission

    def _resolve_active_binding(self, plugin_id: str, plugin_version: str, capability_name: str) -> PluginCapabilityPermissionBinding:
        try:
            binding = self._binding_service._resolve_active_binding_for_activation(
                plugin_id, plugin_version, capability_name
            )
        except PluginPermissionBindingError:
            raise PluginRegistrationActivationError(
                PLUGIN_REGISTRATION_ACTIVATION_ERROR_BINDING_INACTIVE
            ) from None
        except Exception:
            raise PluginRegistrationActivationError(
                PLUGIN_REGISTRATION_ACTIVATION_ERROR_BINDING_RESOLUTION_FAILED
            ) from None
        if binding is None:
            raise PluginRegistrationActivationError(
                PLUGIN_REGISTRATION_ACTIVATION_ERROR_BINDING_NOT_FOUND
            )
        return binding

    def _resolve_active_adapter(self, plugin_id: str, plugin_version: str, capability_name: str) -> ModuleAdapter:
        try:
            adapter = self._exposure_service._resolve_active_adapter_for_registration(
                plugin_id, plugin_version, capability_name
            )
        except PluginModuleExposureError:
            raise PluginRegistrationActivationError(
                PLUGIN_REGISTRATION_ACTIVATION_ERROR_EXPOSURE_INACTIVE
            ) from None
        except Exception:
            raise PluginRegistrationActivationError(
                PLUGIN_REGISTRATION_ACTIVATION_ERROR_ADAPTER_RESOLUTION_FAILED
            ) from None
        if adapter is None:
            raise PluginRegistrationActivationError(
                PLUGIN_REGISTRATION_ACTIVATION_ERROR_EXPOSURE_NOT_FOUND
            )
        if not isinstance(adapter, ModuleAdapter):
            raise PluginRegistrationActivationError(
                PLUGIN_REGISTRATION_ACTIVATION_ERROR_ADAPTER_RESOLUTION_FAILED
            )
        return adapter

    def _validate_reserved(self, binding: PluginCapabilityPermissionBinding) -> None:
        if binding.module_adapter_id in self._reserved_adapter_ids:
            raise PluginRegistrationActivationError(
                PLUGIN_REGISTRATION_ACTIVATION_ERROR_ADAPTER_ID_RESERVED
            )
        if binding.capability_id in self._reserved_capability_ids:
            raise PluginRegistrationActivationError(
                PLUGIN_REGISTRATION_ACTIVATION_ERROR_CAPABILITY_ID_RESERVED
            )
        if (binding.module_adapter_id, binding.operation) in self._reserved_routes:
            raise PluginRegistrationActivationError(
                PLUGIN_REGISTRATION_ACTIVATION_ERROR_ROUTE_RESERVED
            )

    def _is_activation_current(self, record: PluginRegistrationActivationRecord, token: object) -> bool:
        if not self._store.is_current_token(record, token):
            return False
        try:
            current, _, _ = self._resolve_current_materialization(
                record.plugin_id,
                record.plugin_version,
                record.capability_name,
            )
            if current != record:
                raise PluginRegistrationActivationError(
                    PLUGIN_REGISTRATION_ACTIVATION_ERROR_SUBJECT_MISMATCH
                )
        except Exception:
            self._store.remove_if_matches(record, token)
            return False
        return True
