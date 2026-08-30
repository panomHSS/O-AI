@dataclass(slots=True, frozen=True)
class PluginDescriptor:
    """Metadata describing a registered plugin."""

    id: str
    name: str
    version: str
    plugin: Plugin