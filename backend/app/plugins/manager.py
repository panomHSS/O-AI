from __future__ import annotations

from .context import PluginExecutionContext
from .registry import PluginRegistry
from .request import PluginRequest
from .response import PluginResult


class PluginManager:
    """Dispatches plugin execution requests."""

    def __init__(
        self,
        registry: PluginRegistry,
    ) -> None:
        self._registry = registry

    def dispatch(
        self,
        plugin_id: str,
        context: PluginExecutionContext,
        request: PluginRequest,
    ) -> PluginResult:
        """Dispatch a request to a plugin."""

        plugin = self._registry.resolve(
            plugin_id,
        )

        # TODO(D17.7):
        # Route execution through PluginRuntime.
        
        return plugin.execute(
            context,
            request,
        )