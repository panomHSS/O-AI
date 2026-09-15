"""D55 immutable metadata contract for controlled Plugin loading."""

from __future__ import annotations

from dataclasses import dataclass


PLUGIN_LOADING_CONTRACT_ERROR_INVALID_PLUGIN_ID = "invalid_loading_plugin_id"
PLUGIN_LOADING_CONTRACT_ERROR_INVALID_PLUGIN_VERSION = (
    "invalid_loading_plugin_version"
)
PLUGIN_LOADING_CONTRACT_ERROR_INVALID_PLUGIN_NAME = "invalid_loaded_plugin_name"
PLUGIN_LOADING_CONTRACT_ERROR_INVALID_CAPABILITIES = (
    "invalid_loaded_plugin_capabilities"
)


class PluginLoadingContractError(ValueError):
    """Safe D55 loading-contract error with a stable reason code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _validated_text(value: object, *, code: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise PluginLoadingContractError(code)
    return value


@dataclass(frozen=True, slots=True)
class LoadedPluginRecord:
    """Immutable metadata for one internally held loaded Plugin instance."""

    plugin_id: str
    plugin_version: str
    plugin_name: str
    projected_capability_names: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "plugin_id",
            _validated_text(
                self.plugin_id,
                code=PLUGIN_LOADING_CONTRACT_ERROR_INVALID_PLUGIN_ID,
            ),
        )
        object.__setattr__(
            self,
            "plugin_version",
            _validated_text(
                self.plugin_version,
                code=PLUGIN_LOADING_CONTRACT_ERROR_INVALID_PLUGIN_VERSION,
            ),
        )
        object.__setattr__(
            self,
            "plugin_name",
            _validated_text(
                self.plugin_name,
                code=PLUGIN_LOADING_CONTRACT_ERROR_INVALID_PLUGIN_NAME,
            ),
        )

        if not isinstance(self.projected_capability_names, tuple):
            raise PluginLoadingContractError(
                PLUGIN_LOADING_CONTRACT_ERROR_INVALID_CAPABILITIES
            )
        capabilities = tuple(
            _validated_text(
                capability,
                code=PLUGIN_LOADING_CONTRACT_ERROR_INVALID_CAPABILITIES,
            )
            for capability in self.projected_capability_names
        )
        if not capabilities or len(set(capabilities)) != len(capabilities):
            raise PluginLoadingContractError(
                PLUGIN_LOADING_CONTRACT_ERROR_INVALID_CAPABILITIES
            )
        object.__setattr__(
            self,
            "projected_capability_names",
            tuple(sorted(capabilities)),
        )
