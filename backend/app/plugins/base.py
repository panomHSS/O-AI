from __future__ import annotations

from typing import Protocol

from .context import PluginExecutionContext
from .request import PluginRequest
from .response import PluginResult


class Plugin(Protocol):
    """Plugin contract."""

    @property
    def id(self) -> str:
        ...

    @property
    def name(self) -> str:
        ...

    @property
    def version(self) -> str:
        ...

    def execute(
        self,
        context: PluginExecutionContext,
        request: PluginRequest,
    ) -> PluginResult:
        ...