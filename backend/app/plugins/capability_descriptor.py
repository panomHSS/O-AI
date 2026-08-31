from __future__ import annotations

from dataclasses import dataclass

from .capability import PluginCapability


@dataclass(slots=True, frozen=True)
class CapabilityDescriptor:
    """Metadata describing a plugin capability."""

    capability: PluginCapability