from __future__ import annotations

from typing import Protocol

from .context import PluginExecutionContext
from .request import PluginRequest
from .response import PluginResult


class PluginRuntimeHook(Protocol):
    """Plugin runtime hook contract."""

    def before_execute(
        self,
        plugin_id: str,
        context: PluginExecutionContext,
        request: PluginRequest,
    ) -> None:
        ...

    def after_execute(
        self,
        plugin_id: str,
        context: PluginExecutionContext,
        request: PluginRequest,
        result: PluginResult,
    ) -> None:
        ...

    def on_error(
        self,
        plugin_id: str,
        context: PluginExecutionContext,
        request: PluginRequest,
        error: Exception,
    ) -> None:
        ...