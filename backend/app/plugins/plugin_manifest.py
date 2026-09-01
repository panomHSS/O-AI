from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class PluginManifest:
    """Manifest describing a plugin."""

    plugin_id: str
    version: str
