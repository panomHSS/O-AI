from dataclasses import dataclass


@dataclass(slots=True)
class PluginExecutionContext:
    """Execution context passed to plugins."""