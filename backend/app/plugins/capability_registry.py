from __future__ import annotations

from typing import Protocol

from .capability import PluginCapability
from .capability_descriptor import CapabilityDescriptor


class CapabilityRegistry(Protocol):
    """Contract for plugin capability registries."""

    def register(
        self,
        descriptor: CapabilityDescriptor,
    ) -> None:
        ...

    def unregister(
        self,
        capability_name: str,
    ) -> None:
        ...

    def resolve(
        self,
        capability_name: str,
    ) -> PluginCapability:
        ...