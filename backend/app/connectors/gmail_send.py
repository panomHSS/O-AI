"""D88 bounded Gmail provider send transport.

This connector performs at most one Gmail messages.send HTTP attempt per call.
It never retries, follows redirects, uses proxies, resolves credentials, claims
approval authority, or exposes provider response bodies.
"""

from __future__ import annotations

import base64
import json
import socket
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass
from email import policy
from email.message import EmailMessage
from typing import Protocol

from pydantic import SecretStr

from app.contracts.gmail_send import GmailSendRequest
from app.contracts.gmail_send_execution import validate_sender


GMAIL_SEND_URL = (
    "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
)
GMAIL_SEND_TIMEOUT_SECONDS = 5.0
GMAIL_SEND_MAX_RESPONSE_BYTES = 64 * 1024
GMAIL_SEND_MAX_PROVIDER_MESSAGE_ID_BYTES = 1024

GMAIL_SEND_ERROR_INVALID_REQUEST = "gmail_send_invalid_request"
GMAIL_SEND_ERROR_PROVIDER_REJECTED = "gmail_send_provider_rejected"
GMAIL_SEND_ERROR_RATE_LIMITED = "gmail_send_rate_limited"
GMAIL_SEND_ERROR_INDETERMINATE = "gmail_send_indeterminate"


class GmailSendConnectorError(RuntimeError):
    """Safe send error with stable code and provider-attempt truth only."""

    def __init__(
        self,
        code: str,
        *,
        provider_attempted: bool,
        indeterminate: bool,
    ) -> None:
        self.code = code
        self.provider_attempted = provider_attempted
        self.indeterminate = indeterminate
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class GmailSendProviderResult:
    """Minimal successful provider projection."""

    message_id: str


class GmailMessageSender(Protocol):
    def send_message(
        self,
        access_token: SecretStr,
        *,
        sender: str,
        request: GmailSendRequest,
    ) -> GmailSendProviderResult: ...


class GmailSendTransport(Protocol):
    def __call__(
        self,
        request: urllib.request.Request,
        timeout_seconds: float,
    ) -> object: ...


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _open_without_redirects_or_proxies(
    request: urllib.request.Request,
    timeout_seconds: float,
):
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        _NoRedirectHandler(),
    )
    return opener.open(request, timeout=timeout_seconds)


