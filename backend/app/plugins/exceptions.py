class PluginError(Exception):
    """Base class for plugin framework errors."""


class PluginNotFoundError(PluginError):
    """Raised when a plugin cannot be found."""

    def __init__(self, plugin_id: str) -> None:
        super().__init__(
            f"Plugin '{plugin_id}' was not found.",
        )

class PluginLifecycleError(PluginError):
    """Raised when a plugin lifecycle transition is invalid."""

    def __init__(
        self,
        plugin_id: str,
        current_state: PluginState,
        target_state: PluginState,
    ) -> None:
        super().__init__(
            f"Plugin '{plugin_id}' cannot transition "
            f"from {current_state.name} "
            f"to {target_state.name}."
        )