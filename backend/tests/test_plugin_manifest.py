import unittest

from app.plugins.plugin_manifest import PluginManifest


class PluginManifestTests(unittest.TestCase):
    """Tests for plugin manifest."""

    def test_manifest_can_be_created(
        self,
    ) -> None:
        manifest = PluginManifest(
            plugin_id="echo",
            version="1.0.0",
        )

        self.assertEqual(
            manifest.plugin_id,
            "echo",
        )

        self.assertEqual(
            manifest.version,
            "1.0.0",
        )