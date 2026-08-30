from __future__ import annotations

from typing import Protocol

from .base import Plugin
from .lifecycle import PluginState


class PluginRegistry(Protocol):
    """Plugin registry contract."""

    def register(
        self,
        plugin: Plugin,
    ) -> None:
        ...

    def unregister(
        self,
        plugin_id: str,
    ) -> None:
        ...

    def resolve(
        self,
        plugin_id: str,
    ) -> Plugin:
        ...

    def transition(
        self,
        plugin_id: str,
        state: PluginState,
    ) -> None:
        ...