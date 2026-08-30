from __future__ import annotations

from .base import Plugin


class PluginRegistry:

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