class GmailSendClient:
    """Perform exactly one bounded Gmail messages.send attempt per call."""

    def __init__(
        self,
        *,
        timeout_seconds: float = GMAIL_SEND_TIMEOUT_SECONDS,
        transport: GmailSendTransport | None = None,
    ) -> None:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be positive.")
        self._timeout_seconds = float(timeout_seconds)
        self._transport = transport or _open_without_redirects_or_proxies

    def send_message(
        self,
        access_token: SecretStr,
        *,
        sender: str,
        request: GmailSendRequest,
    ) -> GmailSendProviderResult:
        token = self._validated_token(access_token)
        sender = self._validated_sender(sender)
        if not isinstance(request, GmailSendRequest):
            raise GmailSendConnectorError(
                GMAIL_SEND_ERROR_INVALID_REQUEST,
                provider_attempted=False,
                indeterminate=False,
            )

        raw = self._raw_message(sender=sender, request=request)
        body = json.dumps(
            {"raw": raw},
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        http_request = urllib.request.Request(
            GMAIL_SEND_URL,
            data=body,
            method="POST",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "O-AI-D88-Gmail-Send",
            },
        )
        response_body = self._perform(http_request)
        return GmailSendProviderResult(
            message_id=self._response_message_id(response_body)
        )

    @staticmethod
    def _validated_token(access_token: object) -> str:
        if not isinstance(access_token, SecretStr):
            raise GmailSendConnectorError(
                GMAIL_SEND_ERROR_INVALID_REQUEST,
                provider_attempted=False,
                indeterminate=False,
            )
        token = access_token.get_secret_value()
        if (
            not token
            or len(token.encode("utf-8")) > 8192
            or "\r" in token
            or "\n" in token
        ):
            raise GmailSendConnectorError(
                GMAIL_SEND_ERROR_INVALID_REQUEST,
                provider_attempted=False,
                indeterminate=False,
            )
        return token

    @staticmethod
    def _validated_sender(sender: object) -> str:
        try:
            return validate_sender(sender)
        except (TypeError, ValueError):
            raise GmailSendConnectorError(
                GMAIL_SEND_ERROR_INVALID_REQUEST,
                provider_attempted=False,
                indeterminate=False,
            ) from None

    @staticmethod
    def _raw_message(
        *,
        sender: str,
        request: GmailSendRequest,
    ) -> str:
        try:
            message = EmailMessage(policy=policy.SMTP)
            message["From"] = sender
            message["To"] = request.message.recipient
            message["Subject"] = request.message.subject
            message.set_content(
                request.message.body,
                subtype="plain",
                charset="utf-8",
            )
            encoded = base64.urlsafe_b64encode(
                message.as_bytes(policy=policy.SMTP)
            ).decode("ascii")
        except Exception:
            raise GmailSendConnectorError(
                GMAIL_SEND_ERROR_INVALID_REQUEST,
                provider_attempted=False,
                indeterminate=False,
            ) from None
        if not encoded:
            raise GmailSendConnectorError(
                GMAIL_SEND_ERROR_INVALID_REQUEST,
                provider_attempted=False,
                indeterminate=False,
            )
        return encoded

    def _perform(self, request: urllib.request.Request) -> bytes:
        try:
            context = self._transport(request, self._timeout_seconds)
            with context as response:
                status = getattr(response, "status", None)
                self._raise_status(status)
                body = response.read(GMAIL_SEND_MAX_RESPONSE_BYTES + 1)
        except GmailSendConnectorError:
            raise
        except urllib.error.HTTPError as error:
            try:
                self._raise_status(error.code)
            finally:
                error.close()
            raise GmailSendConnectorError(
                GMAIL_SEND_ERROR_INDETERMINATE,
                provider_attempted=True,
                indeterminate=True,
            ) from None
        except (socket.timeout, TimeoutError, urllib.error.URLError):
            raise GmailSendConnectorError(
                GMAIL_SEND_ERROR_INDETERMINATE,
                provider_attempted=True,
                indeterminate=True,
            ) from None
        except Exception:
            raise GmailSendConnectorError(
                GMAIL_SEND_ERROR_INDETERMINATE,
                provider_attempted=True,
                indeterminate=True,
            ) from None

        if not isinstance(body, bytes):
            raise GmailSendConnectorError(
                GMAIL_SEND_ERROR_INDETERMINATE,
                provider_attempted=True,
                indeterminate=True,
            )
        if len(body) > GMAIL_SEND_MAX_RESPONSE_BYTES:
            raise GmailSendConnectorError(
                GMAIL_SEND_ERROR_INDETERMINATE,
                provider_attempted=True,
                indeterminate=True,
            )
        return body

    @staticmethod
    def _raise_status(status: object) -> None:
        if status == 200:
            return
        if status == 429:
            raise GmailSendConnectorError(
                GMAIL_SEND_ERROR_RATE_LIMITED,
                provider_attempted=True,
                indeterminate=False,
            )
        if status == 408 or (
            isinstance(status, int) and 500 <= status <= 599
        ):
            raise GmailSendConnectorError(
                GMAIL_SEND_ERROR_INDETERMINATE,
                provider_attempted=True,
                indeterminate=True,
            )
        if isinstance(status, int) and 400 <= status <= 499:
            raise GmailSendConnectorError(
                GMAIL_SEND_ERROR_PROVIDER_REJECTED,
                provider_attempted=True,
                indeterminate=False,
            )
        raise GmailSendConnectorError(
            GMAIL_SEND_ERROR_INDETERMINATE,
            provider_attempted=True,
            indeterminate=True,
        )

    @staticmethod
    def _response_message_id(body: bytes) -> str:
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise GmailSendConnectorError(
                GMAIL_SEND_ERROR_INDETERMINATE,
                provider_attempted=True,
                indeterminate=True,
            ) from None
        if not isinstance(payload, dict):
            raise GmailSendConnectorError(
                GMAIL_SEND_ERROR_INDETERMINATE,
                provider_attempted=True,
                indeterminate=True,
            )
        message_id = payload.get("id")
        if (
            not isinstance(message_id, str)
            or not message_id
            or message_id != message_id.strip()
            or len(message_id.encode("utf-8"))
            > GMAIL_SEND_MAX_PROVIDER_MESSAGE_ID_BYTES
            or any(
                unicodedata.category(character) == "Cc"
                for character in message_id
            )
        ):
            raise GmailSendConnectorError(
                GMAIL_SEND_ERROR_INDETERMINATE,
                provider_attempted=True,
                indeterminate=True,
            )
        return message_id


__all__ = [
    "GMAIL_SEND_ERROR_INDETERMINATE",
    "GMAIL_SEND_ERROR_INVALID_REQUEST",
    "GMAIL_SEND_ERROR_PROVIDER_REJECTED",
    "GMAIL_SEND_ERROR_RATE_LIMITED",
    "GMAIL_SEND_MAX_RESPONSE_BYTES",
    "GMAIL_SEND_TIMEOUT_SECONDS",
    "GMAIL_SEND_URL",
    "GmailMessageSender",
    "GmailSendClient",
    "GmailSendConnectorError",
    "GmailSendProviderResult",
]
