"""D77 bounded authenticated read-only Gmail connector."""

from __future__ import annotations

import base64
import binascii
import json
import socket
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Protocol

from pydantic import SecretStr

from app.contracts.gmail import (
    GMAIL_MAX_BODY_CHARS,
    GMAIL_MAX_FROM_CHARS,
    GMAIL_MAX_MESSAGE_ID_BYTES,
    GMAIL_MAX_RESULTS,
    GMAIL_MAX_SNIPPET_CHARS,
    GMAIL_MAX_SUBJECT_CHARS,
    GmailMessage,
    GmailReadQuery,
    GmailReadResult,
)


GMAIL_API_BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me"
GMAIL_MESSAGES_URL = f"{GMAIL_API_BASE_URL}/messages"
GMAIL_TIMEOUT_SECONDS = 5.0
GMAIL_LIST_MAX_RESPONSE_BYTES = 64 * 1024
GMAIL_MESSAGE_MAX_RESPONSE_BYTES = 256 * 1024
GMAIL_MAX_RESULT_BYTES = 32 * 1024
GMAIL_MAX_MIME_DEPTH = 16
GMAIL_MAX_MIME_PARTS = 128
GMAIL_MAX_HEADERS = 256
GMAIL_MAX_LABELS = 128
GMAIL_LIST_FIELDS = "messages(id),nextPageToken"

GMAIL_ERROR_AUTH_FAILED = "gmail_auth_failed"
GMAIL_ERROR_UNAVAILABLE = "gmail_unavailable"
GMAIL_ERROR_RATE_LIMITED = "gmail_rate_limited"
GMAIL_ERROR_RESPONSE_INVALID = "gmail_response_invalid"
GMAIL_ERROR_RESPONSE_TOO_LARGE = "gmail_response_too_large"
GMAIL_ERROR_MESSAGE_NOT_FOUND = "gmail_message_not_found"
GMAIL_ERROR_QUERY_INVALID = "gmail_query_invalid"


