"""D45 API schemas for explicit one-time owner execution approval."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.execution_approval import (
    ExecutionApprovalDecisionOutcome,
    ExecutionApprovalProposalOutcome,
)
from app.contracts.chat_plugin_action import ChatPluginActionCompletion


class CreateExecutionApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_kind: Literal["tool", "module"]
    adapter_id: str = Field(min_length=1, max_length=128)
    operation: str = Field(min_length=1, max_length=128)
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        max_length=64,
    )


class ExecutionApprovalDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_digest: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )


class ExecutionCapabilityResponse(BaseModel):
    capability_id: str
    effect: str
    data_class: str


class ExecutionApprovalProposalResponse(BaseModel):
    status: Literal["pending", "rejected", "unavailable"]
    request_id: str
    target_kind: Literal["tool", "module"]
    reason_code: str
    approval_id: str | None = None
    adapter_id: str | None = None
    operation: str | None = None
    parameters: dict[str, Any] | None = None
    capability: ExecutionCapabilityResponse | None = None
    owner_approval_required: bool | None = None
    plan_digest: str | None = None
    expires_at: datetime | None = None

    @classmethod
    def from_outcome(
        cls,
        outcome: ExecutionApprovalProposalOutcome,
    ) -> "ExecutionApprovalProposalResponse":
        proposal = outcome.proposal
        if proposal is None:
            return cls(
                status=outcome.status,
                request_id=outcome.request_id,
                target_kind=outcome.target_kind,
                reason_code=outcome.reason_code,
            )
        return cls(
            status=outcome.status,
            request_id=outcome.request_id,
            target_kind=outcome.target_kind,
            reason_code=outcome.reason_code,
            approval_id=proposal.approval_id,
            adapter_id=proposal.adapter_id,
            operation=proposal.operation,
            parameters=dict(proposal.parameters),
            capability=ExecutionCapabilityResponse(
                capability_id=proposal.capability_id,
                effect=proposal.effect,
                data_class=proposal.data_class,
            ),
            owner_approval_required=(
                proposal.owner_approval_required
            ),
            plan_digest=proposal.plan_digest,
            expires_at=proposal.expires_at,
        )


class ExecutionResultResponse(BaseModel):
    status: Literal["succeeded", "failed", "blocked"]
    output: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None


class GmailReadDisplayMessageResponse(BaseModel):
    sender: str
    subject: str
    received_at: str
    unread: bool
    snippet: str
    body: str


class GmailReadDisplayResponse(BaseModel):
    messages: list[GmailReadDisplayMessageResponse]


class ExecutionChatCompletionResponse(BaseModel):
    conversation_id: UUID
    reply: str
    gmail_read: GmailReadDisplayResponse | None = None

    @classmethod
    def from_completion(
        cls,
        completion: ChatPluginActionCompletion,
    ) -> "ExecutionChatCompletionResponse":
        gmail_read = None
        if completion.gmail_read is not None:
            gmail_read = GmailReadDisplayResponse(
                messages=[
                    GmailReadDisplayMessageResponse(
                        sender=message.sender,
                        subject=message.subject,
                        received_at=message.received_at,
                        unread=message.unread,
                        snippet=message.snippet,
                        body=message.body,
                    )
                    for message in completion.gmail_read
                ]
            )
        return cls(
            conversation_id=completion.conversation_id,
            reply=completion.reply,
            gmail_read=gmail_read,
        )


class ExecutionApprovalDecisionResponse(BaseModel):
    approval_id: str
    request_id: str
    decision: Literal["approved", "denied"]
    status: Literal[
        "completed",
        "blocked",
        "rejected",
        "unavailable",
    ]
    target_kind: Literal["tool", "module"] | None
    reason_code: str
    result: ExecutionResultResponse | None = None
    chat_completion: ExecutionChatCompletionResponse | None = None

    @classmethod
    def from_outcome(
        cls,
        outcome: ExecutionApprovalDecisionOutcome,
        *,
        chat_completion: ChatPluginActionCompletion | None = None,
    ) -> "ExecutionApprovalDecisionResponse":
        execution = outcome.execution
        result = execution.result
        public_result = None
        if result is not None:
            public_result = ExecutionResultResponse(
                status=result.status,
                output=dict(result.output),
                error_code=(
                    "execution_failed"
                    if result.error is not None
                    else None
                ),
            )
        return cls(
            approval_id=outcome.approval_id,
            request_id=execution.request_id,
            decision=outcome.decision,
            status=execution.status,
            target_kind=execution.target_kind,
            reason_code=execution.reason_code,
            result=public_result,
            chat_completion=(
                ExecutionChatCompletionResponse.from_completion(
                    chat_completion
                )
                if chat_completion is not None
                else None
            ),
        )
