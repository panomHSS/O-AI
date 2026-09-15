"""D58 immutable controlled Plugin registration activation contract."""

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


class PluginRegistrationActivationContractError(ValueError):
    """Safe D58 activation-contract error."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _text(value: object, *, code: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise PluginRegistrationActivationContractError(code)
    return value


@dataclass(frozen=True, slots=True)
class PluginRegistrationActivationRecord:
    """Metadata for one registered/permitted Plugin capability activation."""

    plugin_id: str
    plugin_version: str
    capability_name: str
    projected_capability_names: tuple[str, ...]
    capability_id: str
    module_adapter_id: str
    module_name: str
    operation: str
    effect: str
    data_class: str
    owner_approval_required: bool

    def __post_init__(self) -> None:
        plugin_id = _text(self.plugin_id, code="invalid_activation_plugin_id")
        plugin_version = _text(
            self.plugin_version,
            code="invalid_activation_plugin_version",
        )
        capability_name = _text(
            self.capability_name,
            code="invalid_activation_capability_name",
        )
        object.__setattr__(self, "plugin_id", plugin_id)
        object.__setattr__(self, "plugin_version", plugin_version)
        object.__setattr__(self, "capability_name", capability_name)

        if not isinstance(self.projected_capability_names, tuple):
            raise PluginRegistrationActivationContractError(
                "invalid_activation_projected_capabilities"
            )
        capabilities = tuple(
            _text(item, code="invalid_activation_projected_capabilities")
            for item in self.projected_capability_names
        )
        if (
            not capabilities
            or len(set(capabilities)) != len(capabilities)
            or capability_name not in capabilities
        ):
            raise PluginRegistrationActivationContractError(
                "invalid_activation_projected_capabilities"
            )
        object.__setattr__(
            self,
            "projected_capability_names",
            tuple(sorted(capabilities)),
        )

        object.__setattr__(
            self,
            "capability_id",
            _text(self.capability_id, code="invalid_activation_capability_id"),
        )
        adapter_id = _text(
            self.module_adapter_id,
            code="invalid_activation_module_adapter_id",
        )
        if not adapter_id.startswith("module."):
            raise PluginRegistrationActivationContractError(
                "invalid_activation_module_adapter_id"
            )
        object.__setattr__(self, "module_adapter_id", adapter_id)

        module_name = _text(
            self.module_name,
            code="invalid_activation_module_name",
        )
        if module_name.startswith("module."):
            raise PluginRegistrationActivationContractError(
                "invalid_activation_module_name"
            )
        object.__setattr__(self, "module_name", module_name)
        object.__setattr__(
            self,
            "operation",
            _text(self.operation, code="invalid_activation_operation"),
        )
        if self.effect not in _ALLOWED_EFFECTS:
            raise PluginRegistrationActivationContractError(
                "invalid_activation_effect"
            )
        if self.data_class not in _ALLOWED_DATA_CLASSES:
            raise PluginRegistrationActivationContractError(
                "invalid_activation_data_class"
            )
        if (
            type(self.owner_approval_required) is not bool
            or self.owner_approval_required is not True
        ):
            raise PluginRegistrationActivationContractError(
                "activation_owner_approval_must_be_required"
            )
