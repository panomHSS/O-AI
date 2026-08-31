from __future__ import annotations

from dataclasses import dataclass

from .capability_descriptor import CapabilityDescriptor


@dataclass(slots=True, frozen=True)
class PluginMetadata:
    """Metadata describing a plugin."""

    author: str
    description: str
    capabilities: list[CapabilityDescriptor]