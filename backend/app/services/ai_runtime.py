"""D49 authorization-gated AI execution runtime."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from app.contracts.ai import (
    AI_ADAPTER_CONTRACT_VERSION,
    AIAdapter,
    AIRequest,
    AIResult,
)
from app.contracts.ai_discovery import AI_CAPABILITY_TEXT_GENERATION
from app.contracts.ai_route import LOCAL_AI_ADAPTER_ID
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep
from app.contracts.execution_authorization import ExecutionAuthorization
from app.contracts.local_ai_profile import (
    GENERAL_CHAT_PROFILE_ID,
    SOFTWARE_ENGINEERING_PROFILE_ID,
    valid_model_id,
)
from app.contracts.local_ai_runtime import (
    AUTHORIZED_LOCAL_AI_MODEL_KEY,
    AUTHORIZED_LOCAL_AI_PROFILE_KEY,
)
from app.services.adapter_registry import AdapterRegistry
from app.services.ai_usage_metering import AIUsageMeter
from app.services.execution_audit import ExecutionAuditTrail
from app.services.execution_guard import execution_plan_digest


class AIExecutionRejectedError(RuntimeError):
    """Safe internal rejection raised before an unauthorized AI invocation."""

    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


class _AuthorizedAIAdapter:
    """One-shot AIAdapter bound to one request and one authorization."""

    contract_version = AI_ADAPTER_CONTRACT_VERSION

    def __init__(
        self,
        *,
        runtime: "AIRuntime",
        request: CommandRequest,
        authorization: ExecutionAuthorization,
        adapter_id: str,
    ) -> None:
        self._runtime = runtime
        self._request = request
        self._authorization = authorization
        self._adapter_id = adapter_id
        self._consumed = False

    @property
    def adapter_id(self) -> str:
        return self._adapter_id

    def generate(self, request: AIRequest) -> AIResult:
        if self._consumed:
            raise AIExecutionRejectedError("ai_authorization_replayed")
        self._consumed = True
        return self._runtime.execute(
            self._request,
            self._authorization,
            request,
        )


class AIRuntime:
    """Invoke one registered AI adapter only through D36 authorization."""

    def __init__(
        self,
        *,
        registry: AdapterRegistry,
        audit: ExecutionAuditTrail | None = None,
        usage_meter: AIUsageMeter | None = None,
    ) -> None:
        self._registry = registry
        self._audit = audit
        self._usage_meter = usage_meter

    def bind(
        self,
        request: CommandRequest,
        authorization: ExecutionAuthorization,
    ) -> AIAdapter:
        """Validate authorization now and return a one-shot adapter proxy."""
        plan, _, _ = self._validate_execution(request, authorization)
        return _AuthorizedAIAdapter(
            runtime=self,
            request=request,
            authorization=authorization,
            adapter_id=plan.adapter_id,
        )

    def execute(
        self,
        request: CommandRequest,
        authorization: ExecutionAuthorization,
        ai_request: AIRequest,
    ) -> AIResult:
        """Revalidate immediately before the provider side effect and invoke once."""
        if not isinstance(ai_request, AIRequest) or not isinstance(
            ai_request.content,
            str,
        ):
            raise AIExecutionRejectedError("invalid_ai_request")

        plan, adapter, digest = self._validate_execution(
            request,
            authorization,
        )
        if not isinstance(ai_request.metadata, Mapping):
            raise AIExecutionRejectedError("invalid_ai_request")
        if {
            AUTHORIZED_LOCAL_AI_PROFILE_KEY,
            AUTHORIZED_LOCAL_AI_MODEL_KEY,
        }.intersection(ai_request.metadata):
            raise AIExecutionRejectedError(
                "reserved_local_ai_authorization_metadata"
            )
        if plan.adapter_id == LOCAL_AI_ADAPTER_ID:
            ai_request = replace(
                ai_request,
                metadata={
                    **ai_request.metadata,
                    AUTHORIZED_LOCAL_AI_PROFILE_KEY: plan.steps[0].parameters[
                        "local_ai_profile_id"
                    ],
                    AUTHORIZED_LOCAL_AI_MODEL_KEY: plan.steps[0].parameters[
                        "model_id"
                    ],
                },
            )
        self._record(
            request_id=request.request_id,
            action="started",
            status="started",
            adapter_id=plan.adapter_id,
            reason_code="ai_execution_started",
            plan_digest=digest,
        )
        try:
            result = adapter.generate(ai_request)
            if not isinstance(result, AIResult) or not isinstance(
                result.content,
                str,
            ):
                raise AIExecutionRejectedError("invalid_ai_result")
        except Exception:
            self._record(
                request_id=request.request_id,
                action="completed",
                status="failed",
                adapter_id=plan.adapter_id,
                reason_code="ai_execution_failed",
                plan_digest=digest,
            )
            raise

        self._record(
            request_id=request.request_id,
            action="completed",
            status="succeeded",
            adapter_id=plan.adapter_id,
            reason_code="ai_execution_succeeded",
            plan_digest=digest,
        )
        self._try_meter_success(
            request_id=request.request_id,
            plan_digest=digest,
            adapter_id=plan.adapter_id,
            authorized_model_id=plan.steps[0].parameters["model_id"],
            result=result,
        )
        return result

    def _validate_execution(
        self,
        request: CommandRequest,
        authorization: ExecutionAuthorization,
    ) -> tuple[ExecutionPlan, AIAdapter, str]:
        if not isinstance(request, CommandRequest):
            raise AIExecutionRejectedError("invalid_command_request")
        if not isinstance(authorization, ExecutionAuthorization):
            raise AIExecutionRejectedError("invalid_execution_authorization")
        if authorization.status != "authorized":
            raise AIExecutionRejectedError("ai_execution_not_authorized")
        if authorization.target_kind != "ai":
            raise AIExecutionRejectedError("authorization_target_mismatch")

        plan = authorization.execution_plan
        if not isinstance(plan, ExecutionPlan):
            raise AIExecutionRejectedError("missing_execution_plan")
        if (
            request.request_id != authorization.request_id
            or request.request_id != plan.request_id
        ):
            raise AIExecutionRejectedError("request_plan_mismatch")
        if request.command != "chat.message":
            raise AIExecutionRejectedError("authorization_policy_violation")
        if plan.owner_approval_required is not False:
            raise AIExecutionRejectedError("authorization_policy_violation")
        if len(plan.steps) != 1:
            raise AIExecutionRejectedError("authorization_policy_violation")

        step = plan.steps[0]
        if not isinstance(step, ExecutionStep) or step.sequence != 1:
            raise AIExecutionRejectedError("authorization_policy_violation")
        parameters = step.parameters
        expected_parameters = {"capability_id", "model_id"}
        if plan.adapter_id == LOCAL_AI_ADAPTER_ID:
            expected_parameters.add("local_ai_profile_id")
            profile_id = parameters.get("local_ai_profile_id")
            if (
                type(profile_id) is not str
                or profile_id
                not in {
                    GENERAL_CHAT_PROFILE_ID,
                    SOFTWARE_ENGINEERING_PROFILE_ID,
                }
                or not valid_model_id(parameters.get("model_id"))
            ):
                raise AIExecutionRejectedError(
                    "authorization_policy_violation"
                )
        if (
            step.operation != "ai.generate_text"
            or set(parameters) != expected_parameters
            or parameters.get("capability_id") != AI_CAPABILITY_TEXT_GENERATION
            or not isinstance(parameters.get("model_id"), str)
            or not parameters["model_id"]
            or parameters["model_id"] != parameters["model_id"].strip()
        ):
            raise AIExecutionRejectedError("authorization_policy_violation")

        try:
            digest = execution_plan_digest(plan)
        except (TypeError, ValueError) as error:
            raise AIExecutionRejectedError("invalid_plan_digest") from error
        if authorization.source_plan_digest != digest:
            raise AIExecutionRejectedError("authorization_plan_mismatch")

        adapter = self._registry.resolve_ai(plan.adapter_id)
        if adapter is None:
            raise AIExecutionRejectedError("ai_adapter_unavailable")
        return plan, adapter, digest

    def _try_meter_success(
        self,
        *,
        request_id: str,
        plan_digest: str,
        adapter_id: str,
        authorized_model_id: str,
        result: AIResult,
    ) -> None:
        if self._usage_meter is None:
            return
        try:
            self._usage_meter.try_record_success(
                request_id=request_id,
                plan_digest=plan_digest,
                adapter_id=adapter_id,
                authorized_model_id=authorized_model_id,
                result=result,
            )
        except Exception:
            # D155 is observability only. Metering must never turn a successful
            # provider execution into a failed AI/chat result.
            return

    def _record(
        self,
        *,
        request_id: str,
        action: str,
        status: str,
        adapter_id: str,
        reason_code: str,
        plan_digest: str,
    ) -> None:
        if self._audit is None:
            return
        self._audit.try_record(
            request_id=request_id,
            stage="execution",
            action=action,
            status=status,
            target_kind="ai",
            adapter_id=adapter_id,
            reason_code=reason_code,
            plan_digest=plan_digest,
        )
