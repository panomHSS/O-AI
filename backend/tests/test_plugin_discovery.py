import unittest

from app.plugins.default_plugin_discovery import (
    DefaultPluginDiscovery,
)


class PluginDiscoveryTests(unittest.TestCase):
    """Tests for plugin discovery."""

    def test_discovery_can_be_created(
        self,
    ) -> None:
        discovery = DefaultPluginDiscovery()

        self.assertIsNotNone(
            discovery,
        )