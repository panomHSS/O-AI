from __future__ import annotations

from .base import Plugin


class EchoPlugin(Plugin):
    """Simple plugin used to validate the plugin framework."""

    def execute(
        self,
        context: PluginExecutionContext,
        request: PluginRequest,
    ) -> PluginResult:
        return PluginResult(
            content=request.content,
        )