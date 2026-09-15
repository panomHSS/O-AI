"""D52 immutable metadata contract for Plugin -> Module capability projection."""

from __future__ import annotations

from dataclasses import dataclass


PLUGIN_PROJECTION_ERROR_INVALID_PLUGIN_ID = "invalid_plugin_id"
PLUGIN_PROJECTION_ERROR_INVALID_PLUGIN_VERSION = "invalid_plugin_version"
PLUGIN_PROJECTION_ERROR_INVALID_CAPABILITY_NAME = "invalid_capability_name"
PLUGIN_PROJECTION_ERROR_INVALID_DESCRIPTION = "invalid_description"
PLUGIN_PROJECTION_ERROR_INVALID_ADAPTER_ID = "invalid_adapter_id"
PLUGIN_PROJECTION_ERROR_INVALID_OPERATION = "invalid_operation"


class PluginProjectionContractError(ValueError):
    """Safe D52 contract error with a stable reason code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _validated_text(value: object, *, code: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise PluginProjectionContractError(code)
    return value


@dataclass(frozen=True, slots=True)
class PluginCapabilityProjection:
    """Metadata-only description of one possible Plugin -> Module exposure."""

    plugin_id: str
    plugin_version: str
    capability_name: str
    description: str
    module_adapter_id: str
    operation: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "plugin_id",
            _validated_text(
                self.plugin_id,
                code=PLUGIN_PROJECTION_ERROR_INVALID_PLUGIN_ID,
            ),
        )
        object.__setattr__(
            self,
            "plugin_version",
            _validated_text(
                self.plugin_version,
                code=PLUGIN_PROJECTION_ERROR_INVALID_PLUGIN_VERSION,
            ),
        )
        object.__setattr__(
            self,
            "capability_name",
            _validated_text(
                self.capability_name,
                code=PLUGIN_PROJECTION_ERROR_INVALID_CAPABILITY_NAME,
            ),
        )
        object.__setattr__(
            self,
            "description",
            _validated_text(
                self.description,
                code=PLUGIN_PROJECTION_ERROR_INVALID_DESCRIPTION,
            ),
        )
        module_adapter_id = _validated_text(
            self.module_adapter_id,
            code=PLUGIN_PROJECTION_ERROR_INVALID_ADAPTER_ID,
        )
        if not module_adapter_id.startswith("module."):
            raise PluginProjectionContractError(
                PLUGIN_PROJECTION_ERROR_INVALID_ADAPTER_ID
            )
        object.__setattr__(self, "module_adapter_id", module_adapter_id)
        object.__setattr__(
            self,
            "operation",
            _validated_text(
                self.operation,
                code=PLUGIN_PROJECTION_ERROR_INVALID_OPERATION,
            ),
        )
