from __future__ import annotations

from typing import override

from .base import Plugin
from .descriptor import PluginDescriptor
from .exceptions import PluginNotFoundError
from .lifecycle import PluginState
from .registration import PluginRegistration
from .registry import PluginRegistry


class InMemoryPluginRegistry(PluginRegistry):
    """In-memory implementation of the plugin registry."""

    def __init__(self) -> None:
        self._registrations: dict[str, PluginRegistration] = {}

    @override
    def register(
        self,
        plugin: Plugin,
    ) -> None:
        descriptor = PluginDescriptor(
            id=plugin.id,
            name=plugin.name,
            version=plugin.version,
            plugin=plugin,
        )

        self._registrations[plugin.id] = PluginRegistration(
            descriptor=descriptor,
            state=PluginState.REGISTERED,
        )

    @override
    def unregister(
        self,
        plugin_id: str,
    ) -> None:
        if plugin_id not in self._registrations:
            raise PluginNotFoundError(plugin_id)

        del self._registrations[plugin_id]

    @override
    def resolve(
        self,
        plugin_id: str,
    ) -> Plugin:
        registration = self._registrations.get(plugin_id)

        if registration is None:
            raise PluginNotFoundError(plugin_id)

        return registration.descriptor.plugin

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

    @override
    def state_of(
        self,
        plugin_id: str,
    ) -> PluginState:
        registration = self._registrations.get(plugin_id)

        if registration is None:
            raise PluginNotFoundError(plugin_id)

        return registration.state