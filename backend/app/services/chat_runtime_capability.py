"""D81 deterministic owner-facing runtime capability status language.

This module classifies only a small allowlist of status/capability questions and
renders only facts already present in RuntimeDiagnosticsResponse.  It carries no
approval, authorization, connector, credential, automation, or AI authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias
from uuid import UUID

from app.schemas.diagnostics import RuntimeDiagnosticsResponse
from app.services.conversations import ConversationService
from app.services.runtime_diagnostics import RuntimeDiagnosticsService


RuntimeCapabilityStatusTarget: TypeAlias = Literal[
    "system",
    "calendar",
    "gmail",
    "automation",
]
RuntimeCapabilityStatusLanguage: TypeAlias = Literal["th", "en"]


@dataclass(frozen=True, slots=True)
class RuntimeCapabilityStatusIntent:
    target: RuntimeCapabilityStatusTarget
    language: RuntimeCapabilityStatusLanguage

    def __post_init__(self) -> None:
        if self.target not in {"system", "calendar", "gmail", "automation"}:
            raise ValueError("Unsupported runtime capability status target.")
        if self.language not in {"th", "en"}:
            raise ValueError("Unsupported runtime capability status language.")


_THAI_SYSTEM = frozenset(
    {
        "/status",
        "สถานะระบบ",
        "ระบบพร้อมไหม",
        "สถานะ o-ai",
        "ตอนนี้ o-ai ทำอะไรได้บ้าง",
        "o-ai รองรับอะไรบ้างตอนนี้",
    }
)
_THAI_CALENDAR = frozenset(
    {
        "สถานะ calendar",
        "สถานะ google calendar",
    }
)
_THAI_GMAIL = frozenset({"สถานะ gmail"})
_THAI_AUTOMATION = frozenset({"สถานะ automation"})

_ENGLISH_SYSTEM = frozenset(
    {
        "what is the system status",
        "what's the system status",
        "system status",
        "o-ai status",
        "what can o-ai do now",
    }
)
_ENGLISH_CALENDAR = frozenset(
    {
        "calendar status",
        "google calendar status",
    }
)
_ENGLISH_GMAIL = frozenset({"gmail status"})
_ENGLISH_AUTOMATION = frozenset({"automation status"})


class RuntimeCapabilityStatusIntentRouter:
    """Exact bounded classifier; never uses model inference."""

    @staticmethod
    def _normalized(message: object) -> str | None:
        if not isinstance(message, str):
            return None
        if not message.strip():
            return None
        return " ".join(message.strip().casefold().split())

    def classify(
        self,
        message: object,
    ) -> RuntimeCapabilityStatusIntent | None:
        normalized = self._normalized(message)
        if normalized is None:
            return None

        if normalized in _THAI_SYSTEM:
            return RuntimeCapabilityStatusIntent(target="system", language="th")
        if normalized in _THAI_CALENDAR:
            return RuntimeCapabilityStatusIntent(
                target="calendar",
                language="th",
            )
        if normalized in _THAI_GMAIL:
            return RuntimeCapabilityStatusIntent(target="gmail", language="th")
        if normalized in _THAI_AUTOMATION:
            return RuntimeCapabilityStatusIntent(
                target="automation",
                language="th",
            )

        if normalized in _ENGLISH_SYSTEM:
            return RuntimeCapabilityStatusIntent(target="system", language="en")
        if normalized in _ENGLISH_CALENDAR:
            return RuntimeCapabilityStatusIntent(
                target="calendar",
                language="en",
            )
        if normalized in _ENGLISH_GMAIL:
            return RuntimeCapabilityStatusIntent(target="gmail", language="en")
        if normalized in _ENGLISH_AUTOMATION:
            return RuntimeCapabilityStatusIntent(
                target="automation",
                language="en",
            )
        return None

    def is_request(self, message: object) -> bool:
        return self.classify(message) is not None


class RuntimeCapabilityResponseComposer:
    """Render one deterministic response from allowlisted snapshot facts only."""

    @staticmethod
    def _th_connection(status: str) -> str:
        labels = {
            "disabled": "ปิดใช้งาน",
            "not_configured": "ยังตั้งค่าไม่ครบ",
            "disconnected": "ยังไม่ได้เชื่อมต่อ",
            "connected": "connected",
            "reauthorization_required": "ต้องเชื่อมต่อ OAuth ใหม่",
            "unavailable": "ตรวจสอบสถานะไม่ได้",
        }
        return labels.get(status, "ตรวจสอบสถานะไม่ได้")

    @staticmethod
    def _en_connection(status: str) -> str:
        labels = {
            "disabled": "disabled",
            "not_configured": "not configured",
            "disconnected": "disconnected",
            "connected": "connected",
            "reauthorization_required": "OAuth reauthorization required",
            "unavailable": "status unavailable",
        }
        return labels.get(status, "status unavailable")

    @staticmethod
    def _th_ready(value: bool) -> str:
        return "พร้อม" if value else "ยังไม่พร้อม"

    @staticmethod
    def _en_ready(value: bool) -> str:
        return "ready" if value else "not ready"

    @staticmethod
    def _th_on(value: bool) -> str:
        return "เปิดใช้งาน" if value else "ปิดใช้งาน"

    @staticmethod
    def _en_on(value: bool) -> str:
        return "enabled" if value else "disabled"

    def compose(
        self,
        intent: RuntimeCapabilityStatusIntent,
        snapshot: RuntimeDiagnosticsResponse,
    ) -> str:
        if not isinstance(intent, RuntimeCapabilityStatusIntent):
            raise TypeError(
                "intent must be RuntimeCapabilityStatusIntent."
            )
        if not isinstance(snapshot, RuntimeDiagnosticsResponse):
            raise TypeError("snapshot must be RuntimeDiagnosticsResponse.")

        if intent.language == "th":
            return self._compose_th(intent.target, snapshot)
        return self._compose_en(intent.target, snapshot)

    def _compose_th(
        self,
        target: RuntimeCapabilityStatusTarget,
        snapshot: RuntimeDiagnosticsResponse,
    ) -> str:
        if target == "calendar":
            c = snapshot.google_calendar
            return "\n".join(
                (
                    "สถานะ Google Calendar ครับ",
                    f"- การเชื่อมต่อ: {self._th_connection(c.status)}",
                    f"- Read via Chat: {self._th_ready(c.read_chat_routable)}",
                    (
                        "- Write backend: "
                        + ("มี" if c.write_backend_implemented else "ไม่มี")
                    ),
                    (
                        "- Write via Chat: "
                        + (
                            "รองรับการสร้างนัด"
                            if c.write_chat_routable
                            else "ยังไม่รองรับ"
                        )
                    ),
                    "- Update/Delete via Chat: ยังไม่รองรับ",
                )
            )

        if target == "gmail":
            g = snapshot.gmail
            return "\n".join(
                (
                    "สถานะ Gmail ครับ",
                    f"- การเชื่อมต่อ: {self._th_connection(g.status)}",
                    f"- Read via Chat: {self._th_ready(g.read_chat_routable)}",
                    (
                        "- Write/Send backend: "
                        + ("รองรับ" if g.write_implemented else "ยังไม่รองรับ")
                    ),
                    (
                        "- Write/Send via Chat: "
                        + ("รองรับ" if g.write_chat_routable else "ยังไม่รองรับ")
                    ),
                )
            )

        if target == "automation":
            a = snapshot.automation
            return "\n".join(
                (
                    "สถานะ Automation ครับ",
                    f"- ระบบ Automation: {self._th_on(a.enabled)}",
                    (
                        "- Local reminder: "
                        + (
                            "มี implementation"
                            if a.local_reminder_implemented
                            else "ไม่มี implementation"
                        )
                    ),
                    (
                        "- Owner delivery UI: "
                        + (
                            "พร้อม"
                            if a.local_reminder_delivery_ui_implemented
                            else "ยังไม่พร้อม"
                        )
                    ),
                    (
                        "- Local reminder via Chat: "
                        + (
                            "รองรับ"
                            if a.local_reminder_chat_routable
                            else "ยังไม่รองรับ"
                        )
                    ),
                    (
                        "- Connector actions: "
                        + (
                            "รองรับ"
                            if a.connector_actions_implemented
                            else "ยังไม่รองรับ"
                        )
                    ),
                    (
                        "- AI actions: "
                        + (
                            "รองรับ"
                            if a.ai_actions_implemented
                            else "ยังไม่รองรับ"
                        )
                    ),
                )
            )

        c = snapshot.google_calendar
        g = snapshot.gmail
        x = snapshot.cross_connector_ai
        a = snapshot.automation
        return "\n".join(
            (
                "สถานะ O-AI ตอนนี้ครับ",
                f"- Service: {snapshot.service}",
                f"- Environment: {snapshot.environment}",
                f"- Database revision: {snapshot.database_revision}",
                f"- Execution audit: {snapshot.execution_audit.status}",
                "",
                "Calendar",
                f"- Connection: {self._th_connection(c.status)}",
                f"- Read via Chat: {self._th_ready(c.read_chat_routable)}",
                (
                    "- Write backend: "
                    + ("มี" if c.write_backend_implemented else "ไม่มี")
                ),
                (
                    "- Write via Chat: "
                    + (
                        "รองรับการสร้างนัด"
                        if c.write_chat_routable
                        else "ยังไม่รองรับ"
                    )
                ),
                "- Update/Delete via Chat: ยังไม่รองรับ",
                "",
                "Gmail",
                f"- Connection: {self._th_connection(g.status)}",
                f"- Read via Chat: {self._th_ready(g.read_chat_routable)}",
                (
                    "- Write/Send backend: "
                    + ("รองรับ" if g.write_implemented else "ยังไม่รองรับ")
                ),
                (
                    "- Write/Send via Chat: "
                    + ("รองรับ" if g.write_chat_routable else "ยังไม่รองรับ")
                ),
                "",
                "Cross-Connector AI",
                f"- Gmail + Calendar context: {self._th_on(x.enabled)}",
                "",
                "Automation",
                f"- Automation: {self._th_on(a.enabled)}",
                (
                    "- Local reminder: "
                    + (
                        "มี implementation"
                        if a.local_reminder_implemented
                        else "ไม่มี implementation"
                    )
                ),
                (
                    "- Owner delivery UI: "
                    + (
                        "พร้อม"
                        if a.local_reminder_delivery_ui_implemented
                        else "ยังไม่พร้อม"
                    )
                ),
                (
                    "- Connector execution: "
                    + (
                        "รองรับ"
                        if a.connector_actions_implemented
                        else "ยังไม่รองรับ"
                    )
                ),
            )
        )

    def _compose_en(
        self,
        target: RuntimeCapabilityStatusTarget,
        snapshot: RuntimeDiagnosticsResponse,
    ) -> str:
        if target == "calendar":
            c = snapshot.google_calendar
            return "\n".join(
                (
                    "Google Calendar status",
                    f"- Connection: {self._en_connection(c.status)}",
                    f"- Read via Chat: {self._en_ready(c.read_chat_routable)}",
                    (
                        "- Write backend: "
                        + ("implemented" if c.write_backend_implemented else "not implemented")
                    ),
                    (
                        "- Write via Chat: "
                        + (
                            "create event supported"
                            if c.write_chat_routable
                            else "not supported"
                        )
                    ),
                    "- Update/Delete via Chat: not supported",
                )
            )

        if target == "gmail":
            g = snapshot.gmail
            return "\n".join(
                (
                    "Gmail status",
                    f"- Connection: {self._en_connection(g.status)}",
                    f"- Read via Chat: {self._en_ready(g.read_chat_routable)}",
                    (
                        "- Write/Send backend: "
                        + ("implemented" if g.write_implemented else "not implemented")
                    ),
                    (
                        "- Write/Send via Chat: "
                        + ("supported" if g.write_chat_routable else "not supported")
                    ),
                )
            )

        if target == "automation":
            a = snapshot.automation
            return "\n".join(
                (
                    "Automation status",
                    f"- Automation: {self._en_on(a.enabled)}",
                    (
                        "- Local reminder: "
                        + (
                            "implemented"
                            if a.local_reminder_implemented
                            else "not implemented"
                        )
                    ),
                    (
                        "- Owner delivery UI: "
                        + (
                            "implemented"
                            if a.local_reminder_delivery_ui_implemented
                            else "not implemented"
                        )
                    ),
                    (
                        "- Local reminder via Chat: "
                        + (
                            "supported"
                            if a.local_reminder_chat_routable
                            else "not supported"
                        )
                    ),
                    (
                        "- Connector actions: "
                        + (
                            "supported"
                            if a.connector_actions_implemented
                            else "not supported"
                        )
                    ),
                    (
                        "- AI actions: "
                        + (
                            "supported"
                            if a.ai_actions_implemented
                            else "not supported"
                        )
                    ),
                )
            )

        c = snapshot.google_calendar
        g = snapshot.gmail
        x = snapshot.cross_connector_ai
        a = snapshot.automation
        return "\n".join(
            (
                "O-AI runtime status",
                f"- Service: {snapshot.service}",
                f"- Environment: {snapshot.environment}",
                f"- Database revision: {snapshot.database_revision}",
                f"- Execution audit: {snapshot.execution_audit.status}",
                "",
                "Calendar",
                f"- Connection: {self._en_connection(c.status)}",
                f"- Read via Chat: {self._en_ready(c.read_chat_routable)}",
                (
                    "- Write backend: "
                    + ("implemented" if c.write_backend_implemented else "not implemented")
                ),
                (
                    "- Write via Chat: "
                    + (
                        "create event supported"
                        if c.write_chat_routable
                        else "not supported"
                    )
                ),
                "- Update/Delete via Chat: not supported",
                "",
                "Gmail",
                f"- Connection: {self._en_connection(g.status)}",
                f"- Read via Chat: {self._en_ready(g.read_chat_routable)}",
                (
                    "- Write/Send backend: "
                    + ("implemented" if g.write_implemented else "not implemented")
                ),
                (
                    "- Write/Send via Chat: "
                    + ("supported" if g.write_chat_routable else "not supported")
                ),
                "",
                "Cross-Connector AI",
                f"- Gmail + Calendar context: {self._en_on(x.enabled)}",
                "",
                "Automation",
                f"- Automation: {self._en_on(a.enabled)}",
                (
                    "- Local reminder: "
                    + (
                        "implemented"
                        if a.local_reminder_implemented
                        else "not implemented"
                    )
                ),
                (
                    "- Owner delivery UI: "
                    + (
                        "implemented"
                        if a.local_reminder_delivery_ui_implemented
                        else "not implemented"
                    )
                ),
                (
                    "- Connector execution: "
                    + (
                        "supported"
                        if a.connector_actions_implemented
                        else "not supported"
                    )
                ),
            )
        )




@dataclass(frozen=True, slots=True)
class RuntimeCapabilityChatOutcome:
    conversation_id: UUID
    reply: str

    def __post_init__(self) -> None:
        if not isinstance(self.conversation_id, UUID):
            raise TypeError("conversation_id must be a UUID.")
        if not isinstance(self.reply, str) or not self.reply or self.reply != self.reply.strip():
            raise ValueError("reply must be a non-empty trimmed string.")


class RuntimeCapabilityChatService:
    """Persist one deterministic D81 status turn without invoking normal AI."""

    def __init__(
        self,
        *,
        conversation_service: ConversationService,
        diagnostics_service: RuntimeDiagnosticsService,
        intent_router: RuntimeCapabilityStatusIntentRouter | None = None,
        response_composer: RuntimeCapabilityResponseComposer | None = None,
    ) -> None:
        self._conversation_service = conversation_service
        self._diagnostics_service = diagnostics_service
        self._intent_router = intent_router or RuntimeCapabilityStatusIntentRouter()
        self._response_composer = (
            response_composer or RuntimeCapabilityResponseComposer()
        )

    def is_request(self, message: object) -> bool:
        return self._intent_router.is_request(message)

    def process(
        self,
        *,
        message: str,
        conversation_id: UUID | None,
        project_id: UUID | None,
        database_revision: str,
    ) -> RuntimeCapabilityChatOutcome:
        intent = self._intent_router.classify(message)
        if intent is None:
            raise ValueError("runtime_capability_status_intent_required")
        if (
            not isinstance(database_revision, str)
            or not database_revision
            or database_revision != database_revision.strip()
        ):
            raise ValueError(
                "database_revision must be a non-empty trimmed string."
            )

        snapshot = self._diagnostics_service.snapshot(
            database_revision=database_revision
        )
        reply = self._response_composer.compose(intent, snapshot)

        conversation, _ = self._conversation_service.begin_turn(
            message,
            conversation_id,
            project_id,
        )
        conversation_uuid = UUID(str(conversation.id))
        self._conversation_service.complete_turn(
            str(conversation.id),
            reply,
        )
        return RuntimeCapabilityChatOutcome(
            conversation_id=conversation_uuid,
            reply=reply,
        )

__all__ = [
    "RuntimeCapabilityChatOutcome",
    "RuntimeCapabilityChatService",
    "RuntimeCapabilityResponseComposer",
    "RuntimeCapabilityStatusIntent",
    "RuntimeCapabilityStatusIntentRouter",
    "RuntimeCapabilityStatusLanguage",
    "RuntimeCapabilityStatusTarget",
]
