import json
import unittest
from datetime import datetime

from pydantic import SecretStr

from app.connectors.google_calendar import (
    GOOGLE_CALENDAR_ERROR_CREDENTIAL_UNAVAILABLE,
    GOOGLE_CALENDAR_ERROR_INVALID_REQUEST,
    GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE,
    GOOGLE_CALENDAR_ERROR_NETWORK,
    GoogleCalendarConnectorError,
    GoogleCalendarEvent,
    GoogleCalendarReadResult,
)
from app.contracts.credential import CredentialProfile, ResolvedCredential
from app.contracts.google_calendar import (
    GOOGLE_CALENDAR_ADAPTER_ID,
    GOOGLE_CALENDAR_CAPABILITY_ID,
    GOOGLE_CALENDAR_CAPABILITY_NAME,
    GOOGLE_CALENDAR_CREDENTIAL_AUTH_SCHEME,
    GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID,
    GOOGLE_CALENDAR_CREDENTIAL_PROVIDER_ID,
    GOOGLE_CALENDAR_CREDENTIAL_SCOPE,
    GOOGLE_CALENDAR_OPERATION,
    GOOGLE_CALENDAR_PLUGIN_ID,
    GOOGLE_CALENDAR_PLUGIN_VERSION,
)
from app.plugins.context import PluginExecutionContext
from app.plugins.google_calendar import GoogleCalendarPlugin
from app.plugins.request import PluginRequest
from app.services.credential_access_broker import (
    CredentialAccessBroker,
    CredentialAccessError,
    StaticCredentialSecretSource,
)
from app.services.credential_profile_catalog import CredentialProfileCatalog


class FakeReader:
    def __init__(self, result=None, *, error=None) -> None:
        event = GoogleCalendarEvent(
            summary="Planning",
            status="confirmed",
            start="2026-09-16T09:00:00+07:00",
            end="2026-09-16T10:00:00+07:00",
            all_day=False,
        )
        self.result = GoogleCalendarReadResult((event,), False) if result is None else result
        self.error = error
        self.calls = 0
        self.tokens = []
        self.windows = []

    def list_upcoming_events(self, access_token, *, time_min, time_max):
        self.calls += 1
        self.tokens.append(access_token)
        self.windows.append((time_min, time_max))
        if self.error is not None:
            raise self.error
        return self.result


