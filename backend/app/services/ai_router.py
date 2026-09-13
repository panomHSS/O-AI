"""Deterministic D24 router that selects, but never invokes, AI adapters."""

from collections.abc import Collection

from app.contracts.ai_route import (
    CHATGPT_DEFAULT_ADAPTER_ID,
    LOCAL_AI_ADAPTER_ID,
    AIRouteDecision,
)
from app.contracts.command_decision import CommandDecision


class AIRouter:
    """Select a future AI route from a D23 command decision only."""

    def __init__(
        self,
        *,
        default_adapter_id: str = CHATGPT_DEFAULT_ADAPTER_ID,
        local_ai_adapter_id: str = LOCAL_AI_ADAPTER_ID,
        available_adapter_ids: Collection[str] = (CHATGPT_DEFAULT_ADAPTER_ID,),
    ) -> None:
        self._default_adapter_id = default_adapter_id
        self._local_ai_adapter_id = local_ai_adapter_id
        self._available_adapter_ids = frozenset(available_adapter_ids)

    def route(self, decision: CommandDecision) -> AIRouteDecision:
        """Return a fail-closed route decision without adapter invocation."""
        if not self._is_supported_decision(decision):
            return AIRouteDecision(
                request_id=getattr(decision, "request_id", ""),
                status="rejected",
                adapter_id=None,
                selection_source=None,
                reason_code="invalid_command_decision",
            )

        if decision.disposition == "reject":
            return AIRouteDecision(
                request_id=decision.request_id,
                status="rejected",
                adapter_id=None,
                selection_source=None,
                reason_code="command_rejected",
            )

        if decision.provider_preference_hint == "local_ai_explicit":
            if self._local_ai_adapter_id not in self._available_adapter_ids:
                return AIRouteDecision(
                    request_id=decision.request_id,
                    status="unavailable",
                    adapter_id=self._local_ai_adapter_id,
                    selection_source=None,
                    reason_code="local_ai_unavailable",
                )
            return AIRouteDecision(
                request_id=decision.request_id,
                status="selected",
                adapter_id=self._local_ai_adapter_id,
                selection_source="explicit",
                reason_code="local_ai_explicit",
            )

        selection_source = (
            "automatic"
            if decision.provider_preference_hint == "automatic"
            else "default"
        )
        if self._default_adapter_id not in self._available_adapter_ids:
            return AIRouteDecision(
                request_id=decision.request_id,
                status="unavailable",
                adapter_id=self._default_adapter_id,
                selection_source=None,
                reason_code="default_adapter_unavailable",
            )
        return AIRouteDecision(
            request_id=decision.request_id,
            status="selected",
            adapter_id=self._default_adapter_id,
            selection_source=selection_source,
            reason_code="configured_default",
        )

    @staticmethod
    def _is_supported_decision(decision: object) -> bool:
        if not isinstance(decision, CommandDecision):
            return False
        if not decision.request_id:
            return False
        if decision.disposition == "reject":
            return decision.intent in {"chat_message", "unknown"}
        return (
            decision.intent == "chat_message"
            and decision.disposition == "defer_to_existing_chat"
            and decision.provider_preference_hint
            in {"unspecified", "automatic", "local_ai_explicit"}
        )
