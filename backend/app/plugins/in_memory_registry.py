from __future__ import annotations

from .base import Plugin
from .exceptions import PluginNotFoundError
from .lifecycle import PluginState
from .registry import PluginRegistry
from typing import override

class InMemoryPluginRegistry(PluginRegistry):
    @override
    def register(
        self,
        plugin: Plugin,
    ) -> None:
        ...

    @override
    def unregister(
        self,
        plugin_id: str,
    ) -> None:
        ...

    @override
    def resolve(
        self,
        plugin_id: str,
    ) -> Plugin:
        ...

    @override
    def transition(
        self,
        plugin_id: str,
        state: PluginState,
    ) -> None:
        """Transition a plugin to a new lifecycle state."""

        registration = self._registrations.get(plugin_id)

        if registration is None:
            raise PluginNotFoundError(plugin_id)

        registration.state = state