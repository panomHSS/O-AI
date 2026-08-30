from __future__ import annotations

from .context import PluginExecutionContext
from .registry import PluginRegistry
from .request import PluginRequest
from .response import PluginResult


class PluginManager:

    def __init__(
        self,
        runtime: PluginRuntime,
    ) -> None:
        self._runtime = runtime

    def dispatch(
        self,
        plugin_id: str,
        context: PluginExecutionContext,
        request: PluginRequest,
    ) -> PluginResult:
        return self._runtime.execute(
            plugin_id=plugin_id,
            context=context,
            request=request,
        )