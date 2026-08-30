from enum import Enum


class PluginState(str, Enum):
    REGISTERED = "registered"
    INITIALIZED = "initialized"
    READY = "ready"
    DISABLED = "disabled"
    FAILED = "failed"