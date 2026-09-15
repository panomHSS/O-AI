import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.api import dependencies
from app.contracts.google_calendar import (
    GOOGLE_CALENDAR_ADAPTER_ID,
    GOOGLE_CALENDAR_CAPABILITY_ID,
    GOOGLE_CALENDAR_CAPABILITY_NAME,
    GOOGLE_CALENDAR_PLUGIN_ID,
    GOOGLE_CALENDAR_PLUGIN_VERSION,
)
from app.plugins.plugin_manifest import PluginManifest


class RaisingTokenSettings:
    oai_github_public_repo_connector_enabled = False
    oai_google_calendar_connector_enabled = True

    @property
    def oai_google_oauth_client_id(self):
        raise AssertionError("Plugin lifecycle must not read OAuth config.")

    @property
    def oai_google_oauth_client_secret(self):
        raise AssertionError("Plugin lifecycle must not read OAuth secrets.")

    @property
    def oai_google_oauth_redirect_uri(self):
        raise AssertionError("Plugin lifecycle must not read OAuth config.")

    @property
    def oai_oauth_token_encryption_key(self):
        raise AssertionError("Plugin lifecycle must not read encryption keys.")


class GoogleCalendarD63IntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        dependencies.get_plugin_governance_store().clear()
        dependencies.get_loaded_plugin_store().clear()
        dependencies.get_plugin_module_exposure_store().clear()
        dependencies.get_plugin_permission_binding_store().clear()
        dependencies.get_plugin_registration_activation_store().clear()
        dependencies.get_credential_access_broker.cache_clear()
        dependencies.get_credential_profile_catalog.cache_clear()
        dependencies.get_credential_secret_source.cache_clear()
        dependencies.get_controlled_plugin_loader.cache_clear()
        dependencies.get_plugin_loading_service.cache_clear()
        dependencies.get_first_party_plugin_enablement_service.cache_clear()

    def tearDown(self) -> None:
        dependencies.get_plugin_governance_store().clear()
        dependencies.get_loaded_plugin_store().clear()
        dependencies.get_plugin_module_exposure_store().clear()
        dependencies.get_plugin_permission_binding_store().clear()
        dependencies.get_plugin_registration_activation_store().clear()
        dependencies.get_credential_access_broker.cache_clear()
        dependencies.get_credential_profile_catalog.cache_clear()
        dependencies.get_credential_secret_source.cache_clear()
        dependencies.get_controlled_plugin_loader.cache_clear()
        dependencies.get_plugin_loading_service.cache_clear()
        dependencies.get_first_party_plugin_enablement_service.cache_clear()

    def test_static_loader_knows_exact_google_calendar_identity(self) -> None:
        plugin = dependencies.get_controlled_plugin_loader().load(
            PluginManifest(
                plugin_id=GOOGLE_CALENDAR_PLUGIN_ID,
                version=GOOGLE_CALENDAR_PLUGIN_VERSION,
            )
        )
        self.assertEqual(plugin.id, GOOGLE_CALENDAR_PLUGIN_ID)
        self.assertEqual(plugin.version, GOOGLE_CALENDAR_PLUGIN_VERSION)

    def test_enabled_lifecycle_activates_without_reading_secret(self) -> None:
        with patch.object(
            dependencies,
            "get_settings",
            return_value=RaisingTokenSettings(),
        ):
            snapshot = dependencies.get_plugin_runtime_activation_snapshot()

        self.assertEqual(
            tuple(adapter.adapter_id for adapter in snapshot.adapters),
            (GOOGLE_CALENDAR_ADAPTER_ID,),
        )
        self.assertEqual(
            tuple(
                permission.capability_id
                for permission in snapshot.permissions
            ),
            (GOOGLE_CALENDAR_CAPABILITY_ID,),
        )
        permission = snapshot.permissions[0]
        self.assertEqual(permission.effect, "read")
        self.assertEqual(permission.data_class, "owner_data")
        self.assertTrue(permission.owner_approval_required)

    def test_disabled_lifecycle_remains_default_deny(self) -> None:
        settings = SimpleNamespace(
            oai_github_public_repo_connector_enabled=False,
            oai_google_calendar_connector_enabled=False,
        )
        with patch.object(
            dependencies,
            "get_settings",
            return_value=settings,
        ):
            snapshot = dependencies.get_plugin_runtime_activation_snapshot()
        self.assertEqual(snapshot.adapters, ())
        self.assertEqual(snapshot.permissions, ())


if __name__ == "__main__":
    unittest.main()
