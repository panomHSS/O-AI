import json
import unittest

from pydantic import SecretStr

from app.contracts.credential import CredentialProfile
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep
from app.contracts.gmail import (
    GMAIL_ADAPTER_ID,
    GMAIL_CAPABILITY_ID,
    GMAIL_CREDENTIAL_AUTH_SCHEME,
    GMAIL_CREDENTIAL_PROVIDER_ID,
    GMAIL_CREDENTIAL_SCOPE,
    GMAIL_CREDENTIAL_SECRET_REF,
    GMAIL_OPERATION,
    GMAIL_PLUGIN_ID,
    GMAIL_PLUGIN_VERSION,
    GMAIL_READ_CAPABILITY_NAME,
    GMAIL_READ_CREDENTIAL_PROFILE_ID,
    GmailReadResult,
)
from app.plugins.default_plugin_discovery import DefaultPluginDiscovery
from app.plugins.explicit_plugin_factory_loader import ExplicitPluginFactoryLoader
from app.plugins.gmail import GmailPlugin
from app.services.capability_permission_policy import PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS
from app.services.credential_access_broker import (
    CredentialAccessBroker,
    StaticCredentialSecretSource,
)
from app.services.credential_profile_catalog import CredentialProfileCatalog
from app.services.plugin_candidate_discovery import PluginCandidateDiscovery
from app.services.plugin_governance import PluginGovernanceDecisionStore, PluginGovernanceService
from app.services.plugin_loading import LoadedPluginStore, PluginLoadingService
from app.services.plugin_module_exposure import PluginModuleExposureService, PluginModuleExposureStore
from app.services.plugin_permission_binding import (
    PRODUCTION_PLUGIN_CAPABILITY_PERMISSION_PROFILES,
    PluginPermissionBindingService,
    PluginPermissionBindingStore,
    PluginPermissionProfileCatalog,
)
from app.services.plugin_projection_catalog import (
    PRODUCTION_PLUGIN_CAPABILITY_PROJECTIONS,
    PluginProjectionCatalog,
)
from app.services.plugin_registration_activation import (
    PluginRegistrationActivationService,
    PluginRegistrationActivationStore,
)


class FakeReader:
    def __init__(self):
        self.calls = 0

    def read_messages(self, access_token, *, query):
        self.calls += 1
        return GmailReadResult(())


