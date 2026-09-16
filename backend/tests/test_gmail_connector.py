import base64
import json
import socket
import unittest
import urllib.error
import urllib.parse
import urllib.request
from unittest.mock import Mock, patch

from pydantic import SecretStr

from app.connectors.gmail import (
    GMAIL_ERROR_AUTH_FAILED,
    GMAIL_ERROR_MESSAGE_NOT_FOUND,
    GMAIL_ERROR_QUERY_INVALID,
    GMAIL_ERROR_RATE_LIMITED,
    GMAIL_ERROR_RESPONSE_INVALID,
    GMAIL_ERROR_RESPONSE_TOO_LARGE,
    GMAIL_ERROR_UNAVAILABLE,
    GMAIL_LIST_FIELDS,
    GMAIL_LIST_MAX_RESPONSE_BYTES,
    GMAIL_MAX_MIME_DEPTH,
    GMAIL_MAX_MIME_PARTS,
    GMAIL_MESSAGE_MAX_RESPONSE_BYTES,
    GMAIL_MESSAGES_URL,
    GmailClient,
    GmailConnectorError,
    _NoRedirectHandler,
    _open_without_redirects,
)
from app.contracts.gmail import GmailReadQuery


def encoded_body(text):
    return (
        base64.urlsafe_b64encode(text.encode("utf-8"))
        .decode("ascii")
        .rstrip("=")
    )


def list_payload(*message_ids, next_page_token=None):
    payload = {
        "messages": [{"id": message_id} for message_id in message_ids]
    }
    if next_page_token is not None:
        payload["nextPageToken"] = next_page_token
    return payload


def message_payload(
    message_id="m1",
    *,
    plain_text="Hello from Gmail",
    include_plain=True,
    attachment_backed=False,
):
    plain_body = {"size": len(plain_text.encode("utf-8"))}
    if attachment_backed:
        plain_body["attachmentId"] = "attachment-secret-id"
    else:
        plain_body["data"] = encoded_body(plain_text)

    parts = [
        {
            "mimeType": "text/html",
            "filename": "",
            "headers": [],
            "body": {
                "size": 26,
                "data": encoded_body("<b>do-not-render</b>"),
            },
        }
    ]
    if include_plain:
        parts.insert(
            0,
            {
                "mimeType": "text/plain",
                "filename": "",
                "headers": [],
                "body": plain_body,
            },
        )

    return {
        "id": message_id,
        "labelIds": ["INBOX", "UNREAD"],
        "internalDate": "1789520523000",
        "snippet": "  Preview   text  ",
        "payload": {
            "mimeType": "multipart/alternative",
            "filename": "",
            "headers": [
                {
                    "name": "From",
                    "value": " Alice <alice@example.com> ",
                },
                {"name": "Subject", "value": "  Project   update "},
            ],
            "body": {"size": 0},
            "parts": parts,
        },
    }


class FakeResponse:
    def __init__(self, body, *, status=200):
        self.body = body
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, limit):
        return self.body[:limit]


class QueueTransport:
    def __init__(self, *items):
        self.items = list(items)
        self.requests = []
        self.timeouts = []

    def __call__(self, request, timeout):
        self.requests.append(request)
        self.timeouts.append(timeout)
        if not self.items:
            raise AssertionError("unexpected network request")
        item = self.items.pop(0)
        if isinstance(item, BaseException):
            raise item
        if isinstance(item, FakeResponse):
            return item
        if isinstance(item, bytes):
            return FakeResponse(item)
        return FakeResponse(json.dumps(item).encode("utf-8"))


