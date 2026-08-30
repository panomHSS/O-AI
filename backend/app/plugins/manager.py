from __future__ import annotations
from .registry import PluginRegistry


class PluginManager:
    """Dispatches plugin execution requests."""

class PluginManager:
    """Dispatches plugin execution requests."""

    def __init__(
        self,
        registry: PluginRegistry,
    ) -> None:
        self._registry = registry