class GmailLifecycleTests(unittest.TestCase):
    def compose(self):
        reader = FakeReader()
        profile = CredentialProfile(
            profile_id=GMAIL_READ_CREDENTIAL_PROFILE_ID,
            plugin_id=GMAIL_PLUGIN_ID,
            plugin_version=GMAIL_PLUGIN_VERSION,
            capability_name=GMAIL_READ_CAPABILITY_NAME,
            provider_id=GMAIL_CREDENTIAL_PROVIDER_ID,
            auth_scheme=GMAIL_CREDENTIAL_AUTH_SCHEME,
            required_scopes=(GMAIL_CREDENTIAL_SCOPE,),
            secret_ref=GMAIL_CREDENTIAL_SECRET_REF,
        )
        broker = CredentialAccessBroker(
            profile_catalog=CredentialProfileCatalog((profile,)),
            secret_source=StaticCredentialSecretSource(
                {GMAIL_CREDENTIAL_SECRET_REF: SecretStr("gmail-secret-never-log")}
            ),
        )
        projection_catalog = PluginProjectionCatalog(
            PRODUCTION_PLUGIN_CAPABILITY_PROJECTIONS
        )
        candidate_discovery = PluginCandidateDiscovery(
            discovery=DefaultPluginDiscovery(),
            projection_catalog=projection_catalog,
        )
        governance = PluginGovernanceService(
            candidate_discovery=candidate_discovery,
            store=PluginGovernanceDecisionStore(),
        )
        loading_store = LoadedPluginStore()
        loading = PluginLoadingService(
            candidate_discovery=candidate_discovery,
            governance=governance,
            loader=ExplicitPluginFactoryLoader(
                {(GMAIL_PLUGIN_ID, GMAIL_PLUGIN_VERSION): lambda: GmailPlugin(credential_broker=broker, client=reader)}
            ),
            store=loading_store,
        )
        exposure = PluginModuleExposureService(
            projection_catalog=projection_catalog,
            candidate_discovery=candidate_discovery,
            governance=governance,
            loading=loading,
            loaded_store=loading_store,
            exposure_store=PluginModuleExposureStore(),
        )
        binding = PluginPermissionBindingService(
            exposure_service=exposure,
            profile_catalog=PluginPermissionProfileCatalog(
                PRODUCTION_PLUGIN_CAPABILITY_PERMISSION_PROFILES
            ),
            store=PluginPermissionBindingStore(),
            reserved_permissions=PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS,
        )
        activation = PluginRegistrationActivationService(
            binding_service=binding,
            exposure_service=exposure,
            store=PluginRegistrationActivationStore(),
            reserved_adapter_ids=tuple(
                permission.adapter_id
                for permission in PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS
            ),
            reserved_permissions=PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS,
        )
        return reader, governance, loading, exposure, binding, activation

    def activate(self):
        parts = self.compose()
        reader, governance, loading, exposure, binding, activation = parts
        governance.admit(GMAIL_PLUGIN_ID, GMAIL_PLUGIN_VERSION)
        loading.load(GMAIL_PLUGIN_ID, GMAIL_PLUGIN_VERSION)
        exposure.expose(GMAIL_PLUGIN_ID, GMAIL_PLUGIN_VERSION, GMAIL_READ_CAPABILITY_NAME)
        binding.bind(GMAIL_PLUGIN_ID, GMAIL_PLUGIN_VERSION, GMAIL_READ_CAPABILITY_NAME)
        activation.activate(GMAIL_PLUGIN_ID, GMAIL_PLUGIN_VERSION, GMAIL_READ_CAPABILITY_NAME)
        self.assertEqual(reader.calls, 0)
        return parts

    def test_discovery_knows_gmail_but_does_not_execute(self):
        reader, governance, loading, exposure, binding, activation = self.compose()
        candidates = {item.plugin_id: item for item in loading._candidate_discovery.discover_candidates()}
        self.assertIn(GMAIL_PLUGIN_ID, candidates)
        self.assertEqual(candidates[GMAIL_PLUGIN_ID].projected_capability_names, (GMAIL_READ_CAPABILITY_NAME,))
        self.assertIsNone(governance.resolve(GMAIL_PLUGIN_ID, GMAIL_PLUGIN_VERSION))
        self.assertEqual(reader.calls, 0)

    def test_activation_snapshot_has_exact_owner_data_permission_and_no_read_yet(self):
        reader, _, _, _, _, activation = self.activate()
        snapshot = activation.runtime_snapshot()
        self.assertEqual(len(snapshot.adapters), 1)
        self.assertEqual(len(snapshot.permissions), 1)
        permission = snapshot.permissions[0]
        self.assertEqual(permission.capability_id, GMAIL_CAPABILITY_ID)
        self.assertEqual(permission.adapter_id, GMAIL_ADAPTER_ID)
        self.assertEqual(permission.operation, GMAIL_OPERATION)
        self.assertEqual(permission.effect, "read")
        self.assertEqual(permission.data_class, "owner_data")
        self.assertTrue(permission.owner_approval_required)
        self.assertEqual(reader.calls, 0)

    def test_post_approval_adapter_execution_reads_once(self):
        reader, _, _, _, _, activation = self.activate()
        adapter = activation.runtime_snapshot().adapters[0]
        request = CommandRequest(request_id="gmail-r1", command="module.execute")
        plan = ExecutionPlan(
            request_id="gmail-r1",
            adapter_id=GMAIL_ADAPTER_ID,
            steps=(ExecutionStep(sequence=1, operation=GMAIL_OPERATION, parameters={"mode": "recent"}),),
            owner_approval_required=False,
        )
        result = adapter.execute(request, plan)
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(reader.calls, 1)
        self.assertEqual(json.loads(result.output["content"]), {"messages": []})

    def test_static_core_permission_catalog_stays_gmail_free(self):
        self.assertFalse(
            any(permission.adapter_id == GMAIL_ADAPTER_ID for permission in PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS)
        )


if __name__ == "__main__":
    unittest.main()
