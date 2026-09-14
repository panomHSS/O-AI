"""D46 deterministic explicit Chat -> Action bridge."""

from __future__ import annotations

from uuid import UUID

from app.contracts.chat_action import (
    ChatActionBridgeOutcome,
    ChatActionDirective,
)
from app.services.conversations import ConversationService
from app.services.execution_approval_service import (
    ExecutionApprovalError,
    ExecutionApprovalService,
)


ACTION_PREFIX = "/action"
PENDING_REPLY = "Action prepared for owner approval."
INVALID_REPLY = "The action directive could not be recognized."
UNAVAILABLE_REPLY = "The requested action is not currently available."
PROJECT_REQUIRED_REPLY = (
    "This action requires a Project-linked conversation."
)


_FIXED_DIRECTIVES: dict[str, ChatActionDirective] = {
    "system info": ChatActionDirective(
        target_kind="tool",
        adapter_id="tool.system.info",
        operation="get_info",
    ),
    "system health": ChatActionDirective(
        target_kind="tool",
        adapter_id="tool.system.health",
        operation="check",
    ),
    "workspace overview": ChatActionDirective(
        target_kind="module",
        adapter_id="module.workspace.overview",
        operation="inspect",
    ),
    "project snapshot": ChatActionDirective(
        target_kind="module",
        adapter_id="module.project.snapshot",
        operation="get_snapshot",
        requires_project_context=True,
    ),
}

_REMAINDER_DIRECTIVES: dict[
    str,
    tuple[str, str, str],
] = {
    "echo": ("tool", "tool.standard.echo", "echo"),
    "list": ("tool", "tool.filesystem.list", "list"),
    "stat": ("tool", "tool.filesystem.stat", "stat"),
    "read": (
        "tool",
        "tool.filesystem.read_text",
        "read_text",
    ),
}


class ChatActionBridge:
    """Convert only explicit /action syntax into D45 approval proposals."""

    def __init__(
        self,
        *,
        conversation_service: ConversationService,
        approval_service: ExecutionApprovalService,
    ) -> None:
        self._conversation_service = conversation_service
        self._approval_service = approval_service

    @staticmethod
    def is_action_directive(message: str) -> bool:
        if not isinstance(message, str):
            return False
        normalized = message.strip()
        if normalized == ACTION_PREFIX:
            return True
        if not normalized.startswith(ACTION_PREFIX):
            return False
        if len(normalized) <= len(ACTION_PREFIX):
            return False
        return normalized[len(ACTION_PREFIX)].isspace()

    def process(
        self,
        *,
        message: str,
        conversation_id: UUID | None = None,
        project_id: UUID | None = None,
    ) -> ChatActionBridgeOutcome:
        if not self.is_action_directive(message):
            raise ValueError(
                "ChatActionBridge only accepts explicit /action directives."
            )

        directive = self._parse(message)
        conversation, _ = self._conversation_service.begin_turn(
            message,
            conversation_id,
            project_id,
        )
        conversation_uuid = UUID(str(conversation.id))

        if directive is None:
            return self._complete(
                conversation_id=str(conversation.id),
                conversation_uuid=conversation_uuid,
                reply=INVALID_REPLY,
                status="rejected",
                reason_code="invalid_action_directive",
            )

        parameters = dict(directive.parameters)
        if directive.requires_project_context:
            linked_project_id = getattr(
                conversation,
                "project_id",
                None,
            )
            if not linked_project_id:
                return self._complete(
                    conversation_id=str(conversation.id),
                    conversation_uuid=conversation_uuid,
                    reply=PROJECT_REQUIRED_REPLY,
                    status="rejected",
                    reason_code="project_context_required",
                )
            parameters = {
                "project_id": str(linked_project_id),
            }

        try:
            approval = self._approval_service.propose(
                target_kind=directive.target_kind,
                adapter_id=directive.adapter_id,
                operation=directive.operation,
                parameters=parameters,
            )
        except ExecutionApprovalError as error:
            return self._complete(
                conversation_id=str(conversation.id),
                conversation_uuid=conversation_uuid,
                reply=UNAVAILABLE_REPLY,
                status="unavailable",
                reason_code=getattr(
                    error,
                    "reason_code",
                    "approval_proposal_invalid",
                ),
            )

        if approval.status == "pending":
            return self._complete(
                conversation_id=str(conversation.id),
                conversation_uuid=conversation_uuid,
                reply=PENDING_REPLY,
                status="pending_approval",
                reason_code=approval.reason_code,
                approval=approval,
            )

        return self._complete(
            conversation_id=str(conversation.id),
            conversation_uuid=conversation_uuid,
            reply=UNAVAILABLE_REPLY,
            status=approval.status,
            reason_code=approval.reason_code,
        )

    def _complete(
        self,
        *,
        conversation_id: str,
        conversation_uuid: UUID,
        reply: str,
        status: str,
        reason_code: str,
        approval=None,
    ) -> ChatActionBridgeOutcome:
        self._conversation_service.complete_turn(
            conversation_id,
            reply,
        )
        return ChatActionBridgeOutcome(
            reply=reply,
            conversation_id=conversation_uuid,
            status=status,  # type: ignore[arg-type]
            reason_code=reason_code,
            approval=approval,
        )

    @staticmethod
    def _parse(message: str) -> ChatActionDirective | None:
        normalized = message.strip()
        payload = normalized[len(ACTION_PREFIX):].lstrip()

        fixed = _FIXED_DIRECTIVES.get(payload)
        if fixed is not None:
            return fixed

        for verb, (
            target_kind,
            adapter_id,
            operation,
        ) in _REMAINDER_DIRECTIVES.items():
            prefix = f"{verb} "
            if not payload.startswith(prefix):
                continue
            remainder = payload[len(prefix):].lstrip()
            if not remainder:
                return None
            parameter_name = (
                "value" if verb == "echo" else "path"
            )
            return ChatActionDirective(
                target_kind=target_kind,  # type: ignore[arg-type]
                adapter_id=adapter_id,
                operation=operation,
                parameters={parameter_name: remainder},
            )

        return None
