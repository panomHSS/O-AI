from __future__ import annotations

from typing import override

from .context import PluginExecutionContext
from .registry import PluginRegistry
from .request import PluginRequest
from .response import PluginResult
from .runtime import PluginRuntime


class DefaultPluginRuntime(PluginRuntime):
    """Default implementation of the plugin runtime."""

    def __init__(
        self,
        registry: PluginRegistry,
    ) -> None:
        self._registry = registry

    @override
    def execute(
        self,
        plugin_id: str,
        context: PluginExecutionContext,
        request: PluginRequest,
    ) -> PluginResult:
        plugin = self._registry.resolve(
            plugin_id,
        )

        return plugin.execute(
            context,
            request,
        )