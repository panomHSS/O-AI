from __future__ import annotations

from typing import override

from .capability import PluginCapability
from .capability_descriptor import CapabilityDescriptor
from .capability_registry import CapabilityRegistry


class InMemoryCapabilityRegistry(CapabilityRegistry):
    """In-memory implementation of the capability registry."""

    def __init__(self) -> None:
        self._capabilities: dict[str, CapabilityDescriptor] = {}

    @override
    def register(
        self,
        descriptor: CapabilityDescriptor,
    ) -> None:
        self._capabilities[
            descriptor.capability.name
        ] = descriptor

    @override
    def unregister(
        self,
        capability_name: str,
    ) -> None:
        del self._capabilities[
            capability_name
        ]

    @override
    def resolve(
        self,
        capability_name: str,
    ) -> PluginCapability:
        return self._capabilities[
            capability_name
        ].capability