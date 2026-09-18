from __future__ import annotations

import base64
import json
import socket
import urllib.error
from email import policy
from email.parser import BytesParser

import pytest
from pydantic import SecretStr

from app.connectors.gmail_send import (
    GMAIL_SEND_ERROR_INDETERMINATE,
    GMAIL_SEND_ERROR_PROVIDER_REJECTED,
    GMAIL_SEND_ERROR_RATE_LIMITED,
    GMAIL_SEND_URL,
    GmailSendClient,
    GmailSendConnectorError,
)
from app.contracts.gmail_send import GmailSendDraft, GmailSendRequest


class Response:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, amount: int) -> bytes:
        return self._body[:amount]


def request() -> GmailSendRequest:
    return GmailSendRequest(
        message=GmailSendDraft(
            recipient="recipient@example.com",
            subject="Café subject",
            body="Line 1\nLine 2\n",
        )
    )


def test_send_builds_exact_single_post_and_plain_text_mime() -> None:
    calls = []

    def transport(http_request, timeout):
        calls.append((http_request, timeout))
        return Response(200, b'{"id":"gmail-message-id-1"}')

    client = GmailSendClient(transport=transport)
    result = client.send_message(
        SecretStr("access-token"),
        sender="owner@example.com",
        request=request(),
    )

    assert result.message_id == "gmail-message-id-1"
    assert len(calls) == 1

    http_request, timeout = calls[0]
    assert http_request.full_url == GMAIL_SEND_URL
    assert http_request.method == "POST"
    assert timeout == 5.0
    assert http_request.get_header("Authorization") == "Bearer access-token"
    assert http_request.get_header("Content-type") == "application/json"

    payload = json.loads(http_request.data.decode("utf-8"))
    assert set(payload) == {"raw"}
    raw = base64.urlsafe_b64decode(payload["raw"].encode("ascii"))
    message = BytesParser(policy=policy.default).parsebytes(raw)

    assert message["From"] == "owner@example.com"
    assert message["To"] == "recipient@example.com"
    assert message["Subject"] == "Café subject"
    assert message.get_content_type() == "text/plain"
    wire_body = message.get_content()
    assert "\r\n" in wire_body
    assert wire_body.replace("\r\n", "\n") == "Line 1\nLine 2\n"
    assert message["Cc"] is None
    assert message["Bcc"] is None
    assert message["Reply-To"] is None
    assert not message.is_multipart()


@pytest.mark.parametrize(
    ("status", "code", "indeterminate"),
    [
        (400, GMAIL_SEND_ERROR_PROVIDER_REJECTED, False),
        (401, GMAIL_SEND_ERROR_PROVIDER_REJECTED, False),
        (403, GMAIL_SEND_ERROR_PROVIDER_REJECTED, False),
        (429, GMAIL_SEND_ERROR_RATE_LIMITED, False),
        (408, GMAIL_SEND_ERROR_INDETERMINATE, True),
        (500, GMAIL_SEND_ERROR_INDETERMINATE, True),
        (503, GMAIL_SEND_ERROR_INDETERMINATE, True),
    ],
)
def test_http_status_classification(
    status: int,
    code: str,
    indeterminate: bool,
) -> None:
    calls = 0

    def transport(http_request, timeout):
        nonlocal calls
        calls += 1
        return Response(status, b"{}")

    client = GmailSendClient(transport=transport)
    with pytest.raises(GmailSendConnectorError) as caught:
        client.send_message(
            SecretStr("access-token"),
            sender="owner@example.com",
            request=request(),
        )

    assert calls == 1
    assert caught.value.code == code
    assert caught.value.provider_attempted is True
    assert caught.value.indeterminate is indeterminate


def test_timeout_is_indeterminate_and_never_retried() -> None:
    calls = 0

    def transport(http_request, timeout):
        nonlocal calls
        calls += 1
        raise socket.timeout("synthetic timeout")

    client = GmailSendClient(transport=transport)
    with pytest.raises(GmailSendConnectorError) as caught:
        client.send_message(
            SecretStr("access-token"),
            sender="owner@example.com",
            request=request(),
        )

    assert calls == 1
    assert caught.value.code == GMAIL_SEND_ERROR_INDETERMINATE
    assert caught.value.provider_attempted is True
    assert caught.value.indeterminate is True


@pytest.mark.parametrize(
    "body",
    [
        b"",
        b"not-json",
        b"[]",
        b"{}",
        b'{"id":""}',
        b'{"id":" bad "}',
    ],
)
def test_invalid_200_response_is_indeterminate(body: bytes) -> None:
    client = GmailSendClient(
        transport=lambda request, timeout: Response(200, body)
    )
    with pytest.raises(GmailSendConnectorError) as caught:
        client.send_message(
            SecretStr("access-token"),
            sender="owner@example.com",
            request=request(),
        )

    assert caught.value.code == GMAIL_SEND_ERROR_INDETERMINATE
    assert caught.value.provider_attempted is True
    assert caught.value.indeterminate is True


def test_http_error_classification_uses_status_without_retry() -> None:
    calls = 0

    def transport(request, timeout):
        nonlocal calls
        calls += 1
        raise urllib.error.HTTPError(
            request.full_url,
            429,
            "rate limited",
            hdrs=None,
            fp=None,
        )

    client = GmailSendClient(transport=transport)
    with pytest.raises(GmailSendConnectorError) as caught:
        client.send_message(
            SecretStr("access-token"),
            sender="owner@example.com",
            request=request(),
        )

    assert calls == 1
    assert caught.value.code == GMAIL_SEND_ERROR_RATE_LIMITED
    assert caught.value.provider_attempted is True
    assert caught.value.indeterminate is False


def test_invalid_local_inputs_do_not_attempt_provider() -> None:
    calls = 0

    def transport(request, timeout):
        nonlocal calls
        calls += 1
        raise AssertionError("provider transport must not be reached")

    client = GmailSendClient(transport=transport)

    for token, sender in (
        (SecretStr(""), "owner@example.com"),
        (SecretStr("token"), "owner@localhost"),
    ):
        with pytest.raises(GmailSendConnectorError) as caught:
            client.send_message(
                token,
                sender=sender,
                request=request(),
            )
        assert caught.value.provider_attempted is False
        assert caught.value.indeterminate is False

    assert calls == 0
