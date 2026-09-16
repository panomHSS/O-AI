import json
import unittest

from pydantic import SecretStr

from app.connectors.gmail import (
    GMAIL_ERROR_AUTH_FAILED,
    GMAIL_ERROR_RESPONSE_INVALID,
    GMAIL_ERROR_UNAVAILABLE,
    GmailConnectorError,
)
from app.contracts.credential import CredentialProfile, ResolvedCredential
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
    GmailMessage,
    GmailReadQuery,
    GmailReadResult,
)
from app.plugins.context import PluginExecutionContext
from app.plugins.gmail import GmailPlugin
from app.plugins.request import PluginRequest
from app.services.credential_access_broker import (
    CredentialAccessBroker,
    CredentialAccessError,
    StaticCredentialSecretSource,
)
from app.services.credential_profile_catalog import CredentialProfileCatalog


class FakeReader:
    def __init__(self, result=None, *, error=None):
        message = GmailMessage(
            message_id="m1",
            sender="alice@example.com",
            subject="Update",
            received_at="2026-09-16T01:00:00Z",
            unread=True,
            snippet="hello",
            body="hello world",
        )
        self.result = GmailReadResult((message,)) if result is None else result
        self.error = error
        self.calls = 0
        self.tokens = []
        self.queries = []

    def read_messages(self, access_token, *, query):
        self.calls += 1
        self.tokens.append(access_token)
        self.queries.append(query)
        if self.error is not None:
            raise self.error
        return self.result


class RecordingBroker(CredentialAccessBroker):
    def __init__(self, resolved=None, *, error=None):
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
        super().__init__(
            profile_catalog=CredentialProfileCatalog((profile,)),
            secret_source=StaticCredentialSecretSource(
                {GMAIL_CREDENTIAL_SECRET_REF: SecretStr("gmail-secret-never-log")}
            ),
        )
        self.calls = 0
        self.error = error
        self.resolved_override = resolved

    def resolve(self, plugin_id, plugin_version, capability_name):
        self.calls += 1
        if self.error is not None:
            raise self.error
        if self.resolved_override is not None:
            return self.resolved_override
        return super().resolve(plugin_id, plugin_version, capability_name)


def request_content(mode="recent", sender=None):
    payload = {"mode": mode}
    if sender is not None:
        payload["sender"] = sender
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


class GmailPluginTests(unittest.TestCase):
    def test_identity_is_exact(self):
        plugin = GmailPlugin(credential_broker=RecordingBroker(), client=FakeReader())
        self.assertEqual(plugin.id, GMAIL_PLUGIN_ID)
        self.assertEqual(plugin.version, GMAIL_PLUGIN_VERSION)
        self.assertEqual(GMAIL_ADAPTER_ID, "module.plugin.gmail")
        self.assertEqual(GMAIL_OPERATION, "read_messages")
        self.assertEqual(GMAIL_CAPABILITY_ID, "exec.plugin.gmail.read_messages")

    def test_constructing_plugin_reads_nothing(self):
        broker = RecordingBroker()
        reader = FakeReader()
        GmailPlugin(credential_broker=broker, client=reader)
        self.assertEqual(broker.calls, 0)
        self.assertEqual(reader.calls, 0)

    def test_invalid_request_fails_before_credential(self):
        broker = RecordingBroker()
        reader = FakeReader()
        plugin = GmailPlugin(credential_broker=broker, client=reader)
        for content in ("{}", '"recent"', '{"mode":"from"}'):
            with self.subTest(content=content):
                with self.assertRaises(GmailConnectorError):
                    plugin.execute(PluginExecutionContext(), PluginRequest(content=content))
        self.assertEqual(broker.calls, 0)
        self.assertEqual(reader.calls, 0)

    def test_execute_resolves_exact_credential_once_and_returns_safe_payload(self):
        broker = RecordingBroker()
        reader = FakeReader()
        result = GmailPlugin(credential_broker=broker, client=reader).execute(
            PluginExecutionContext(),
            PluginRequest(content=request_content("unread")),
        )
        self.assertEqual(broker.calls, 1)
        self.assertEqual(reader.calls, 1)
        self.assertEqual(reader.queries, [GmailReadQuery(mode="unread")])
        self.assertIsInstance(reader.tokens[0], SecretStr)
        payload = json.loads(result.content)
        self.assertEqual(payload["messages"][0]["subject"], "Update")
        self.assertNotIn("gmail-secret-never-log", result.content)

    def test_credential_failure_is_safe_and_reader_is_not_called(self):
        broker = RecordingBroker(
            error=CredentialAccessError("credential_access_secret_not_found")
        )
        reader = FakeReader()
        with self.assertRaises(GmailConnectorError) as caught:
            GmailPlugin(credential_broker=broker, client=reader).execute(
                PluginExecutionContext(),
                PluginRequest(content=request_content()),
            )
        self.assertEqual(caught.exception.code, GMAIL_ERROR_AUTH_FAILED)
        self.assertEqual(reader.calls, 0)

    def test_mismatched_credential_profile_fails_closed(self):
        resolved = ResolvedCredential(
            profile_id="wrong",
            plugin_id=GMAIL_PLUGIN_ID,
            plugin_version=GMAIL_PLUGIN_VERSION,
            capability_name=GMAIL_READ_CAPABILITY_NAME,
            provider_id=GMAIL_CREDENTIAL_PROVIDER_ID,
            auth_scheme=GMAIL_CREDENTIAL_AUTH_SCHEME,
            required_scopes=(GMAIL_CREDENTIAL_SCOPE,),
            secret=SecretStr("gmail-secret-never-log"),
        )
        reader = FakeReader()
        with self.assertRaises(GmailConnectorError) as caught:
            GmailPlugin(
                credential_broker=RecordingBroker(resolved=resolved),
                client=reader,
            ).execute(
                PluginExecutionContext(),
                PluginRequest(content=request_content()),
            )
        self.assertEqual(caught.exception.code, GMAIL_ERROR_AUTH_FAILED)
        self.assertEqual(reader.calls, 0)

    def test_safe_connector_error_is_preserved(self):
        reader = FakeReader(error=GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID))
        with self.assertRaises(GmailConnectorError) as caught:
            GmailPlugin(credential_broker=RecordingBroker(), client=reader).execute(
                PluginExecutionContext(),
                PluginRequest(content=request_content()),
            )
        self.assertEqual(caught.exception.code, GMAIL_ERROR_RESPONSE_INVALID)

    def test_unexpected_reader_error_is_normalized(self):
        reader = FakeReader(error=RuntimeError("gmail-secret-never-log"))
        with self.assertRaises(GmailConnectorError) as caught:
            GmailPlugin(credential_broker=RecordingBroker(), client=reader).execute(
                PluginExecutionContext(),
                PluginRequest(content=request_content()),
            )
        self.assertEqual(caught.exception.code, GMAIL_ERROR_UNAVAILABLE)
        self.assertNotIn("gmail-secret-never-log", str(caught.exception))

    def test_invalid_reader_result_fails_closed(self):
        reader = FakeReader(result=[{"bad": True}])
        with self.assertRaises(GmailConnectorError) as caught:
            GmailPlugin(credential_broker=RecordingBroker(), client=reader).execute(
                PluginExecutionContext(),
                PluginRequest(content=request_content()),
            )
        self.assertEqual(caught.exception.code, GMAIL_ERROR_RESPONSE_INVALID)


if __name__ == "__main__":
    unittest.main()
