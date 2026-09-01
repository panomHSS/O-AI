import unittest

from app.plugins.default_plugin_loader import (
    DefaultPluginLoader,
)


class PluginLoaderTests(unittest.TestCase):
    """Tests for plugin loader."""

    def test_loader_can_be_created(
        self,
    ) -> None:
        loader = DefaultPluginLoader()

        self.assertIsNotNone(
            loader,
        )