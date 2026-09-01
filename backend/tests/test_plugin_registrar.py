import unittest

from app.plugins.default_plugin_registrar import (
    DefaultPluginRegistrar,
)
from app.plugins.echo import EchoPlugin

from app.plugins.plugin_manifest import PluginManifest


class PluginRegistrarTests(unittest.TestCase):
    """Tests for plugin registrar."""

    def test_registrar_can_be_created(
        self,
    ) -> None:
        registrar = DefaultPluginRegistrar(
            discovery=FakeDiscovery(),
            loader=FakeLoader(),
            registry=FakeRegistry(),
        )

        self.assertIsNotNone(
            registrar,
        )

    def test_registrar_registers_discovered_plugins(
        self,
    ) -> None:
        discovery = FakeDiscovery()
        loader = FakeLoader()
        registry = FakeRegistry()

        registrar = DefaultPluginRegistrar(
            discovery=discovery,
            loader=loader,
            registry=registry,
        )

        registrar.register_plugins()

        self.assertTrue(discovery.called)
        self.assertTrue(loader.called)
        self.assertTrue(registry.called)

class FakeDiscovery:
    def __init__(self):
        self.called = False

    def discover(self):
        self.called = True

        return [
            PluginManifest(
                plugin_id="echo",
                version="1.0.0",
            )
        ]

class FakeLoader:
    def __init__(self):
        self.called = False

    def load(
        self,
        manifest,
    ):
        self.called = True

        return EchoPlugin()

class FakeRegistry:
    def __init__(self):
        self.called = False
        self.plugins = []

    def register(
        self,
        plugin,
    ):
        self.called = True
        self.plugins.append(plugin)