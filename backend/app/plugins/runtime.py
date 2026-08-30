from __future__ import annotations

from typing import Protocol

from .context import PluginExecutionContext
from .request import PluginRequest
from .response import PluginResult


class PluginRuntime(Protocol):
    """Plugin runtime contract."""

    def execute(
        self,
        plugin_id: str,
        context: PluginExecutionContext,
        request: PluginRequest,
    ) -> PluginResult:
        ...