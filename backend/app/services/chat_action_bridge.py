"""D46 deterministic explicit Chat -> Action bridge, extended by D61."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from app.contracts.chat_action import (
    ChatActionBridgeOutcome,
    ChatActionDirective,
)
from app.contracts.chat_plugin_action import (
    CalendarChatWindow,
    ChatPluginActionBinding,
)
from app.contracts.gmail import (
    GMAIL_ADAPTER_ID,
    GMAIL_OPERATION,
    GmailReadQuery,
)
from app.services.chat_calendar import (
    GOOGLE_CALENDAR_CHAT_ADAPTER_ID,
    GOOGLE_CALENDAR_CHAT_OPERATION,
    GOOGLE_CALENDAR_CHAT_TIME_MAX_PARAMETER,
    GOOGLE_CALENDAR_CHAT_TIME_MIN_PARAMETER,
    CalendarChatWindowResolver,
    CalendarSpecificDateParser,
)
from app.services.chat_calendar_clarification import (
    CalendarClarificationStore,
)
from app.services.chat_plugin_action import (
    GITHUB_PUBLIC_REPO_ADAPTER_ID,
    GITHUB_PUBLIC_REPO_OPERATION,
    ChatPluginActionBindingStore,
    ChatPluginIntentRouter,
)
from app.services.google_oauth_connection_status import (
    GoogleOAuthConnectionStatusReader,
)
from app.services.conversations import ConversationService
from app.services.execution_approval_service import (
    ExecutionApprovalError,
    ExecutionApprovalService,
)


ACTION_PREFIX = "/action"
_PLAINTEXT_APPROVAL_PHRASES = frozenset(
    {
        "อนุมัติ",
        "อนุมัติครับ",
        "อนุมัติค่ะ",
        "approve",
        "approved",
        "ตกลง",
    }
)
PENDING_REPLY = "Action prepared for owner approval."
PLUGIN_PENDING_REPLY = (
    "พบคำขอข้อมูลสดจาก GitHub และเตรียม Action "
    "สำหรับการอนุมัติของเจ้าของแล้วครับ"
)
PLUGIN_DISABLED_REPLY = (
    "GitHub public repository connector ยังไม่ได้เปิดใช้งานครับ"
)
PLUGIN_INVALID_REPLY = (
    "พบคำขอข้อมูล GitHub แต่ต้องระบุ repository "
    "แบบ owner/repository เพียงหนึ่งรายการครับ"
)
CALENDAR_PENDING_REPLY = (
    "พบคำขออ่าน Google Calendar และเตรียม Action "
    "สำหรับการอนุมัติของเจ้าของแล้วครับ"
)
CALENDAR_DISABLED_REPLY = "Google Calendar connector ยังไม่ได้เปิดใช้งานครับ"
CALENDAR_DISCONNECTED_REPLY = (
    "ยังไม่ได้เชื่อมต่อ Google Calendar ผ่าน OAuth ครับ"
)
CALENDAR_REAUTH_REPLY = (
    "Google Calendar ต้องเชื่อมต่อ OAuth ใหม่ก่อนใช้งานครับ"
)
CALENDAR_INVALID_REPLY = (
    "คำขอ Google Calendar นี้ยังไม่อยู่ในช่วงเวลาที่รองรับ "
    "(วันนี้/พรุ่งนี้และช่วงเช้า-บ่าย-เย็น, 7 วันข้างหน้า, "
    "สัปดาห์นี้, สัปดาห์หน้า, เดือนนี้ หรือสุดสัปดาห์) ครับ"
)
CALENDAR_STATUS_UNAVAILABLE_REPLY = (
    "ไม่สามารถตรวจสถานะการเชื่อมต่อ Google Calendar ได้ในครั้งนี้ครับ"
)
GMAIL_PENDING_REPLY = (
    "พบคำขออ่าน Gmail และเตรียม Action "
    "สำหรับการอนุมัติของเจ้าของแล้วครับ"
)
GMAIL_DISABLED_REPLY = "Gmail connector ยังไม่ได้เปิดใช้งานครับ"
GMAIL_INVALID_REPLY = (
    "คำขอ Gmail นี้รองรับเฉพาะอีเมลล่าสุด, อีเมลที่ยังไม่ได้อ่าน "
    "หรืออีเมลจากผู้ส่งหนึ่งรายครับ"
)
GMAIL_STRUCTURED_APPROVAL_REQUIRED_REPLY = (
    "คำว่าอนุมัติในข้อความแชตยังไม่ใช่การอนุมัติ Action อ่าน Gmail ครับ "
    "กรุณาใช้การอนุมัติแบบ structured ของ Action ที่รออยู่"
)
CALENDAR_TIMEZONE_UNAVAILABLE_REPLY = (
    "ไม่สามารถตีความช่วงเวลา Calendar ตาม timezone ของเจ้าของได้ครับ"
)
CALENDAR_DATE_CONFIRMATION_REPLY = "หมายถึงวันที่ {date_value} ใช่ไหมครับ"
CALENDAR_DATE_INVALID_REPLY = "วันที่ในคำขอ Google Calendar ไม่ถูกต้องหรือไม่รองรับครับ"
CALENDAR_DATE_CANCELLED_REPLY = "ยกเลิกการยืนยันวันที่สำหรับคำขออ่าน Google Calendar แล้วครับ"
CALENDAR_DATE_EXPIRED_REPLY = (
    "การยืนยันวันที่ Google Calendar หมดเวลาแล้ว "
    "กรุณาส่งคำขอวันที่อีกครั้งครับ"
)
CALENDAR_CLARIFICATION_UNAVAILABLE_REPLY = "ไม่สามารถเก็บสถานะยืนยันวันที่ Calendar ได้ในครั้งนี้ครับ"
CALENDAR_STRUCTURED_APPROVAL_REQUIRED_REPLY = (
    "คำว่าอนุมัติในข้อความแชตยังไม่ใช่การอนุมัติ Action ครับ "
    "กรุณาใช้การอนุมัติแบบ structured ของ Action ที่รออยู่"
)
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
    """Convert deterministic Chat action syntax/intents into D45 proposals."""

    def __init__(
        self,
        *,
        conversation_service: ConversationService,
        approval_service: ExecutionApprovalService,
        plugin_binding_store: ChatPluginActionBindingStore | None = None,
        plugin_intent_router: ChatPluginIntentRouter | None = None,
        github_public_repo_connector_enabled: bool = False,
        google_calendar_connector_enabled: bool = False,
        gmail_connector_enabled: bool = False,
        google_calendar_connection_status_reader: (
            GoogleOAuthConnectionStatusReader | None
        ) = None,
        owner_timezone: str = "Asia/Bangkok",
        calendar_window_resolver: CalendarChatWindowResolver | None = None,
        calendar_specific_date_parser: CalendarSpecificDateParser | None = None,
        calendar_clarification_store: CalendarClarificationStore | None = None,
    ) -> None:
        if type(github_public_repo_connector_enabled) is not bool:
            raise TypeError(
                "github_public_repo_connector_enabled must be an exact bool."
            )
        if type(google_calendar_connector_enabled) is not bool:
            raise TypeError(
                "google_calendar_connector_enabled must be an exact bool."
            )
        if type(gmail_connector_enabled) is not bool:
            raise TypeError("gmail_connector_enabled must be an exact bool.")
        self._conversation_service = conversation_service
        self._approval_service = approval_service
        self._plugin_binding_store = (
            plugin_binding_store or ChatPluginActionBindingStore()
        )
        self._plugin_intent_router = (
            plugin_intent_router or ChatPluginIntentRouter()
        )
        self._github_public_repo_connector_enabled = (
            github_public_repo_connector_enabled
        )
        self._google_calendar_connector_enabled = (
            google_calendar_connector_enabled
        )
        self._gmail_connector_enabled = gmail_connector_enabled
        self._google_calendar_connection_status_reader = (
            google_calendar_connection_status_reader
        )
        self._calendar_window_resolver = (
            calendar_window_resolver
            or CalendarChatWindowResolver(owner_timezone)
        )
        self._calendar_specific_date_parser = (
            calendar_specific_date_parser
            or CalendarSpecificDateParser(owner_timezone)
        )
        self._calendar_clarification_store = (
            calendar_clarification_store or CalendarClarificationStore()
        )

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

    def is_plugin_action_request(self, message: str) -> bool:
        if self._calendar_specific_date_parser.parse(message).status != "none":
            return True
        return self._plugin_intent_router.classify(message).status != "none"

    def calendar_clarification_disposition(
        self,
        conversation_id: UUID | None,
        message: object,
    ) -> str:
        status = self._calendar_clarification_store.classify(
            conversation_id, message
        )
        if status in {"positive", "negative", "expired"}:
            return "handle"
        if status == "unrelated":
            return "clear"
        return "none"

    def clear_calendar_clarification(
        self, conversation_id: UUID | None
    ) -> bool:
        return self._calendar_clarification_store.clear(conversation_id)

    def process_calendar_clarification(
        self,
        *,
        message: str,
        conversation_id: UUID,
        project_id: UUID | None = None,
    ) -> ChatActionBridgeOutcome:
        resolution = self._calendar_clarification_store.consume_response(
            conversation_id, message
        )
        if resolution.status not in {"positive", "negative", "expired"}:
            raise ValueError(
                "No matching Calendar clarification response is pending."
            )
        conversation, _ = self._conversation_service.begin_turn(
            message, conversation_id, project_id
        )
        conversation_uuid = UUID(str(conversation.id))
        if resolution.status == "negative":
            return self._complete(
                conversation_id=str(conversation.id),
                conversation_uuid=conversation_uuid,
                reply=CALENDAR_DATE_CANCELLED_REPLY,
                status="rejected",
                reason_code="calendar_specific_date_cancelled",
            )
        if resolution.status == "expired":
            return self._complete(
                conversation_id=str(conversation.id),
                conversation_uuid=conversation_uuid,
                reply=CALENDAR_DATE_EXPIRED_REPLY,
                status="rejected",
                reason_code="calendar_specific_date_confirmation_expired",
            )
        assert resolution.candidate_date is not None
        return self._process_google_calendar_plugin(
            conversation_id=str(conversation.id),
            conversation_uuid=conversation_uuid,
            calendar_window="exact_date",
            calendar_date=resolution.candidate_date,
        )

    @staticmethod
    def _normalized_plaintext_approval(message: object) -> str:
        if not isinstance(message, str):
            return ""
        return " ".join(message.strip().casefold().split())

    def is_pending_calendar_plaintext_approval(
        self,
        conversation_id: UUID | None,
        message: object,
    ) -> bool:
        if not isinstance(conversation_id, UUID):
            return False
        normalized = self._normalized_plaintext_approval(message)
        if normalized not in _PLAINTEXT_APPROVAL_PHRASES:
            return False
        return self._plugin_binding_store.has_pending_calendar_binding(
            conversation_id
        )

    def process_pending_calendar_plaintext_approval(
        self,
        *,
        message: str,
        conversation_id: UUID,
        project_id: UUID | None = None,
    ) -> ChatActionBridgeOutcome:
        if not self.is_pending_calendar_plaintext_approval(
            conversation_id,
            message,
        ):
            raise ValueError(
                "No pending Calendar structured approval guard matched."
            )
        conversation, _ = self._conversation_service.begin_turn(
            message,
            conversation_id,
            project_id,
        )
        conversation_uuid = UUID(str(conversation.id))
        return self._complete(
            conversation_id=str(conversation.id),
            conversation_uuid=conversation_uuid,
            reply=CALENDAR_STRUCTURED_APPROVAL_REQUIRED_REPLY,
            status="rejected",
            reason_code="calendar_approval_requires_structured_action",
        )

    def is_pending_gmail_plaintext_approval(
        self,
        conversation_id: UUID | None,
        message: object,
    ) -> bool:
        if not isinstance(conversation_id, UUID):
            return False
        normalized = self._normalized_plaintext_approval(message)
        if normalized not in _PLAINTEXT_APPROVAL_PHRASES:
            return False
        return self._plugin_binding_store.has_pending_gmail_binding(
            conversation_id
        )

    def process_pending_gmail_plaintext_approval(
        self,
        *,
        message: str,
        conversation_id: UUID,
        project_id: UUID | None = None,
    ) -> ChatActionBridgeOutcome:
        if not self.is_pending_gmail_plaintext_approval(
            conversation_id,
            message,
        ):
            raise ValueError(
                "No pending Gmail structured approval guard matched."
            )
        conversation, _ = self._conversation_service.begin_turn(
            message,
            conversation_id,
            project_id,
        )
        conversation_uuid = UUID(str(conversation.id))
        return self._complete(
            conversation_id=str(conversation.id),
            conversation_uuid=conversation_uuid,
            reply=GMAIL_STRUCTURED_APPROVAL_REQUIRED_REPLY,
            status="rejected",
            reason_code="gmail_approval_requires_structured_action",
        )

    def process(
        self,
        *,
        message: str,
        conversation_id: UUID | None = None,
        project_id: UUID | None = None,
    ) -> ChatActionBridgeOutcome:
        explicit = self.is_action_directive(message)
        plugin_intent = (
            None
            if explicit
            else self._plugin_intent_router.classify(message)
        )
        specific_date = (
            None
            if explicit
            else self._calendar_specific_date_parser.parse(message)
        )
        if not explicit and (
            plugin_intent is None
            or specific_date is None
            or (
                plugin_intent.status == "none"
                and specific_date.status == "none"
            )
        ):
            raise ValueError(
                "ChatActionBridge accepts only deterministic action requests."
            )

        conversation, _ = self._conversation_service.begin_turn(
            message,
            conversation_id,
            project_id,
        )
        conversation_uuid = UUID(str(conversation.id))

        if not explicit:
            assert plugin_intent is not None
            if plugin_intent.status == "invalid":
                if plugin_intent.calendar_intent:
                    return self._complete(
                        conversation_id=str(conversation.id),
                        conversation_uuid=conversation_uuid,
                        reply=CALENDAR_INVALID_REPLY,
                        status="rejected",
                        reason_code="invalid_google_calendar_intent",
                    )
                if self._plugin_intent_router.is_gmail_request(message):
                    return self._complete(
                        conversation_id=str(conversation.id),
                        conversation_uuid=conversation_uuid,
                        reply=GMAIL_INVALID_REPLY,
                        status="rejected",
                        reason_code="invalid_gmail_intent",
                    )
                return self._complete(
                    conversation_id=str(conversation.id),
                    conversation_uuid=conversation_uuid,
                    reply=PLUGIN_INVALID_REPLY,
                    status="rejected",
                    reason_code="invalid_github_repository_intent",
                )

            assert specific_date is not None
            if specific_date.status == "invalid":
                return self._complete(
                    conversation_id=str(conversation.id),
                    conversation_uuid=conversation_uuid,
                    reply=CALENDAR_DATE_INVALID_REPLY,
                    status="rejected",
                    reason_code=(specific_date.reason_code or "calendar_specific_date_invalid"),
                )
            if specific_date.status == "needs_confirmation":
                assert specific_date.date is not None
                try:
                    self._calendar_clarification_store.add(
                        conversation_uuid, specific_date.date
                    )
                except RuntimeError:
                    return self._complete(
                        conversation_id=str(conversation.id),
                        conversation_uuid=conversation_uuid,
                        reply=CALENDAR_CLARIFICATION_UNAVAILABLE_REPLY,
                        status="unavailable",
                        reason_code="calendar_clarification_store_full",
                    )
                return self._complete(
                    conversation_id=str(conversation.id),
                    conversation_uuid=conversation_uuid,
                    reply=CALENDAR_DATE_CONFIRMATION_REPLY.format(
                        date_value=specific_date.date.strftime("%d/%m/%Y")
                    ),
                    status="rejected",
                    reason_code="calendar_specific_date_confirmation_required",
                )
            if specific_date.status == "exact":
                assert specific_date.date is not None
                return self._process_google_calendar_plugin(
                    conversation_id=str(conversation.id),
                    conversation_uuid=conversation_uuid,
                    calendar_window="exact_date",
                    calendar_date=specific_date.date,
                )

            if plugin_intent.gmail_query is not None:
                if not self._gmail_connector_enabled:
                    return self._complete(
                        conversation_id=str(conversation.id),
                        conversation_uuid=conversation_uuid,
                        reply=GMAIL_DISABLED_REPLY,
                        status="unavailable",
                        reason_code="gmail_connector_disabled",
                    )
                return self._process_gmail_plugin(
                    conversation_id=str(conversation.id),
                    conversation_uuid=conversation_uuid,
                    gmail_query=plugin_intent.gmail_query,
                )

            if plugin_intent.calendar_intent:
                assert plugin_intent.calendar_window is not None
                return self._process_google_calendar_plugin(
                    conversation_id=str(conversation.id),
                    conversation_uuid=conversation_uuid,
                    calendar_window=plugin_intent.calendar_window,
                    calendar_date=plugin_intent.calendar_date,
                )

            if not self._github_public_repo_connector_enabled:
                return self._complete(
                    conversation_id=str(conversation.id),
                    conversation_uuid=conversation_uuid,
                    reply=PLUGIN_DISABLED_REPLY,
                    status="unavailable",
                    reason_code=(
                        "github_public_repo_connector_disabled"
                    ),
                )
            assert plugin_intent.repository_reference is not None
            return self._process_github_plugin(
                conversation_id=str(conversation.id),
                conversation_uuid=conversation_uuid,
                repository_reference=(
                    plugin_intent.repository_reference
                ),
            )

        directive = self._parse(message)
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

        return self._propose(
            conversation_id=str(conversation.id),
            conversation_uuid=conversation_uuid,
            target_kind=directive.target_kind,
            adapter_id=directive.adapter_id,
            operation=directive.operation,
            parameters=parameters,
            pending_reply=PENDING_REPLY,
        )

    def _process_github_plugin(
        self,
        *,
        conversation_id: str,
        conversation_uuid: UUID,
        repository_reference: str,
    ) -> ChatActionBridgeOutcome:
        outcome = self._propose(
            conversation_id=conversation_id,
            conversation_uuid=conversation_uuid,
            target_kind="module",
            adapter_id=GITHUB_PUBLIC_REPO_ADAPTER_ID,
            operation=GITHUB_PUBLIC_REPO_OPERATION,
            parameters={"content": repository_reference},
            pending_reply=PLUGIN_PENDING_REPLY,
            complete_pending=False,
        )
        if (
            outcome.status == "pending_approval"
            and outcome.approval is not None
            and outcome.approval.proposal is not None
        ):
            proposal = outcome.approval.proposal
            self._plugin_binding_store.add(
                ChatPluginActionBinding(
                    approval_id=proposal.approval_id,
                    conversation_id=conversation_uuid,
                    repository_reference=repository_reference,
                    expires_at=proposal.expires_at,
                )
            )
            self._conversation_service.complete_turn(
                conversation_id,
                PLUGIN_PENDING_REPLY,
            )
        return outcome

    def _process_gmail_plugin(
        self,
        *,
        conversation_id: str,
        conversation_uuid: UUID,
        gmail_query: GmailReadQuery,
    ) -> ChatActionBridgeOutcome:
        outcome = self._propose(
            conversation_id=conversation_id,
            conversation_uuid=conversation_uuid,
            target_kind="module",
            adapter_id=GMAIL_ADAPTER_ID,
            operation=GMAIL_OPERATION,
            parameters=gmail_query.to_parameters(),
            pending_reply=GMAIL_PENDING_REPLY,
            complete_pending=False,
        )
        if (
            outcome.status == "pending_approval"
            and outcome.approval is not None
            and outcome.approval.proposal is not None
        ):
            proposal = outcome.approval.proposal
            self._plugin_binding_store.add(
                ChatPluginActionBinding(
                    approval_id=proposal.approval_id,
                    conversation_id=conversation_uuid,
                    repository_reference=None,
                    expires_at=proposal.expires_at,
                    gmail_query=gmail_query,
                )
            )
            self._conversation_service.complete_turn(
                conversation_id,
                GMAIL_PENDING_REPLY,
            )
        return outcome

    def _process_google_calendar_plugin(
        self,
        *,
        conversation_id: str,
        conversation_uuid: UUID,
        calendar_window: CalendarChatWindow,
        calendar_date: date | None = None,
    ) -> ChatActionBridgeOutcome:
        if not self._google_calendar_connector_enabled:
            return self._complete(
                conversation_id=conversation_id,
                conversation_uuid=conversation_uuid,
                reply=CALENDAR_DISABLED_REPLY,
                status="unavailable",
                reason_code="google_calendar_connector_disabled",
            )

        reader = self._google_calendar_connection_status_reader
        if reader is None:
            return self._complete(
                conversation_id=conversation_id,
                conversation_uuid=conversation_uuid,
                reply=CALENDAR_DISCONNECTED_REPLY,
                status="unavailable",
                reason_code="google_calendar_not_connected",
            )
        try:
            connection_status = reader.read_status()
        except Exception:
            return self._complete(
                conversation_id=conversation_id,
                conversation_uuid=conversation_uuid,
                reply=CALENDAR_STATUS_UNAVAILABLE_REPLY,
                status="unavailable",
                reason_code="google_calendar_connection_status_unavailable",
            )

        if connection_status == "disconnected":
            return self._complete(
                conversation_id=conversation_id,
                conversation_uuid=conversation_uuid,
                reply=CALENDAR_DISCONNECTED_REPLY,
                status="unavailable",
                reason_code="google_calendar_not_connected",
            )
        if connection_status != "active":
            return self._complete(
                conversation_id=conversation_id,
                conversation_uuid=conversation_uuid,
                reply=CALENDAR_REAUTH_REPLY,
                status="unavailable",
                reason_code="google_calendar_reauthorization_required",
            )

        try:
            if calendar_window == "exact_date":
                if type(calendar_date) is not date:
                    raise ValueError("exact_date requires one Gregorian date.")
                snapshot = self._calendar_window_resolver.snapshot_exact_date(
                    calendar_date
                )
            else:
                if calendar_date is not None:
                    raise ValueError(
                        "relative Calendar window cannot carry calendar_date."
                    )
                snapshot = self._calendar_window_resolver.snapshot(
                    calendar_window
                )
        except Exception:
            return self._complete(
                conversation_id=conversation_id,
                conversation_uuid=conversation_uuid,
                reply=CALENDAR_TIMEZONE_UNAVAILABLE_REPLY,
                status="unavailable",
                reason_code="google_calendar_owner_timezone_invalid",
            )

        outcome = self._propose(
            conversation_id=conversation_id,
            conversation_uuid=conversation_uuid,
            target_kind="module",
            adapter_id=GOOGLE_CALENDAR_CHAT_ADAPTER_ID,
            operation=GOOGLE_CALENDAR_CHAT_OPERATION,
            parameters={
                GOOGLE_CALENDAR_CHAT_TIME_MIN_PARAMETER: snapshot.start.isoformat(
                    timespec="seconds"
                ),
                GOOGLE_CALENDAR_CHAT_TIME_MAX_PARAMETER: snapshot.end.isoformat(
                    timespec="seconds"
                ),
            },
            pending_reply=CALENDAR_PENDING_REPLY,
            complete_pending=False,
        )
        if (
            outcome.status == "pending_approval"
            and outcome.approval is not None
            and outcome.approval.proposal is not None
        ):
            proposal = outcome.approval.proposal
            self._plugin_binding_store.add(
                ChatPluginActionBinding(
                    approval_id=proposal.approval_id,
                    conversation_id=conversation_uuid,
                    repository_reference=None,
                    expires_at=proposal.expires_at,
                    calendar_window=snapshot.window,
                    calendar_date=calendar_date,
                    calendar_window_start=snapshot.start,
                    calendar_window_end=snapshot.end,
                )
            )
            self._conversation_service.complete_turn(
                conversation_id,
                CALENDAR_PENDING_REPLY,
            )
        return outcome

    def _propose(
        self,
        *,
        conversation_id: str,
        conversation_uuid: UUID,
        target_kind: str,
        adapter_id: str,
        operation: str,
        parameters: dict[str, object],
        pending_reply: str,
        complete_pending: bool = True,
    ) -> ChatActionBridgeOutcome:
        try:
            approval = self._approval_service.propose(
                target_kind=target_kind,
                adapter_id=adapter_id,
                operation=operation,
                parameters=parameters,
            )
        except ExecutionApprovalError as error:
            return self._complete(
                conversation_id=conversation_id,
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
            if complete_pending:
                self._conversation_service.complete_turn(
                    conversation_id,
                    pending_reply,
                )
            return ChatActionBridgeOutcome(
                reply=pending_reply,
                conversation_id=conversation_uuid,
                status="pending_approval",
                reason_code=approval.reason_code,
                approval=approval,
            )

        return self._complete(
            conversation_id=conversation_id,
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