class RecordingBroker(CredentialAccessBroker):
    def __init__(self, resolved=None, *, error=None) -> None:
        profile = CredentialProfile(
            profile_id=GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID,
            plugin_id=GOOGLE_CALENDAR_PLUGIN_ID,
            plugin_version=GOOGLE_CALENDAR_PLUGIN_VERSION,
            capability_name=GOOGLE_CALENDAR_CAPABILITY_NAME,
            provider_id=GOOGLE_CALENDAR_CREDENTIAL_PROVIDER_ID,
            auth_scheme=GOOGLE_CALENDAR_CREDENTIAL_AUTH_SCHEME,
            required_scopes=(GOOGLE_CALENDAR_CREDENTIAL_SCOPE,),
            secret_ref="google_calendar.access_token",
        )
        super().__init__(
            profile_catalog=CredentialProfileCatalog((profile,)),
            secret_source=StaticCredentialSecretSource(
                {"google_calendar.access_token": SecretStr("calendar-secret-never-log")}
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


def request_content(time_min="2026-09-16T00:00:00+07:00", time_max="2026-09-17T00:00:00+07:00"):
    return json.dumps(
        {"time_min": time_min, "time_max": time_max},
        sort_keys=True,
        separators=(",", ":"),
    )


class GoogleCalendarPluginTests(unittest.TestCase):
    def test_identity_is_exact_and_static(self) -> None:
        plugin = GoogleCalendarPlugin(credential_broker=RecordingBroker(), client=FakeReader())
        self.assertEqual(plugin.id, GOOGLE_CALENDAR_PLUGIN_ID)
        self.assertEqual(plugin.version, GOOGLE_CALENDAR_PLUGIN_VERSION)
        self.assertEqual(GOOGLE_CALENDAR_ADAPTER_ID, "module.plugin.google_calendar")
        self.assertEqual(GOOGLE_CALENDAR_OPERATION, "list_upcoming_events")
        self.assertEqual(GOOGLE_CALENDAR_CAPABILITY_ID, "exec.plugin.google_calendar.upcoming_events")

    def test_constructing_plugin_reads_no_credential_and_no_network(self) -> None:
        broker = RecordingBroker()
        reader = FakeReader()
        GoogleCalendarPlugin(credential_broker=broker, client=reader)
        self.assertEqual(broker.calls, 0)
        self.assertEqual(reader.calls, 0)

    def test_invalid_or_legacy_request_does_not_read_credential(self) -> None:
        for content in ("primary", "upcoming", "{}"):
            with self.subTest(content=content):
                broker = RecordingBroker()
                reader = FakeReader()
                plugin = GoogleCalendarPlugin(credential_broker=broker, client=reader)
                with self.assertRaises(GoogleCalendarConnectorError) as caught:
                    plugin.execute(PluginExecutionContext(), PluginRequest(content=content))
                self.assertEqual(caught.exception.code, GOOGLE_CALENDAR_ERROR_INVALID_REQUEST)
                self.assertEqual(broker.calls, 0)
                self.assertEqual(reader.calls, 0)

    def test_execute_forwards_exact_window_and_returns_bounded_payload(self) -> None:
        broker = RecordingBroker()
        reader = FakeReader()
        plugin = GoogleCalendarPlugin(credential_broker=broker, client=reader)
        result = plugin.execute(
            PluginExecutionContext(),
            PluginRequest(content=request_content()),
        )
        self.assertEqual(broker.calls, 1)
        self.assertEqual(reader.calls, 1)
        self.assertIsInstance(reader.tokens[0], SecretStr)
        self.assertEqual(
            reader.windows[0][0],
            datetime.fromisoformat("2026-09-16T00:00:00+07:00"),
        )
        self.assertEqual(
            reader.windows[0][1],
            datetime.fromisoformat("2026-09-17T00:00:00+07:00"),
        )
        parsed = json.loads(result.content)
        self.assertEqual(parsed["truncated"], False)
        self.assertEqual(parsed["events"][0]["summary"], "Planning")
        self.assertNotIn("calendar-secret-never-log", result.content)

    def test_truncation_boolean_is_propagated_without_page_token(self) -> None:
        reader = FakeReader(result=GoogleCalendarReadResult((), True))
        result = GoogleCalendarPlugin(
            credential_broker=RecordingBroker(), client=reader
        ).execute(PluginExecutionContext(), PluginRequest(content=request_content()))
        self.assertEqual(json.loads(result.content), {"events": [], "truncated": True})
        self.assertNotIn("token", result.content.casefold())

    def test_invalid_window_is_rejected_before_credential(self) -> None:
        broker = RecordingBroker()
        reader = FakeReader()
        plugin = GoogleCalendarPlugin(credential_broker=broker, client=reader)
        with self.assertRaises(GoogleCalendarConnectorError) as caught:
            plugin.execute(
                PluginExecutionContext(),
                PluginRequest(content=request_content("2026-09-17T00:00:00+07:00", "2026-09-16T00:00:00+07:00")),
            )
        self.assertEqual(caught.exception.code, GOOGLE_CALENDAR_ERROR_INVALID_REQUEST)
        self.assertEqual(broker.calls, 0)
        self.assertEqual(reader.calls, 0)

    def test_credential_failure_is_normalized_without_secret_leak(self) -> None:
        broker = RecordingBroker(error=CredentialAccessError("credential_access_secret_not_found"))
        plugin = GoogleCalendarPlugin(credential_broker=broker, client=FakeReader())
        with self.assertRaises(GoogleCalendarConnectorError) as caught:
            plugin.execute(PluginExecutionContext(), PluginRequest(content=request_content()))
        self.assertEqual(caught.exception.code, GOOGLE_CALENDAR_ERROR_CREDENTIAL_UNAVAILABLE)

    def test_mismatched_resolved_profile_fails_before_reader(self) -> None:
        resolved = ResolvedCredential(
            profile_id="wrong",
            plugin_id=GOOGLE_CALENDAR_PLUGIN_ID,
            plugin_version=GOOGLE_CALENDAR_PLUGIN_VERSION,
            capability_name=GOOGLE_CALENDAR_CAPABILITY_NAME,
            provider_id=GOOGLE_CALENDAR_CREDENTIAL_PROVIDER_ID,
            auth_scheme=GOOGLE_CALENDAR_CREDENTIAL_AUTH_SCHEME,
            required_scopes=(GOOGLE_CALENDAR_CREDENTIAL_SCOPE,),
            secret=SecretStr("calendar-secret-never-log"),
        )
        reader = FakeReader()
        plugin = GoogleCalendarPlugin(credential_broker=RecordingBroker(resolved=resolved), client=reader)
        with self.assertRaises(GoogleCalendarConnectorError) as caught:
            plugin.execute(PluginExecutionContext(), PluginRequest(content=request_content()))
        self.assertEqual(caught.exception.code, GOOGLE_CALENDAR_ERROR_CREDENTIAL_UNAVAILABLE)
        self.assertEqual(reader.calls, 0)

    def test_safe_connector_error_is_preserved(self) -> None:
        reader = FakeReader(error=GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE))
        plugin = GoogleCalendarPlugin(credential_broker=RecordingBroker(), client=reader)
        with self.assertRaises(GoogleCalendarConnectorError) as caught:
            plugin.execute(PluginExecutionContext(), PluginRequest(content=request_content()))
        self.assertEqual(caught.exception.code, GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE)

    def test_unexpected_reader_error_is_normalized(self) -> None:
        reader = FakeReader(error=RuntimeError("calendar-secret-never-log"))
        plugin = GoogleCalendarPlugin(credential_broker=RecordingBroker(), client=reader)
        with self.assertRaises(GoogleCalendarConnectorError) as caught:
            plugin.execute(PluginExecutionContext(), PluginRequest(content=request_content()))
        self.assertEqual(caught.exception.code, GOOGLE_CALENDAR_ERROR_NETWORK)
        self.assertNotIn("calendar-secret-never-log", str(caught.exception))

    def test_invalid_reader_result_is_rejected(self) -> None:
        plugin = GoogleCalendarPlugin(
            credential_broker=RecordingBroker(),
            client=FakeReader(result=[{"bad": True}]),
        )
        with self.assertRaises(GoogleCalendarConnectorError) as caught:
            plugin.execute(PluginExecutionContext(), PluginRequest(content=request_content()))
        self.assertEqual(caught.exception.code, GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE)


if __name__ == "__main__":
    unittest.main()
