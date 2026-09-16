"""D77 deterministic Gmail Chat intent and safe completion."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping

from app.connectors.gmail import (
    GMAIL_ERROR_AUTH_FAILED,
    GMAIL_ERROR_MESSAGE_NOT_FOUND,
    GMAIL_ERROR_QUERY_INVALID,
    GMAIL_ERROR_RATE_LIMITED,
    GMAIL_ERROR_RESPONSE_INVALID,
    GMAIL_ERROR_RESPONSE_TOO_LARGE,
    GMAIL_ERROR_UNAVAILABLE,
    GMAIL_MAX_RESULT_BYTES,
)
from app.contracts.chat_plugin_action import (
    ChatPluginActionBinding,
    ChatPluginIntentOutcome,
)
from app.contracts.execution_approval import ExecutionApprovalDecisionOutcome
from app.contracts.gmail import (
    GMAIL_MAX_RESULTS,
    GmailMessage,
    GmailReadQuery,
    GmailReadResult,
)


_EMAIL_TOKEN_RE = re.compile(
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+"
)
_FROM_RE = re.compile(
    r"(?:อีเมลจาก|เมลจาก|emails?\s+from)\s+"
    r"([A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+)",
    re.IGNORECASE,
)

_RECENT_PHRASES = (
    "อีเมลล่าสุด",
    "เมลล่าสุด",
    "latest email",
    "latest emails",
    "recent email",
    "recent emails",
)
_UNREAD_PHRASES = (
    "อีเมลที่ยังไม่ได้อ่าน",
    "เมลยังไม่อ่าน",
    "unread email",
    "unread emails",
)
_UNSUPPORTED_PHRASES = (
    "attachment",
    "attachments",
    "ไฟล์แนบ",
    "thread",
    "threads",
    "history",
    "ประวัติ",
    "search email",
    "search emails",
    "ค้นหาอีเมล",
    "ค้นหาเมล",
    "label",
    "labels",
    "send email",
    "send mail",
    "ส่งอีเมล",
    "ส่งเมล",
    "reply",
    "ตอบกลับ",
    "delete",
    "ลบอีเมล",
    "archive",
    "mark as read",
    "mark as unread",
)


class GmailChatIntentRouter:
    """Recognize only the frozen D77 recent/unread/from Gmail intents."""

    @staticmethod
    def has_signal(message: object) -> bool:
        if not isinstance(message, str) or not message.strip():
            return False
        folded = message.casefold()
        return (
            "อีเมล" in folded
            or "เมล" in folded
            or re.search(r"\bgmail\b", folded) is not None
            or re.search(r"\bemails?\b", folded) is not None
        )

    def classify(self, message: object) -> ChatPluginIntentOutcome:
        if not self.has_signal(message):
            return ChatPluginIntentOutcome(status="none")
        assert isinstance(message, str)
        normalized = " ".join(message.strip().split())
        folded = normalized.casefold()

        if any(phrase in folded for phrase in _UNSUPPORTED_PHRASES):
            return ChatPluginIntentOutcome(status="invalid")

        from_matches = list(_FROM_RE.finditer(normalized))
        email_tokens = _EMAIL_TOKEN_RE.findall(normalized)
        recent = any(phrase in folded for phrase in _RECENT_PHRASES)
        unread = any(phrase in folded for phrase in _UNREAD_PHRASES)
        mode_count = int(bool(from_matches)) + int(recent) + int(unread)
        if mode_count != 1:
            return ChatPluginIntentOutcome(status="invalid")

        if from_matches:
            if len(from_matches) != 1 or len(email_tokens) != 1:
                return ChatPluginIntentOutcome(status="invalid")
            sender = from_matches[0].group(1)
            try:
                query = GmailReadQuery(mode="from", sender=sender)
            except ValueError:
                return ChatPluginIntentOutcome(status="invalid")
            return ChatPluginIntentOutcome(
                status="matched",
                gmail_query=query,
            )

        query = GmailReadQuery(mode="unread" if unread else "recent")
        return ChatPluginIntentOutcome(status="matched", gmail_query=query)


class GmailChatCompletionComposer:
    """Render normalized Gmail data as display-only text without an LLM."""

    HISTORY_SAFE_REPLY = (
        "Gmail result was displayed as untrusted external data; "
        "email content was not retained in AI conversation context."
    )

    DENIED_REPLY = "ยกเลิกการอ่าน Gmail ตามการตัดสินใจของเจ้าของแล้วครับ"
    FAILURE_REPLY = "ไม่สามารถอ่าน Gmail ได้ในครั้งนี้ครับ"
    EMPTY_REPLY = "ไม่พบอีเมลที่ตรงกับคำขอนี้ครับ"

    _ERROR_REPLIES = {
        GMAIL_ERROR_AUTH_FAILED: (
            "ไม่สามารถใช้สิทธิ์ Gmail ได้ กรุณาตรวจการเชื่อมต่อ OAuth ครับ"
        ),
        GMAIL_ERROR_UNAVAILABLE: "Gmail ไม่พร้อมใช้งานในครั้งนี้ครับ",
        GMAIL_ERROR_RATE_LIMITED: (
            "Gmail จำกัดการเรียกใช้งานชั่วคราว กรุณาลองใหม่ภายหลังครับ"
        ),
        GMAIL_ERROR_RESPONSE_INVALID: "ได้รับข้อมูล Gmail ที่ไม่ถูกต้องครับ",
        GMAIL_ERROR_RESPONSE_TOO_LARGE: "ข้อมูล Gmail เกินขนาดที่อนุญาตครับ",
        GMAIL_ERROR_MESSAGE_NOT_FOUND: "ไม่พบอีเมลที่ Gmail ระบุไว้ครับ",
        GMAIL_ERROR_QUERY_INVALID: "คำขออ่าน Gmail ไม่ถูกต้องครับ",
    }

    def reply_for_approved(
        self,
        binding: ChatPluginActionBinding,
        outcome: ExecutionApprovalDecisionOutcome,
    ) -> str:
        if binding.gmail_query is None:
            return self.FAILURE_REPLY
        execution = outcome.execution
        result = execution.result
        if (
            execution.status != "completed"
            or result is None
            or result.status != "succeeded"
        ):
            code = getattr(result, "error", None) if result is not None else None
            return self._ERROR_REPLIES.get(code, self.FAILURE_REPLY)

        output = result.output
        if not isinstance(output, Mapping) or set(output) != {"content"}:
            return self.FAILURE_REPLY
        content = output.get("content")
        if not isinstance(content, str):
            return self.FAILURE_REPLY
        return self.reply_for_content(content)

    def reply_for_content(self, content: str) -> str:
        parsed = self._validated_result(content)
        if parsed is None:
            return self.FAILURE_REPLY
        if not parsed.messages:
            return self.EMPTY_REPLY

        lines = [f"พบอีเมล {len(parsed.messages)} รายการครับ"]
        for index, message in enumerate(parsed.messages, start=1):
            display_body = message.body or message.snippet
            lines.extend(
                (
                    f"อีเมล {index}",
                    f"จาก: {self._one_line(message.sender)}",
                    f"หัวข้อ: {self._one_line(message.subject)}",
                    f"เวลา: {message.received_at}",
                    (
                        "สถานะ: ยังไม่ได้อ่าน"
                        if message.unread
                        else "สถานะ: อ่านแล้ว"
                    ),
                    f"เนื้อหา: {self._one_line(display_body)}",
                )
            )
        reply = "\n".join(lines)
        if len(reply.encode("utf-8")) > GMAIL_MAX_RESULT_BYTES + 8192:
            return self.FAILURE_REPLY
        return reply

    @staticmethod
    def _validated_result(content: object) -> GmailReadResult | None:
        if (
            not isinstance(content, str)
            or len(content.encode("utf-8")) > GMAIL_MAX_RESULT_BYTES
        ):
            return None
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict) or set(payload) != {"messages"}:
            return None
        raw_messages = payload.get("messages")
        if (
            not isinstance(raw_messages, list)
            or len(raw_messages) > GMAIL_MAX_RESULTS
        ):
            return None

        messages: list[GmailMessage] = []
        required = {
            "message_id",
            "from",
            "subject",
            "received_at",
            "unread",
            "snippet",
            "body",
        }
        for item in raw_messages:
            if not isinstance(item, dict) or set(item) != required:
                return None
            try:
                message = GmailMessage(
                    message_id=item["message_id"],
                    sender=item["from"],
                    subject=item["subject"],
                    received_at=item["received_at"],
                    unread=item["unread"],
                    snippet=item["snippet"],
                    body=item["body"],
                )
            except (TypeError, ValueError):
                return None
            messages.append(message)
        try:
            return GmailReadResult(messages=tuple(messages))
        except ValueError:
            return None

    @staticmethod
    def _one_line(value: object) -> str:
        if not isinstance(value, str):
            return "—"
        normalized = " ".join(value.split())
        return normalized or "—"
