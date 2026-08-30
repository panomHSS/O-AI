from dataclasses import dataclass


@dataclass(slots=True)
class PluginRequest:
    """Plugin execution request."""

    content: str