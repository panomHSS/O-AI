"""D88 private ModuleAdapter for one authorized Gmail send attempt."""

from __future__ import annotations

from app.connectors.gmail_send import (
    GMAIL_SEND_ERROR_INDETERMINATE,
    GmailMessageSender,
    GmailSendClient,
    GmailSendConnectorError,
)
from app.contracts.command import CommandRequest, ExecutionPlan, Result
from app.contracts.gmail import (
    GMAIL_CREDENTIAL_AUTH_SCHEME,
    GMAIL_CREDENTIAL_PROVIDER_ID,
    GMAIL_PLUGIN_ID,
    GMAIL_PLUGIN_VERSION,
)
from app.contracts.gmail_send import GMAIL_SEND_OPERATION
from app.contracts.gmail_send_execution import (
    GMAIL_SEND_ADAPTER_ID,
    GMAIL_SEND_CAPABILITY_NAME,
    GMAIL_SEND_CREDENTIAL_PROFILE_ID,
    GMAIL_SEND_CREDENTIAL_SCOPE,
    gmail_send_request_from_parameters,
)
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION
from app.services.credential_access_broker import (
    CredentialAccessBroker,
    CredentialAccessError,
)
from app.services.gmail_send_approval import gmail_send_digest


GMAIL_SEND_ERROR_CREDENTIAL_UNAVAILABLE = (
    "gmail_send_credential_unavailable"
)


class GmailSendModuleAdapter:
    """Execute one already-authorized exact D88 send through D62."""

    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION

    def __init__(
        self,
        *,
        credential_broker: CredentialAccessBroker,
        client: GmailMessageSender | None = None,
    ) -> None:
        if not isinstance(credential_broker, CredentialAccessBroker):
            raise TypeError(
                "credential_broker must be CredentialAccessBroker."
            )
        self._credential_broker = credential_broker
        self._client = GmailSendClient() if client is None else client

    @property
    def adapter_id(self) -> str:
        return GMAIL_SEND_ADAPTER_ID

    @property
    def module_name(self) -> str:
        return "Gmail Send Message"

    def execute(
        self,
        request: CommandRequest,
        plan: ExecutionPlan,
    ) -> Result:
        if request.request_id != plan.request_id:
            return self._failed(
                request.request_id,
                "request_plan_mismatch",
                provider_attempted=False,
            )
        if plan.adapter_id != self.adapter_id:
            return self._failed(
                request.request_id,
                "adapter_mismatch",
                provider_attempted=False,
            )
        if plan.owner_approval_required:
            return self._failed(
                request.request_id,
                "owner_approval_required",
                provider_attempted=False,
            )
        if len(plan.steps) != 1:
            return self._failed(
                request.request_id,
                "invalid_plan_shape",
                provider_attempted=False,
            )

        step = plan.steps[0]
        if step.sequence != 1 or step.operation != GMAIL_SEND_OPERATION:
            return self._failed(
                request.request_id,
                "unsupported_operation",
                provider_attempted=False,
            )

        try:
            send_request, send_digest, sender = (
                gmail_send_request_from_parameters(step.parameters)
            )
        except ValueError:
            return self._failed(
                request.request_id,
                "gmail_send_execution_parameters_invalid",
                provider_attempted=False,
            )

        if gmail_send_digest(send_request) != send_digest:
            return self._failed(
                request.request_id,
                "gmail_send_execution_parameters_invalid",
                provider_attempted=False,
            )

        try:
            credential = self._credential_broker.resolve(
                GMAIL_PLUGIN_ID,
                GMAIL_PLUGIN_VERSION,
                GMAIL_SEND_CAPABILITY_NAME,
            )
        except CredentialAccessError:
            return self._failed(
                request.request_id,
                GMAIL_SEND_ERROR_CREDENTIAL_UNAVAILABLE,
                provider_attempted=False,
            )
        except Exception:
            return self._failed(
                request.request_id,
                GMAIL_SEND_ERROR_CREDENTIAL_UNAVAILABLE,
                provider_attempted=False,
            )

        if (
            credential.profile_id != GMAIL_SEND_CREDENTIAL_PROFILE_ID
            or credential.plugin_id != GMAIL_PLUGIN_ID
            or credential.plugin_version != GMAIL_PLUGIN_VERSION
            or credential.capability_name != GMAIL_SEND_CAPABILITY_NAME
            or credential.provider_id != GMAIL_CREDENTIAL_PROVIDER_ID
            or credential.auth_scheme != GMAIL_CREDENTIAL_AUTH_SCHEME
            or credential.required_scopes != (GMAIL_SEND_CREDENTIAL_SCOPE,)
        ):
            return self._failed(
                request.request_id,
                GMAIL_SEND_ERROR_CREDENTIAL_UNAVAILABLE,
                provider_attempted=False,
            )

        try:
            provider_result = self._client.send_message(
                credential.secret,
                sender=sender,
                request=send_request,
            )
        except GmailSendConnectorError as error:
            return self._failed(
                request.request_id,
                error.code,
                provider_attempted=error.provider_attempted,
            )
        except Exception:
            return self._failed(
                request.request_id,
                GMAIL_SEND_ERROR_INDETERMINATE,
                provider_attempted=True,
            )

        return Result(
            request_id=request.request_id,
            status="succeeded",
            output={
                "message_id": provider_result.message_id,
                "provider_attempted": True,
            },
        )

    @staticmethod
    def _failed(
        request_id: str,
        code: str,
        *,
        provider_attempted: bool,
    ) -> Result:
        return Result(
            request_id=request_id,
            status="failed",
            output={"provider_attempted": provider_attempted},
            error=code,
        )


__all__ = [
    "GMAIL_SEND_ERROR_CREDENTIAL_UNAVAILABLE",
    "GmailSendModuleAdapter",
]
