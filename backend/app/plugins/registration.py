from __future__ import annotations

from dataclasses import dataclass

from .descriptor import PluginDescriptor
from .lifecycle import PluginState


@dataclass(slots=True)
class PluginRegistration:
    """Runtime registration for a plugin."""

    descriptor: PluginDescriptor
    state: PluginState