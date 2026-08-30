from __future__ import annotations

from dataclasses import dataclass

from .base import Plugin


@dataclass(slots=True, frozen=True)
class PluginDescriptor:
    """Metadata describing a registered plugin."""

    id: str
    name: str
    version: str
    plugin: Plugin