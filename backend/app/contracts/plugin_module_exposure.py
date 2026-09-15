"""D56 immutable metadata contract for governed Plugin Module exposure."""

from __future__ import annotations

from dataclasses import dataclass


PLUGIN_MODULE_EXPOSURE_CONTRACT_ERROR_INVALID_PLUGIN_ID = "invalid_exposure_plugin_id"
PLUGIN_MODULE_EXPOSURE_CONTRACT_ERROR_INVALID_PLUGIN_VERSION = "invalid_exposure_plugin_version"
PLUGIN_MODULE_EXPOSURE_CONTRACT_ERROR_INVALID_CAPABILITY_NAME = "invalid_exposure_capability_name"
PLUGIN_MODULE_EXPOSURE_CONTRACT_ERROR_INVALID_CAPABILITIES = "invalid_exposure_capabilities"
PLUGIN_MODULE_EXPOSURE_CONTRACT_ERROR_INVALID_ADAPTER_ID = "invalid_exposure_adapter_id"
PLUGIN_MODULE_EXPOSURE_CONTRACT_ERROR_INVALID_MODULE_NAME = "invalid_exposure_module_name"
PLUGIN_MODULE_EXPOSURE_CONTRACT_ERROR_INVALID_OPERATION = "invalid_exposure_operation"


class PluginModuleExposureContractError(ValueError):
    """Safe D56 exposure-contract error with a stable reason code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _validated_text(value: object, *, code: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise PluginModuleExposureContractError(code)
    return value


@dataclass(frozen=True, slots=True)
class PluginModuleExposureRecord:
    """Immutable metadata for one capability-specific Module exposure."""

    plugin_id: str
    plugin_version: str
    capability_name: str
    projected_capability_names: tuple[str, ...]
    module_adapter_id: str
    module_name: str
    operation: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "plugin_id", _validated_text(self.plugin_id, code=PLUGIN_MODULE_EXPOSURE_CONTRACT_ERROR_INVALID_PLUGIN_ID))
        object.__setattr__(self, "plugin_version", _validated_text(self.plugin_version, code=PLUGIN_MODULE_EXPOSURE_CONTRACT_ERROR_INVALID_PLUGIN_VERSION))
        capability_name = _validated_text(self.capability_name, code=PLUGIN_MODULE_EXPOSURE_CONTRACT_ERROR_INVALID_CAPABILITY_NAME)
        object.__setattr__(self, "capability_name", capability_name)
        if not isinstance(self.projected_capability_names, tuple):
            raise PluginModuleExposureContractError(PLUGIN_MODULE_EXPOSURE_CONTRACT_ERROR_INVALID_CAPABILITIES)
        capabilities = tuple(_validated_text(item, code=PLUGIN_MODULE_EXPOSURE_CONTRACT_ERROR_INVALID_CAPABILITIES) for item in self.projected_capability_names)
        if not capabilities or len(set(capabilities)) != len(capabilities) or capability_name not in capabilities:
            raise PluginModuleExposureContractError(PLUGIN_MODULE_EXPOSURE_CONTRACT_ERROR_INVALID_CAPABILITIES)
        object.__setattr__(self, "projected_capability_names", tuple(sorted(capabilities)))
        adapter_id = _validated_text(self.module_adapter_id, code=PLUGIN_MODULE_EXPOSURE_CONTRACT_ERROR_INVALID_ADAPTER_ID)
        if not adapter_id.startswith("module."):
            raise PluginModuleExposureContractError(PLUGIN_MODULE_EXPOSURE_CONTRACT_ERROR_INVALID_ADAPTER_ID)
        object.__setattr__(self, "module_adapter_id", adapter_id)
        module_name = _validated_text(self.module_name, code=PLUGIN_MODULE_EXPOSURE_CONTRACT_ERROR_INVALID_MODULE_NAME)
        if module_name.startswith("module."):
            raise PluginModuleExposureContractError(PLUGIN_MODULE_EXPOSURE_CONTRACT_ERROR_INVALID_MODULE_NAME)
        object.__setattr__(self, "module_name", module_name)
        object.__setattr__(self, "operation", _validated_text(self.operation, code=PLUGIN_MODULE_EXPOSURE_CONTRACT_ERROR_INVALID_OPERATION))
