"""D57 immutable Plugin capability / permission binding contracts."""

from __future__ import annotations

from dataclasses import dataclass

_ALLOWED_EFFECTS = frozenset(
    {"none", "read", "write", "external_side_effect", "process_execution"}
)
_ALLOWED_DATA_CLASSES = frozenset(
    {
        "none",
        "system_metadata",
        "workspace_metadata",
        "workspace_content",
        "owner_data",
        "external_data",
    }
)


class PluginPermissionBindingContractError(ValueError):
    """Safe D57 contract error with a stable reason code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _text(value: object, *, code: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise PluginPermissionBindingContractError(code)
    return value


def _module_adapter_id(value: object) -> str:
    value = _text(value, code="invalid_binding_module_adapter_id")
    if not value.startswith("module."):
        raise PluginPermissionBindingContractError(
            "invalid_binding_module_adapter_id"
        )
    return value


def _effect(value: object) -> str:
    if value not in _ALLOWED_EFFECTS:
        raise PluginPermissionBindingContractError("invalid_binding_effect")
    return value  # type: ignore[return-value]


def _data_class(value: object) -> str:
    if value not in _ALLOWED_DATA_CLASSES:
        raise PluginPermissionBindingContractError(
            "invalid_binding_data_class"
        )
    return value  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class PluginCapabilityPermissionProfile:
    """O-AI-controlled permission intent for one exact Plugin capability."""

    plugin_id: str
    plugin_version: str
    capability_name: str
    capability_id: str
    module_adapter_id: str
    operation: str
    effect: str
    data_class: str
    owner_approval_required: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "plugin_id", _text(self.plugin_id, code="invalid_binding_plugin_id"))
        object.__setattr__(self, "plugin_version", _text(self.plugin_version, code="invalid_binding_plugin_version"))
        object.__setattr__(self, "capability_name", _text(self.capability_name, code="invalid_binding_capability_name"))
        object.__setattr__(self, "capability_id", _text(self.capability_id, code="invalid_binding_capability_id"))
        object.__setattr__(self, "module_adapter_id", _module_adapter_id(self.module_adapter_id))
        object.__setattr__(self, "operation", _text(self.operation, code="invalid_binding_operation"))
        object.__setattr__(self, "effect", _effect(self.effect))
        object.__setattr__(self, "data_class", _data_class(self.data_class))
        if type(self.owner_approval_required) is not bool or self.owner_approval_required is not True:
            raise PluginPermissionBindingContractError(
                "binding_owner_approval_must_be_required"
            )


@dataclass(frozen=True, slots=True)
class PluginCapabilityPermissionBinding:
    """Metadata-only binding; this is not an active D44 permission."""

    plugin_id: str
    plugin_version: str
    capability_name: str
    projected_capability_names: tuple[str, ...]
    capability_id: str
    module_adapter_id: str
    operation: str
    effect: str
    data_class: str
    owner_approval_required: bool

    def __post_init__(self) -> None:
        plugin_id = _text(self.plugin_id, code="invalid_binding_plugin_id")
        plugin_version = _text(self.plugin_version, code="invalid_binding_plugin_version")
        capability_name = _text(self.capability_name, code="invalid_binding_capability_name")
        object.__setattr__(self, "plugin_id", plugin_id)
        object.__setattr__(self, "plugin_version", plugin_version)
        object.__setattr__(self, "capability_name", capability_name)
        if not isinstance(self.projected_capability_names, tuple):
            raise PluginPermissionBindingContractError(
                "invalid_binding_projected_capabilities"
            )
        capabilities = tuple(
            _text(item, code="invalid_binding_projected_capabilities")
            for item in self.projected_capability_names
        )
        if not capabilities or len(set(capabilities)) != len(capabilities) or capability_name not in capabilities:
            raise PluginPermissionBindingContractError(
                "invalid_binding_projected_capabilities"
            )
        object.__setattr__(self, "projected_capability_names", tuple(sorted(capabilities)))
        object.__setattr__(self, "capability_id", _text(self.capability_id, code="invalid_binding_capability_id"))
        object.__setattr__(self, "module_adapter_id", _module_adapter_id(self.module_adapter_id))
        object.__setattr__(self, "operation", _text(self.operation, code="invalid_binding_operation"))
        object.__setattr__(self, "effect", _effect(self.effect))
        object.__setattr__(self, "data_class", _data_class(self.data_class))
        if type(self.owner_approval_required) is not bool or self.owner_approval_required is not True:
            raise PluginPermissionBindingContractError(
                "binding_owner_approval_must_be_required"
            )