class GmailConnectorTests(unittest.TestCase):
    TOKEN = "secret-gmail-token-never-log"

    def client(self, transport):
        return GmailClient(transport=transport)

    def read(self, transport, query=None, credential=None):
        return self.client(transport).read_messages(
            SecretStr(self.TOKEN) if credential is None else credential,
            query=GmailReadQuery(mode="recent") if query is None else query,
        )

    def test_recent_read_uses_one_fixed_list_get_and_exact_bounds(self):
        transport = QueueTransport(
            list_payload("m1"),
            message_payload("m1"),
        )
        result = self.read(transport)
        self.assertEqual(len(result.messages), 1)
        self.assertEqual(len(transport.requests), 2)
        self.assertEqual(transport.timeouts, [5.0, 5.0])

        list_request, get_request = transport.requests
        list_url = urllib.parse.urlsplit(list_request.full_url)
        self.assertEqual(
            f"{list_url.scheme}://{list_url.netloc}{list_url.path}",
            GMAIL_MESSAGES_URL,
        )
        self.assertEqual(list_request.get_method(), "GET")
        list_query = urllib.parse.parse_qs(list_url.query)
        self.assertEqual(list_query["maxResults"], ["5"])
        self.assertEqual(list_query["includeSpamTrash"], ["false"])
        self.assertEqual(list_query["fields"], [GMAIL_LIST_FIELDS])
        self.assertNotIn("q", list_query)
        self.assertNotIn("pageToken", list_query)

        get_url = urllib.parse.urlsplit(get_request.full_url)
        self.assertEqual(
            get_url.path,
            "/gmail/v1/users/me/messages/m1",
        )
        self.assertEqual(
            urllib.parse.parse_qs(get_url.query),
            {"format": ["full"]},
        )
        self.assertEqual(get_request.get_method(), "GET")

    def test_unread_and_from_queries_are_exact_and_not_raw_caller_search(self):
        cases = (
            (GmailReadQuery(mode="unread"), "is:unread"),
            (
                GmailReadQuery(
                    mode="from",
                    sender="alice@example.com",
                ),
                "from:alice@example.com",
            ),
        )
        for query, expected in cases:
            with self.subTest(mode=query.mode):
                transport = QueueTransport(list_payload())
                self.read(transport, query=query)
                parsed = urllib.parse.urlsplit(
                    transport.requests[0].full_url
                )
                actual = urllib.parse.parse_qs(parsed.query)
                self.assertEqual(actual["q"], [expected])
                self.assertEqual(actual["maxResults"], ["5"])

    def test_access_token_is_header_only_on_every_request(self):
        transport = QueueTransport(
            list_payload("m1"),
            message_payload("m1"),
        )
        self.read(transport)
        for request in transport.requests:
            self.assertNotIn(self.TOKEN, request.full_url)
            headers = {
                key.casefold(): value
                for key, value in request.header_items()
            }
            self.assertEqual(
                headers["authorization"],
                f"Bearer {self.TOKEN}",
            )
            self.assertNotIn("cookie", headers)
            self.assertNotIn("proxy-authorization", headers)

    def test_default_transport_disables_proxy_and_redirects(self):
        request = urllib.request.Request(
            GMAIL_MESSAGES_URL,
            method="GET",
        )
        opener = Mock()
        sentinel = object()
        opener.open.return_value = sentinel
        with patch(
            "app.connectors.gmail.urllib.request.build_opener",
            return_value=opener,
        ) as build_opener:
            result = _open_without_redirects(request, 5.0)
        self.assertIs(result, sentinel)
        handlers = build_opener.call_args.args
        self.assertEqual(len(handlers), 2)
        self.assertIsInstance(
            handlers[0],
            urllib.request.ProxyHandler,
        )
        self.assertEqual(handlers[0].proxies, {})
        self.assertIsInstance(handlers[1], _NoRedirectHandler)
        opener.open.assert_called_once_with(request, timeout=5.0)

    def test_message_is_normalized_without_html_or_provider_metadata(self):
        transport = QueueTransport(
            list_payload("m1", next_page_token="opaque-never-expose"),
            message_payload("m1"),
        )
        result = self.read(transport)
        message = result.messages[0]
        self.assertEqual(message.message_id, "m1")
        self.assertEqual(
            message.sender,
            "Alice <alice@example.com>",
        )
        self.assertEqual(message.subject, "Project update")
        self.assertEqual(message.snippet, "Preview text")
        self.assertTrue(message.unread)
        self.assertEqual(message.body, "Hello from Gmail")
        self.assertTrue(message.received_at.endswith("Z"))
        serialized = json.dumps(message.as_dict())
        self.assertNotIn("labelIds", serialized)
        self.assertNotIn("attachment", serialized)
        self.assertNotIn("do-not-render", serialized)
        self.assertNotIn("opaque-never-expose", serialized)

    def test_attachment_backed_plain_text_is_never_fetched(self):
        transport = QueueTransport(
            list_payload("m1"),
            message_payload(
                "m1",
                plain_text="attachment body",
                attachment_backed=True,
            ),
        )
        result = self.read(transport)
        self.assertEqual(result.messages[0].body, "")
        self.assertEqual(len(transport.requests), 2)
        self.assertTrue(
            all(
                "attachments" not in request.full_url
                for request in transport.requests
            )
        )

    def test_html_only_message_has_empty_body(self):
        transport = QueueTransport(
            list_payload("m1"),
            message_payload("m1", include_plain=False),
        )
        result = self.read(transport)
        self.assertEqual(result.messages[0].body, "")

    def test_opaque_message_id_is_url_encoded_exactly(self):
        message_id = "opaque/id?x=1"
        transport = QueueTransport(
            list_payload(message_id),
            message_payload(message_id),
        )
        self.read(transport)
        get_request = transport.requests[1]
        self.assertIn(
            "/messages/opaque%2Fid%3Fx%3D1",
            get_request.full_url,
        )

    def test_invalid_query_or_credential_fails_before_network(self):
        cases = (
            ("not-a-query", SecretStr(self.TOKEN), GMAIL_ERROR_QUERY_INVALID),
            (
                GmailReadQuery(mode="recent"),
                "plain-token",
                GMAIL_ERROR_AUTH_FAILED,
            ),
            (
                GmailReadQuery(mode="recent"),
                SecretStr("bad\r\nInjected: yes"),
                GMAIL_ERROR_AUTH_FAILED,
            ),
        )
        for query, credential, expected in cases:
            with self.subTest(expected=expected):
                transport = QueueTransport()
                with self.assertRaises(GmailConnectorError) as caught:
                    self.read(
                        transport,
                        query=query,
                        credential=credential,
                    )
                self.assertEqual(caught.exception.code, expected)
                self.assertEqual(len(transport.requests), 0)

    def test_list_shape_is_bounded_and_duplicate_ids_fail_closed(self):
        invalid_payloads = (
            {"messages": "not-a-list"},
            {
                "messages": [
                    {"id": f"m{index}"}
                    for index in range(6)
                ]
            },
            {"messages": [{"id": "m1"}, {"id": "m1"}]},
            {"messages": [{"id": "m1", "threadId": "t1"}]},
            {"messages": [{"id": ""}]},
            {"messages": [], "nextPageToken": ""},
        )
        for payload in invalid_payloads:
            with self.subTest(payload=str(payload)[:60]):
                transport = QueueTransport(payload)
                with self.assertRaises(GmailConnectorError) as caught:
                    self.read(transport)
                self.assertEqual(
                    caught.exception.code,
                    GMAIL_ERROR_RESPONSE_INVALID,
                )
                self.assertEqual(len(transport.requests), 1)

    def test_message_id_must_match_the_id_returned_by_list(self):
        transport = QueueTransport(
            list_payload("m1"),
            message_payload("different-id"),
        )
        with self.assertRaises(GmailConnectorError) as caught:
            self.read(transport)
        self.assertEqual(
            caught.exception.code,
            GMAIL_ERROR_RESPONSE_INVALID,
        )

    def test_response_size_and_json_are_bounded(self):
        transport = QueueTransport(
            b"x" * (GMAIL_LIST_MAX_RESPONSE_BYTES + 1)
        )
        with self.assertRaises(GmailConnectorError) as caught:
            self.read(transport)
        self.assertEqual(
            caught.exception.code,
            GMAIL_ERROR_RESPONSE_TOO_LARGE,
        )

        transport = QueueTransport(
            list_payload("m1"),
            b"x" * (GMAIL_MESSAGE_MAX_RESPONSE_BYTES + 1),
        )
        with self.assertRaises(GmailConnectorError) as caught:
            self.read(transport)
        self.assertEqual(
            caught.exception.code,
            GMAIL_ERROR_RESPONSE_TOO_LARGE,
        )

        transport = QueueTransport(b"{not-json")
        with self.assertRaises(GmailConnectorError) as caught:
            self.read(transport)
        self.assertEqual(
            caught.exception.code,
            GMAIL_ERROR_RESPONSE_INVALID,
        )

    def test_invalid_base64_fails_closed_and_html_is_not_a_fallback(self):
        payload = message_payload("m1")
        payload["payload"]["parts"][0]["body"]["data"] = "***not-base64***"
        transport = QueueTransport(list_payload("m1"), payload)
        with self.assertRaises(GmailConnectorError) as caught:
            self.read(transport)
        self.assertEqual(
            caught.exception.code,
            GMAIL_ERROR_RESPONSE_INVALID,
        )

    def test_mime_depth_is_bounded(self):
        root = message_payload("m1")
        root["payload"]["parts"] = []
        current = root["payload"]
        for depth in range(GMAIL_MAX_MIME_DEPTH + 1):
            child = {
                "mimeType": "multipart/mixed",
                "filename": "",
                "headers": [],
                "body": {"size": 0},
                "parts": [],
            }
            current["parts"] = [child]
            current = child
        transport = QueueTransport(list_payload("m1"), root)
        with self.assertRaises(GmailConnectorError) as caught:
            self.read(transport)
        self.assertEqual(
            caught.exception.code,
            GMAIL_ERROR_RESPONSE_INVALID,
        )

    def test_mime_part_count_is_bounded(self):
        payload = message_payload("m1")
        payload["payload"]["parts"] = [
            {
                "mimeType": "application/octet-stream",
                "filename": f"part-{index}",
                "headers": [],
                "body": {"size": 0},
            }
            for index in range(GMAIL_MAX_MIME_PARTS)
        ]
        transport = QueueTransport(list_payload("m1"), payload)
        with self.assertRaises(GmailConnectorError) as caught:
            self.read(transport)
        self.assertEqual(
            caught.exception.code,
            GMAIL_ERROR_RESPONSE_INVALID,
        )

    def test_transport_failures_are_safe_and_never_retry(self):
        cases = (
            (FakeResponse(b"{}", status=401), GMAIL_ERROR_AUTH_FAILED),
            (FakeResponse(b"{}", status=403), GMAIL_ERROR_AUTH_FAILED),
            (FakeResponse(b"{}", status=429), GMAIL_ERROR_RATE_LIMITED),
            (FakeResponse(b"{}", status=408), GMAIL_ERROR_UNAVAILABLE),
            (FakeResponse(b"{}", status=500), GMAIL_ERROR_UNAVAILABLE),
            (socket.timeout(self.TOKEN), GMAIL_ERROR_UNAVAILABLE),
            (
                urllib.error.URLError(self.TOKEN),
                GMAIL_ERROR_UNAVAILABLE,
            ),
        )
        for item, expected in cases:
            with self.subTest(expected=expected):
                transport = QueueTransport(item)
                with self.assertRaises(GmailConnectorError) as caught:
                    self.read(transport)
                self.assertEqual(caught.exception.code, expected)
                self.assertEqual(len(transport.requests), 1)
                self.assertNotIn(self.TOKEN, str(caught.exception))

    def test_http_error_and_message_not_found_are_normalized(self):
        error = urllib.error.HTTPError(
            GMAIL_MESSAGES_URL,
            401,
            self.TOKEN,
            hdrs=None,
            fp=None,
        )
        transport = QueueTransport(error)
        with self.assertRaises(GmailConnectorError) as caught:
            self.read(transport)
        self.assertEqual(caught.exception.code, GMAIL_ERROR_AUTH_FAILED)
        self.assertNotIn(self.TOKEN, str(caught.exception))
        self.assertTrue(error.closed)

        transport = QueueTransport(
            list_payload("m1"),
            FakeResponse(b"{}", status=404),
        )
        with self.assertRaises(GmailConnectorError) as caught:
            self.read(transport)
        self.assertEqual(
            caught.exception.code,
            GMAIL_ERROR_MESSAGE_NOT_FOUND,
        )
        self.assertEqual(len(transport.requests), 2)

    def test_final_normalized_result_is_bounded_to_32_kib(self):
        message_ids = [f"m{index}" for index in range(5)]
        huge = "ก" * 4096
        items = [list_payload(*message_ids)]
        items.extend(
            message_payload(message_id, plain_text=huge)
            for message_id in message_ids
        )
        transport = QueueTransport(*items)
        with self.assertRaises(GmailConnectorError) as caught:
            self.read(transport)
        self.assertEqual(
            caught.exception.code,
            GMAIL_ERROR_RESPONSE_TOO_LARGE,
        )
        self.assertEqual(len(transport.requests), 6)


if __name__ == "__main__":
    unittest.main()
