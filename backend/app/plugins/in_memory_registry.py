from __future__ import annotations

from typing import override

from .base import Plugin
from .descriptor import PluginDescriptor
from .lifecycle import PluginState
from .registration import PluginRegistration
from .registry import PluginRegistry
from .exceptions import PluginLifecycleError
from .exceptions import PluginNotFoundError


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
    def state_of(
        self,
        plugin_id: str,
    ) -> PluginState:
        registration = self._registrations.get(plugin_id)

        if registration is None:
            raise PluginNotFoundError(plugin_id)

        return registration.state

    @override
    def transition(
        self,
        plugin_id: str,
        state: PluginState,
    ) -> None:
        registration = self._registrations.get(plugin_id)

        if registration is None:
            raise PluginNotFoundError(plugin_id)

        current = registration.state

        allowed_transitions = {
            PluginState.REGISTERED: {
                PluginState.INITIALIZED,
            },
            PluginState.INITIALIZED: {
                PluginState.READY,
            },
            PluginState.READY: {
                PluginState.DISABLED,
                PluginState.FAILED,
            },
            PluginState.DISABLED: set(),
            PluginState.FAILED: set(),
        }

        if state not in allowed_transitions[current]:
            raise PluginLifecycleError(
                plugin_id=plugin_id,
                current_state=current,
                target_state=state,
            )

        registration.state = state