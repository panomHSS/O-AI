"""D77 authenticated bounded read-only Gmail Plugin."""

from __future__ import annotations

import json

from app.connectors.gmail import (
    GMAIL_ERROR_AUTH_FAILED,
    GMAIL_ERROR_RESPONSE_INVALID,
    GMAIL_ERROR_UNAVAILABLE,
    GMAIL_MAX_RESULT_BYTES,
    GmailClient,
    GmailConnectorError,
    GmailReader,
)
from app.contracts.gmail import (
    GMAIL_ADAPTER_ID,
    GMAIL_CAPABILITY_ID,
    GMAIL_CREDENTIAL_AUTH_SCHEME,
    GMAIL_CREDENTIAL_PROVIDER_ID,
    GMAIL_CREDENTIAL_SCOPE,
    GMAIL_OPERATION,
    GMAIL_PLUGIN_ID,
    GMAIL_PLUGIN_VERSION,
    GMAIL_READ_CAPABILITY_NAME,
    GMAIL_READ_CREDENTIAL_PROFILE_ID,
    GmailMessage,
    GmailReadQuery,
    GmailReadResult,
)
from app.plugins.base import Plugin
from app.plugins.context import PluginExecutionContext
from app.plugins.request import PluginRequest
from app.plugins.response import PluginResult
from app.services.credential_access_broker import (
    CredentialAccessBroker,
    CredentialAccessError,
)

_GMAIL_MAX_PLUGIN_INPUT_BYTES = 1024


class GmailPlugin(Plugin):
    """Read one approved bounded Gmail query through the exact D76 credential."""

    def __init__(
        self,
        *,
        credential_broker: CredentialAccessBroker,
        client: GmailReader | None = None,
    ) -> None:
        if not isinstance(credential_broker, CredentialAccessBroker):
            raise TypeError("credential_broker must be CredentialAccessBroker.")
        self._credential_broker = credential_broker
        self._client = GmailClient() if client is None else client

    @property
    def id(self) -> str:
        return GMAIL_PLUGIN_ID

    @property
    def name(self) -> str:
        return "Gmail Read Messages"

    @property
    def version(self) -> str:
        return GMAIL_PLUGIN_VERSION

    def execute(
        self,
        context: PluginExecutionContext,
        request: PluginRequest,
    ) -> PluginResult:
        query = self._validated_query(request)
        try:
            credential = self._credential_broker.resolve(
                GMAIL_PLUGIN_ID,
                GMAIL_PLUGIN_VERSION,
                GMAIL_READ_CAPABILITY_NAME,
            )
        except CredentialAccessError:
            raise GmailConnectorError(GMAIL_ERROR_AUTH_FAILED) from None
        except Exception:
            raise GmailConnectorError(GMAIL_ERROR_AUTH_FAILED) from None

        if (
            credential.profile_id != GMAIL_READ_CREDENTIAL_PROFILE_ID
            or credential.plugin_id != GMAIL_PLUGIN_ID
            or credential.plugin_version != GMAIL_PLUGIN_VERSION
            or credential.capability_name != GMAIL_READ_CAPABILITY_NAME
            or credential.provider_id != GMAIL_CREDENTIAL_PROVIDER_ID
            or credential.auth_scheme != GMAIL_CREDENTIAL_AUTH_SCHEME
            or credential.required_scopes != (GMAIL_CREDENTIAL_SCOPE,)
        ):
            raise GmailConnectorError(GMAIL_ERROR_AUTH_FAILED)

        try:
            read_result = self._client.read_messages(
                credential.secret,
                query=query,
            )
        except GmailConnectorError:
            raise
        except Exception:
            raise GmailConnectorError(GMAIL_ERROR_UNAVAILABLE) from None

        if (
            not isinstance(read_result, GmailReadResult)
            or any(
                not isinstance(message, GmailMessage)
                for message in read_result.messages
            )
        ):
            raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID)

        content = json.dumps(
            {
                "messages": [
                    message.as_dict() for message in read_result.messages
                ]
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        if len(content.encode("utf-8")) > GMAIL_MAX_RESULT_BYTES:
            raise GmailConnectorError(GMAIL_ERROR_RESPONSE_INVALID)
        return PluginResult(content=content)

    @staticmethod
    def _validated_query(request: object) -> GmailReadQuery:
        if (
            not isinstance(request, PluginRequest)
            or not isinstance(request.content, str)
            or len(request.content.encode("utf-8"))
            > _GMAIL_MAX_PLUGIN_INPUT_BYTES
        ):
            raise GmailConnectorError("gmail_query_invalid")
        try:
            payload = json.loads(request.content)
            return GmailReadQuery.from_parameters(payload)
        except (json.JSONDecodeError, TypeError, ValueError):
            raise GmailConnectorError("gmail_query_invalid") from None


__all__ = [
    "GMAIL_ADAPTER_ID",
    "GMAIL_CAPABILITY_ID",
    "GMAIL_OPERATION",
    "GMAIL_PLUGIN_ID",
    "GMAIL_PLUGIN_VERSION",
    "GmailPlugin",
]
