"""D75 private ModuleAdapter for one approved Google Calendar update."""

from __future__ import annotations

from app.connectors.google_calendar_write import (
    GOOGLE_CALENDAR_UPDATE_ERROR_INDETERMINATE,
    GoogleCalendarEventUpdater,
    GoogleCalendarWriteClient,
    GoogleCalendarWriteError,
)
from app.contracts.command import CommandRequest, ExecutionPlan, Result
from app.contracts.google_calendar import (
    GOOGLE_CALENDAR_CREDENTIAL_AUTH_SCHEME,
    GOOGLE_CALENDAR_CREDENTIAL_PROVIDER_ID,
    GOOGLE_CALENDAR_CREDENTIAL_SCOPE,
    GOOGLE_CALENDAR_PLUGIN_ID,
    GOOGLE_CALENDAR_PLUGIN_VERSION,
    GOOGLE_CALENDAR_UPDATE_CAPABILITY_NAME,
    GOOGLE_CALENDAR_UPDATE_CREDENTIAL_PROFILE_ID,
)
from app.contracts.google_calendar_update_delete_execution import (
    GOOGLE_CALENDAR_UPDATE_ADAPTER_ID,
    GOOGLE_CALENDAR_UPDATE_MODULE_NAME,
    calendar_update_request_from_parameters,
)
from app.contracts.google_calendar_write import GOOGLE_CALENDAR_UPDATE_EVENT_OPERATION
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION
from app.services.calendar_write_approval import calendar_write_digest
from app.services.credential_access_broker import (
    CredentialAccessBroker,
    CredentialAccessError,
)

CALENDAR_UPDATE_ERROR_CREDENTIAL_UNAVAILABLE = (
    "calendar_update_credential_unavailable"
)


class GoogleCalendarUpdateModuleAdapter:
    """Execute exactly one authorized update through D62 and D75."""

    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION

    def __init__(
        self,
        *,
        credential_broker: CredentialAccessBroker,
        client: GoogleCalendarEventUpdater | None = None,
    ) -> None:
        if not isinstance(credential_broker, CredentialAccessBroker):
            raise TypeError("credential_broker must be CredentialAccessBroker.")
        self._credential_broker = credential_broker
        self._client = GoogleCalendarWriteClient() if client is None else client

    @property
    def adapter_id(self) -> str:
        return GOOGLE_CALENDAR_UPDATE_ADAPTER_ID

    @property
    def module_name(self) -> str:
        return GOOGLE_CALENDAR_UPDATE_MODULE_NAME

    def execute(self, request: CommandRequest, plan: ExecutionPlan) -> Result:
        if request.request_id != plan.request_id:
            return self._failed(request.request_id, "request_plan_mismatch")
        if plan.adapter_id != self.adapter_id:
            return self._failed(request.request_id, "adapter_mismatch")
        if plan.owner_approval_required:
            return self._failed(request.request_id, "owner_approval_required")
        if len(plan.steps) != 1:
            return self._failed(request.request_id, "invalid_plan_shape")
        step = plan.steps[0]
        if (
            step.sequence != 1
            or step.operation != GOOGLE_CALENDAR_UPDATE_EVENT_OPERATION
        ):
            return self._failed(request.request_id, "unsupported_operation")
        try:
            update_request, write_digest = calendar_update_request_from_parameters(
                step.parameters
            )
        except ValueError:
            return self._failed(
                request.request_id,
                "calendar_update_parameters_invalid",
            )
        if calendar_write_digest(update_request) != write_digest:
            return self._failed(
                request.request_id,
                "calendar_update_parameters_invalid",
            )

        try:
            credential = self._credential_broker.resolve(
                GOOGLE_CALENDAR_PLUGIN_ID,
                GOOGLE_CALENDAR_PLUGIN_VERSION,
                GOOGLE_CALENDAR_UPDATE_CAPABILITY_NAME,
            )
        except CredentialAccessError:
            return self._failed(
                request.request_id,
                CALENDAR_UPDATE_ERROR_CREDENTIAL_UNAVAILABLE,
            )
        except Exception:
            return self._failed(
                request.request_id,
                CALENDAR_UPDATE_ERROR_CREDENTIAL_UNAVAILABLE,
            )

        if (
            credential.profile_id != GOOGLE_CALENDAR_UPDATE_CREDENTIAL_PROFILE_ID
            or credential.plugin_id != GOOGLE_CALENDAR_PLUGIN_ID
            or credential.plugin_version != GOOGLE_CALENDAR_PLUGIN_VERSION
            or credential.capability_name != GOOGLE_CALENDAR_UPDATE_CAPABILITY_NAME
            or credential.provider_id != GOOGLE_CALENDAR_CREDENTIAL_PROVIDER_ID
            or credential.auth_scheme != GOOGLE_CALENDAR_CREDENTIAL_AUTH_SCHEME
            or credential.required_scopes != (GOOGLE_CALENDAR_CREDENTIAL_SCOPE,)
        ):
            return self._failed(
                request.request_id,
                CALENDAR_UPDATE_ERROR_CREDENTIAL_UNAVAILABLE,
            )

        try:
            result = self._client.update_event(
                credential.secret,
                target=update_request.target,
                changes=update_request.changes,
            )
        except GoogleCalendarWriteError as error:
            return self._failed(
                request.request_id,
                (
                    GOOGLE_CALENDAR_UPDATE_ERROR_INDETERMINATE
                    if error.indeterminate
                    else error.code
                ),
            )
        except Exception:
            return self._failed(
                request.request_id,
                GOOGLE_CALENDAR_UPDATE_ERROR_INDETERMINATE,
            )
        if result.event_id != update_request.target.event_id:
            return self._failed(
                request.request_id,
                GOOGLE_CALENDAR_UPDATE_ERROR_INDETERMINATE,
            )
        return Result(
            request_id=request.request_id,
            status="succeeded",
            output={"event_id": result.event_id},
        )

    @staticmethod
    def _failed(request_id: str, code: str) -> Result:
        return Result(request_id=request_id, status="failed", error=code)


__all__ = [
    "CALENDAR_UPDATE_ERROR_CREDENTIAL_UNAVAILABLE",
    "GoogleCalendarUpdateModuleAdapter",
]