class GmailConnectorError(ValueError):
    """Safe Gmail connector error containing only one stable reason code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class GmailReader(Protocol):
    def read_messages(
        self,
        access_token: SecretStr,
        *,
        query: GmailReadQuery,
    ) -> GmailReadResult:
        ...


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects rather than granting another network hop."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _open_without_redirects(
    request: urllib.request.Request,
    timeout_seconds: float,
):
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        _NoRedirectHandler(),
    )
    return opener.open(request, timeout=timeout_seconds)


Transport = Callable[[urllib.request.Request, float], object]


class GmailClient:
    """Read at most five exact messages through the D76 Gmail credential."""

    def __init__(
        self,
        *,
        timeout_seconds: float = GMAIL_TIMEOUT_SECONDS,
        transport: Transport | None = None,
    ) -> None:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be positive.")
        self._timeout_seconds = float(timeout_seconds)
        self._transport = (
            _open_without_redirects if transport is None else transport
        )

    def read_messages(
        self,
        access_token: SecretStr,
        *,
        query: GmailReadQuery,
    ) -> GmailReadResult:
        self._validate_query(query)
        token = self._validated_token(access_token)

        list_request = self._build_list_request(token, query)
        list_payload = self._request_json(
            list_request,
            max_bytes=GMAIL_LIST_MAX_RESPONSE_BYTES,
            message_lookup=False,
        )
        message_ids = self._parse_message_ids(list_payload)

        messages = tuple(
            self._read_one_message(token, message_id)
            for message_id in message_ids
        )
        result = GmailReadResult(messages=messages)
        serialized = json.dumps(
            {"messages": [message.as_dict() for message in result.messages]},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(serialized) > GMAIL_MAX_RESULT_BYTES:
            raise GmailConnectorError(GMAIL_ERROR_RESPONSE_TOO_LARGE)
        return result

    @staticmethod
    def _validate_query(query: object) -> None:
        if not isinstance(query, GmailReadQuery):
            raise GmailConnectorError(GMAIL_ERROR_QUERY_INVALID)

    @staticmethod
    def _validated_token(access_token: object) -> str:
        if not isinstance(access_token, SecretStr):
            raise GmailConnectorError(GMAIL_ERROR_AUTH_FAILED)
        token = access_token.get_secret_value()
        if (
            not token
            or len(token.encode("utf-8")) > 8192
            or "\r" in token
            or "\n" in token
        ):
            raise GmailConnectorError(GMAIL_ERROR_AUTH_FAILED)
        return token

    def _build_list_request(
        self,
        token: str,
        query: GmailReadQuery,
    ) -> urllib.request.Request:
        parameters: list[tuple[str, str]] = [
            ("maxResults", str(GMAIL_MAX_RESULTS)),
            ("includeSpamTrash", "false"),
            ("fields", GMAIL_LIST_FIELDS),
        ]
        if query.provider_query is not None:
            parameters.append(("q", query.provider_query))
        encoded = urllib.parse.urlencode(parameters)
        return self._request(
            f"{GMAIL_MESSAGES_URL}?{encoded}",
            token,
        )

    def _read_one_message(
        self,
        token: str,
        message_id: str,
    ) -> GmailMessage:
        encoded_id = urllib.parse.quote(message_id, safe="")
        encoded_query = urllib.parse.urlencode((("format", "full"),))
        request = self._request(
            f"{GMAIL_MESSAGES_URL}/{encoded_id}?{encoded_query}",
            token,
        )
        payload = self._request_json(
            request,
            max_bytes=GMAIL_MESSAGE_MAX_RESPONSE_BYTES,
            message_lookup=True,
        )
        return self._normalize_message(payload, expected_id=message_id)

    @staticmethod
    def _request(url: str, token: str) -> urllib.request.Request:
        return urllib.request.Request(
            url,
            method="GET",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "User-Agent": "O-AI-D77-Gmail-Connector",
            },
        )

    def _request_json(
        self,
        request: urllib.request.Request,
        *,
        max_bytes: int,
        message_lookup: bool,
    ) -> dict[str, object]:
        try:
            response_context = self._transport(
                request,
                self._timeout_seconds,
            )
            with response_context as response:
                status = getattr(response, "status", None)
                self._raise_for_status(
                    status,
                    message_lookup=message_lookup,
                )
                body = response.read(max_bytes + 1)
        except GmailConnectorError:
            raise
        except (socket.timeout, TimeoutError):
            raise GmailConnectorError(GMAIL_ERROR_UNAVAILABLE) from None
        except urllib.error.HTTPError as error:
            try:
                self._raise_for_status(
                    error.code,
                    message_lookup=message_lookup,
                )
            finally:
                error.close()
            raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID) from None
        except urllib.error.URLError:
            raise GmailConnectorError(GMAIL_ERROR_UNAVAILABLE) from None
        except Exception:
            raise GmailConnectorError(GMAIL_ERROR_UNAVAILABLE) from None

        if not isinstance(body, bytes):
            raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID)
        if len(body) > max_bytes:
            raise GmailConnectorError(GMAIL_ERROR_RESPONSE_TOO_LARGE)
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID) from None
        if not isinstance(payload, dict):
            raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID)
        return payload

    @staticmethod
    def _raise_for_status(
        status: object,
        *,
        message_lookup: bool,
    ) -> None:
        if status == 200:
            return
        if status in (401, 403):
            raise GmailConnectorError(GMAIL_ERROR_AUTH_FAILED)
        if status == 404 and message_lookup:
            raise GmailConnectorError(GMAIL_ERROR_MESSAGE_NOT_FOUND)
        if status == 429:
            raise GmailConnectorError(GMAIL_ERROR_RATE_LIMITED)
        if status == 408 or (
            isinstance(status, int) and 500 <= status <= 599
        ):
            raise GmailConnectorError(GMAIL_ERROR_UNAVAILABLE)
        raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID)

    @classmethod
    def _parse_message_ids(
        cls,
        payload: dict[str, object],
    ) -> tuple[str, ...]:
        messages = payload.get("messages", [])
        if (
            not isinstance(messages, list)
            or len(messages) > GMAIL_MAX_RESULTS
        ):
            raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID)

        next_page_token = payload.get("nextPageToken")
        if next_page_token is not None and (
            not isinstance(next_page_token, str)
            or not next_page_token
            or len(next_page_token.encode("utf-8")) > 4096
        ):
            raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID)

        result: list[str] = []
        seen: set[str] = set()
        for item in messages:
            if not isinstance(item, dict) or set(item) != {"id"}:
                raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID)
            message_id = cls._validated_message_id(item.get("id"))
            if message_id in seen:
                raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID)
            seen.add(message_id)
            result.append(message_id)
        return tuple(result)

    @staticmethod
    def _validated_message_id(value: object) -> str:
        if (
            not isinstance(value, str)
            or not value
            or value != value.strip()
            or len(value.encode("utf-8")) > GMAIL_MAX_MESSAGE_ID_BYTES
            or any(
                unicodedata.category(character) == "Cc"
                for character in value
            )
        ):
            raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID)
        return value

    @classmethod
    def _normalize_message(
        cls,
        payload: dict[str, object],
        *,
        expected_id: str,
    ) -> GmailMessage:
        actual_id = cls._validated_message_id(payload.get("id"))
        if actual_id != expected_id:
            raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID)

        labels = payload.get("labelIds", [])
        if (
            not isinstance(labels, list)
            or len(labels) > GMAIL_MAX_LABELS
            or any(
                not isinstance(label, str)
                or not label
                or len(label.encode("utf-8")) > 256
                for label in labels
            )
        ):
            raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID)

        received_at = cls._normalize_internal_date(
            payload.get("internalDate")
        )
        snippet_raw = payload.get("snippet", "")
        if not isinstance(snippet_raw, str):
            raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID)

        mime_payload = payload.get("payload")
        if not isinstance(mime_payload, dict):
            raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID)

        sender = cls._header_value(mime_payload, "from")
        subject = cls._header_value(mime_payload, "subject")
        body = cls._extract_plain_text(mime_payload)

        try:
            return GmailMessage(
                message_id=actual_id,
                sender=cls._one_line(sender, GMAIL_MAX_FROM_CHARS),
                subject=cls._one_line(
                    subject,
                    GMAIL_MAX_SUBJECT_CHARS,
                ),
                received_at=received_at,
                unread="UNREAD" in labels,
                snippet=cls._one_line(
                    snippet_raw,
                    GMAIL_MAX_SNIPPET_CHARS,
                ),
                body=body[:GMAIL_MAX_BODY_CHARS],
            )
        except ValueError:
            raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID) from None

    @staticmethod
    def _normalize_internal_date(value: object) -> str:
        if (
            not isinstance(value, str)
            or not value
            or not value.isascii()
            or not value.isdigit()
            or len(value) > 20
        ):
            raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID)
        try:
            milliseconds = int(value)
            parsed = datetime.fromtimestamp(
                milliseconds / 1000,
                tz=timezone.utc,
            )
        except (OverflowError, OSError, ValueError):
            raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID) from None
        return parsed.isoformat().replace("+00:00", "Z")

    @classmethod
    def _header_value(
        cls,
        payload: dict[str, object],
        target: str,
    ) -> str:
        headers = payload.get("headers", [])
        if (
            not isinstance(headers, list)
            or len(headers) > GMAIL_MAX_HEADERS
        ):
            raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID)

        found = ""
        for header in headers:
            if not isinstance(header, dict):
                raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID)
            name = header.get("name")
            value = header.get("value")
            if not isinstance(name, str) or not isinstance(value, str):
                raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID)
            if len(name.encode("utf-8")) > 128:
                raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID)
            if not found and name.casefold() == target:
                found = value
        return found

    @classmethod
    def _extract_plain_text(
        cls,
        root: dict[str, object],
    ) -> str:
        stack: list[tuple[dict[str, object], int]] = [(root, 0)]
        visited = 0
        first_body: str | None = None

        while stack:
            part, depth = stack.pop()
            visited += 1
            if (
                depth > GMAIL_MAX_MIME_DEPTH
                or visited > GMAIL_MAX_MIME_PARTS
            ):
                raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID)

            mime_type = part.get("mimeType", "")
            filename = part.get("filename", "")
            if not isinstance(mime_type, str) or not isinstance(
                filename, str
            ):
                raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID)

            body = part.get("body", {})
            if not isinstance(body, dict):
                raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID)
            if "data" in body and not isinstance(body.get("data"), str):
                raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID)

            if (
                first_body is None
                and mime_type.casefold() == "text/plain"
                and filename == ""
                and "attachmentId" not in body
                and isinstance(body.get("data"), str)
            ):
                first_body = cls._decode_body(body["data"])

            parts = part.get("parts", [])
            if not isinstance(parts, list):
                raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID)
            if any(not isinstance(child, dict) for child in parts):
                raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID)
            for child in reversed(parts):
                stack.append((child, depth + 1))

        return "" if first_body is None else first_body

    @staticmethod
    def _decode_body(value: str) -> str:
        try:
            encoded = value.encode("ascii")
            padded = encoded + b"=" * (-len(encoded) % 4)
            decoded = base64.b64decode(
                padded,
                altchars=b"-_",
                validate=True,
            )
        except (UnicodeEncodeError, binascii.Error, ValueError):
            raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID) from None
        return decoded.decode("utf-8", errors="replace")

    @staticmethod
    def _one_line(value: str, max_chars: int) -> str:
        return " ".join(value.split())[:max_chars]


__all__ = [
    "GMAIL_API_BASE_URL",
    "GMAIL_ERROR_AUTH_FAILED",
    "GMAIL_ERROR_MESSAGE_NOT_FOUND",
    "GMAIL_ERROR_QUERY_INVALID",
    "GMAIL_ERROR_RATE_LIMITED",
    "GMAIL_ERROR_RESPONSE_INVALID",
    "GMAIL_ERROR_RESPONSE_TOO_LARGE",
    "GMAIL_ERROR_UNAVAILABLE",
    "GMAIL_LIST_FIELDS",
    "GMAIL_LIST_MAX_RESPONSE_BYTES",
    "GMAIL_MAX_MIME_DEPTH",
    "GMAIL_MAX_MIME_PARTS",
    "GMAIL_MAX_RESULT_BYTES",
    "GMAIL_MESSAGE_MAX_RESPONSE_BYTES",
    "GMAIL_MESSAGES_URL",
    "GMAIL_TIMEOUT_SECONDS",
    "GmailClient",
    "GmailConnectorError",
    "GmailReader",
]
