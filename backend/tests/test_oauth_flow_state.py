import unittest
from datetime import datetime, timedelta, timezone

from app.services.oauth_flow_state import (
    OAUTH_FLOW_ERROR_EXPIRED_STATE,
    OAUTH_FLOW_ERROR_INVALID_STATE,
    OAUTH_FLOW_ERROR_STORE_FULL,
    OAuthFlowStateError,
    OAuthFlowStateStore,
)


class OAuthFlowStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 9, 15, tzinfo=timezone.utc)

    def store(self, **kwargs):
        return OAuthFlowStateStore(
            clock=lambda: self.now,
            **kwargs,
        )

    def test_state_is_high_entropy_and_single_use(self) -> None:
        store = self.store()
        state = store.issue()
        self.assertGreaterEqual(len(state), 40)
        self.assertEqual(store.count, 1)
        store.consume(state)
        self.assertEqual(store.count, 0)
        with self.assertRaises(OAuthFlowStateError) as caught:
            store.consume(state)
        self.assertEqual(
            caught.exception.code,
            OAUTH_FLOW_ERROR_INVALID_STATE,
        )

    def test_expired_state_fails_closed_and_is_consumed(self) -> None:
        store = self.store(ttl_seconds=10)
        state = store.issue()
        self.now += timedelta(seconds=11)
        with self.assertRaises(OAuthFlowStateError) as caught:
            store.consume(state)
        self.assertEqual(
            caught.exception.code,
            OAUTH_FLOW_ERROR_EXPIRED_STATE,
        )
        self.assertEqual(store.count, 0)

    def test_store_is_bounded(self) -> None:
        store = self.store(max_pending=1)
        store.issue()
        with self.assertRaises(OAuthFlowStateError) as caught:
            store.issue()
        self.assertEqual(
            caught.exception.code,
            OAUTH_FLOW_ERROR_STORE_FULL,
        )


if __name__ == "__main__":
    unittest.main()
