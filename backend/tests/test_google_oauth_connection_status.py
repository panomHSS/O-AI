import unittest
from types import SimpleNamespace

from app.services.google_oauth_connection_status import (
    GoogleOAuthConnectionStatusReader,
)


class FakeRepository:
    def __init__(self, record):
        self.record = record
        self.calls = 0

    def get(self, profile_id):
        self.calls += 1
        self.profile_id = profile_id
        return self.record


class TrapRecord:
    provider_id = "google"
    plugin_id = "google_calendar"
    plugin_version = "1.0.0"
    capability_name = "upcoming_events"
    granted_scopes = "https://www.googleapis.com/auth/calendar.events.readonly"
    cipher_version = "aesgcm-v1"
    status = "active"

    @property
    def encrypted_refresh_token(self):
        raise AssertionError("status preflight must not read ciphertext")

    @property
    def encryption_nonce(self):
        raise AssertionError("status preflight must not read nonce")


class GoogleOAuthConnectionStatusReaderTests(unittest.TestCase):
    def test_missing_record_is_disconnected(self):
        reader = GoogleOAuthConnectionStatusReader(FakeRepository(None))
        self.assertEqual(reader.read_status(), "disconnected")

    def test_active_status_reads_only_non_secret_metadata(self):
        reader = GoogleOAuthConnectionStatusReader(FakeRepository(TrapRecord()))
        self.assertEqual(reader.read_status(), "active")

    def test_reauthorization_and_subject_drift_fail_closed(self):
        reauth = SimpleNamespace(
            provider_id="google",
            plugin_id="google_calendar",
            plugin_version="1.0.0",
            capability_name="upcoming_events",
            granted_scopes=(
                "https://www.googleapis.com/auth/calendar.events.readonly"
            ),
            cipher_version="aesgcm-v1",
            status="reauthorization_required",
        )
        self.assertEqual(
            GoogleOAuthConnectionStatusReader(
                FakeRepository(reauth)
            ).read_status(),
            "reauthorization_required",
        )

        drift = SimpleNamespace(**{**reauth.__dict__, "status": "active", "plugin_id": "other"})
        self.assertEqual(
            GoogleOAuthConnectionStatusReader(
                FakeRepository(drift)
            ).read_status(),
            "reauthorization_required",
        )


if __name__ == "__main__":
    unittest.main()
