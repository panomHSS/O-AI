from __future__ import annotations

from .base import Plugin
from .context import PluginExecutionContext
from .request import PluginRequest
from .response import PluginResult


class EchoPlugin(Plugin):
    """Simple plugin used to validate the plugin framework."""

    @property
    def id(self) -> str:
        return "echo"


    @property
    def name(self) -> str:
        return "Echo Plugin"


    @property
    def version(self) -> str:
        return "1.0.0"

    def execute(
        self,
        context: PluginExecutionContext,
        request: PluginRequest,
    ) -> PluginResult:
        return PluginResult(
            content=request.content,
        )