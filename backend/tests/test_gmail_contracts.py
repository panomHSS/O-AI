import unittest

from app.contracts.gmail import (
    GMAIL_ADAPTER_ID,
    GMAIL_CAPABILITY_ID,
    GMAIL_CREDENTIAL_SCOPE,
    GMAIL_CREDENTIAL_SECRET_REF,
    GMAIL_MAX_BODY_CHARS,
    GMAIL_MAX_RESULTS,
    GMAIL_OPERATION,
    GMAIL_PLUGIN_ID,
    GMAIL_PLUGIN_VERSION,
    GMAIL_READ_CAPABILITY_NAME,
    GMAIL_READ_CREDENTIAL_PROFILE_ID,
    GmailMessage,
    GmailReadQuery,
    GmailReadResult,
)


class GmailReadContractTests(unittest.TestCase):
    def message(self, *, message_id="m1", body="body"):
        return GmailMessage(
            message_id=message_id,
            sender="alice@example.com",
            subject="Subject",
            received_at="2026-09-16T01:02:03Z",
            unread=True,
            snippet="Preview",
            body=body,
        )

    def test_exact_d76_identity_is_preserved_and_d77_execution_identity_is_fixed(self):
        self.assertEqual(GMAIL_PLUGIN_ID, "gmail")
        self.assertEqual(GMAIL_PLUGIN_VERSION, "1.0.0")
        self.assertEqual(GMAIL_READ_CAPABILITY_NAME, "read_messages")
        self.assertEqual(
            GMAIL_READ_CREDENTIAL_PROFILE_ID,
            "gmail.messages.readonly",
        )
        self.assertEqual(
            GMAIL_CREDENTIAL_SCOPE,
            "https://www.googleapis.com/auth/gmail.readonly",
        )
        self.assertEqual(GMAIL_CREDENTIAL_SECRET_REF, "gmail.access_token")
        self.assertEqual(GMAIL_ADAPTER_ID, "module.plugin.gmail")
        self.assertEqual(GMAIL_OPERATION, "read_messages")
        self.assertEqual(
            GMAIL_CAPABILITY_ID,
            "exec.plugin.gmail.read_messages",
        )

    def test_recent_query_has_no_provider_q(self):
        query = GmailReadQuery(mode="recent")
        self.assertIsNone(query.provider_query)
        self.assertEqual(query.to_parameters(), {"mode": "recent"})
        self.assertEqual(
            GmailReadQuery.from_parameters({"mode": "recent"}),
            query,
        )

    def test_unread_query_is_exact(self):
        query = GmailReadQuery(mode="unread")
        self.assertEqual(query.provider_query, "is:unread")
        self.assertEqual(query.to_parameters(), {"mode": "unread"})

    def test_from_query_requires_one_valid_exact_sender(self):
        query = GmailReadQuery(
            mode="from",
            sender="alice@example.com",
        )
        self.assertEqual(
            query.provider_query,
            "from:alice@example.com",
        )
        self.assertEqual(
            query.to_parameters(),
            {"mode": "from", "sender": "alice@example.com"},
        )
        self.assertEqual(
            GmailReadQuery.from_parameters(query.to_parameters()),
            query,
        )

    def test_sender_is_forbidden_for_non_from_modes(self):
        for mode in ("recent", "unread"):
            with self.subTest(mode=mode):
                with self.assertRaises(ValueError):
                    GmailReadQuery(
                        mode=mode,
                        sender="alice@example.com",
                    )

    def test_invalid_sender_and_raw_search_shapes_fail_closed(self):
        for sender in (
            "",
            " alice@example.com",
            "alice@example.com ",
            "Alice <alice@example.com>",
            "alice",
            "alice@localhost",
            "a\r\n@example.com",
            "x" * 321 + "@example.com",
        ):
            with self.subTest(sender=sender[:30]):
                with self.assertRaises(ValueError):
                    GmailReadQuery(mode="from", sender=sender)

        for parameters in (
            {},
            {"mode": "search", "q": "subject:invoice"},
            {"mode": "recent", "q": "is:starred"},
            {"mode": "unread", "sender": "alice@example.com"},
            {
                "mode": "from",
                "sender": "alice@example.com",
                "maxResults": 50,
            },
        ):
            with self.subTest(parameters=parameters):
                with self.assertRaises(ValueError):
                    GmailReadQuery.from_parameters(parameters)

    def test_message_projection_uses_exact_safe_keys(self):
        message = self.message()
        self.assertEqual(
            set(message.as_dict()),
            {
                "body",
                "from",
                "message_id",
                "received_at",
                "snippet",
                "subject",
                "unread",
            },
        )
        self.assertEqual(message.as_dict()["from"], "alice@example.com")

    def test_message_and_result_bounds_fail_closed(self):
        with self.assertRaises(ValueError):
            self.message(body="x" * (GMAIL_MAX_BODY_CHARS + 1))
        with self.assertRaises(ValueError):
            GmailReadResult(
                messages=tuple(
                    self.message(message_id=f"m{index}")
                    for index in range(GMAIL_MAX_RESULTS + 1)
                )
            )
        result = GmailReadResult(
            messages=tuple(
                self.message(message_id=f"m{index}")
                for index in range(GMAIL_MAX_RESULTS)
            )
        )
        self.assertEqual(len(result.messages), GMAIL_MAX_RESULTS)


if __name__ == "__main__":
    unittest.main()
