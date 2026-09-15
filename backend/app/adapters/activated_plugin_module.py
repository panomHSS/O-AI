"""D58 activation-aware ModuleAdapter wrapper for stale-snapshot safety."""

from __future__ import annotations

from collections.abc import Callable

from app.contracts.command import CommandRequest, ExecutionPlan, Result
from app.contracts.plugin_registration_activation import (
    PluginRegistrationActivationRecord,
)
from app.contracts.tool_module import (
    TOOL_MODULE_ADAPTER_CONTRACT_VERSION,
    ModuleAdapter,
)

PLUGIN_REGISTRATION_INACTIVE = "plugin_registration_inactive"

ActivationChecker = Callable[
    [PluginRegistrationActivationRecord, object],
    bool,
]


class ActivatedPluginModuleAdapter:
    """Guard a D56 ModuleAdapter with the current D58 activation token."""

    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION

    def __init__(
        self,
        *,
        record: PluginRegistrationActivationRecord,
        activation_token: object,
        delegate: ModuleAdapter,
        checker: ActivationChecker,
    ) -> None:
        self._record = record
        self._activation_token = activation_token
        self._delegate = delegate
        self._checker = checker

    @property
    def adapter_id(self) -> str:
        return self._record.module_adapter_id

    @property
    def module_name(self) -> str:
        return self._record.module_name

    def execute(
        self,
        request: CommandRequest,
        plan: ExecutionPlan,
    ) -> Result:
        try:
            active = self._checker(self._record, self._activation_token)
        except Exception:
            active = False
        if not active:
            return Result(
                request_id=request.request_id,
                status="failed",
                error=PLUGIN_REGISTRATION_INACTIVE,
            )
        return self._delegate.execute(request, plan)
