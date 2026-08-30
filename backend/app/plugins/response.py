from dataclasses import dataclass


@dataclass(slots=True)
class PluginResult:
    """Plugin execution result."""

    content: str