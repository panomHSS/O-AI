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
from app.contracts.cross_connector_context import (
    CROSS_CONNECTOR_GMAIL_MAX_TEXT_CHARS,
    GmailContextMessage,
)
from app.contracts.chat_plugin_action import (
    ChatPluginActionBinding,
    ChatPluginIntentOutcome,
)
from app.contracts.execution_approval import ExecutionApprovalDecisionOutcome
from app.contracts.gmail import (
    GMAIL_MAX_RESULTS,
    GmailMessage,
    GmailReadDisplayMessage,
    GmailReadQuery,
    GmailReadResult,
)


_EMAIL_PATTERN = (
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+"
)
_EMAIL_TOKEN_RE = re.compile(_EMAIL_PATTERN)

_THAI_POLITE = r"(?:\s*(?:ครับ|ค่ะ|คะ))?"

_RECENT_PATTERNS = (
    re.compile(
        rf"(?:มี\s*)?(?:อีเมล|เมล)ล่าสุด"
        rf"(?:อะไรบ้าง|บ้าง|ไหม|หรือเปล่า)?{_THAI_POLITE}",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?:ช่วย\s*)?(?:ดู|เช็ก|เช็ค)\s*(?:อีเมล|เมล)ล่าสุด"
        rf"(?:ให้หน่อย)?{_THAI_POLITE}",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?:ช่วย\s*)?(?:ดู|เช็ก|เช็ค)\s+gmail\s+ล่าสุด"
        rf"(?:ให้หน่อย)?{_THAI_POLITE}",
        re.IGNORECASE,
    ),
    re.compile(r"(?:latest|recent)\s+emails?", re.IGNORECASE),
    re.compile(
        r"(?:please\s+)?(?:show|check|list|read)\s+"
        r"(?:my\s+)?(?:latest|recent)\s+emails?",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:please\s+)?(?:show|check|list|read)\s+"
        r"(?:my\s+)?gmail\s+(?:latest|recent)(?:\s+emails?)?",
        re.IGNORECASE,
    ),
)

_UNREAD_PATTERNS = (
    re.compile(
        rf"(?:มี\s*)?(?:อีเมล|เมล)(?:ที่)?ยัง(?:ไม่ได้|ไม่)อ่าน"
        rf"(?:อะไรบ้าง|บ้าง|ไหม|หรือเปล่า)?{_THAI_POLITE}",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?:ช่วย\s*)?(?:ดู|เช็ก|เช็ค)\s*(?:อีเมล|เมล)"
        rf"(?:ที่)?ยัง(?:ไม่ได้|ไม่)อ่าน(?:ให้หน่อย)?{_THAI_POLITE}",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?:ช่วย\s*)?(?:ดู|เช็ก|เช็ค)\s+gmail\s+"
        rf"(?:ที่)?ยัง(?:ไม่ได้|ไม่)อ่าน(?:ให้หน่อย)?{_THAI_POLITE}",
        re.IGNORECASE,
    ),
    re.compile(r"unread\s+emails?", re.IGNORECASE),
    re.compile(
        r"(?:please\s+)?(?:show|check|list|read)\s+"
        r"(?:my\s+)?unread\s+emails?",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:please\s+)?(?:show|check|list|read)\s+"
        r"(?:my\s+)?gmail\s+unread(?:\s+emails?)?",
        re.IGNORECASE,
    ),
)

_FROM_PATTERNS = (
    re.compile(
        rf"(?:มี\s*)?(?:อีเมล|เมล)จาก\s+({_EMAIL_PATTERN})"
        rf"(?:\s*(?:ไหม|หรือเปล่า|หรือไม่|บ้าง))?{_THAI_POLITE}",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?:ช่วย\s*)?(?:ดู|เช็ก|เช็ค)\s*(?:อีเมล|เมล)จาก\s+"
        rf"({_EMAIL_PATTERN})(?:ให้หน่อย)?{_THAI_POLITE}",
        re.IGNORECASE,
    ),
    re.compile(rf"emails?\s+from\s+({_EMAIL_PATTERN})", re.IGNORECASE),
    re.compile(
        rf"(?:please\s+)?(?:show|check|list|read)\s+"
        rf"(?:my\s+)?emails?\s+from\s+({_EMAIL_PATTERN})",
        re.IGNORECASE,
    ),
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
    "forward",
    "ส่งต่อ",
    "draft",
    "compose",
    "ร่างอีเมล",
    "delete",
    "ลบอีเมล",
    "archive",
    "mark as read",
    "mark as unread",
    "ทำเป็นอ่านแล้ว",
    "ทำเป็นยังไม่อ่าน",
    "star email",
    "ติดดาว",
)

_EXAMPLE_PREFIXES = (
    "ตัวอย่าง",
    "ยกตัวอย่าง",
    "เช่น",
    "example",
    "for example",
)
_THAI_NEGATION_RE = re.compile(r"^(?:กรุณา\s*)?(?:อย่า|ไม่ต้อง|ไม่ต้องการ)")
_ENGLISH_NEGATION_RE = re.compile(
    r"^(?:please\s+)?(?:do\s+not|don't|dont)\b",
    re.IGNORECASE,
)
_QUOTE_PAIRS = (
    ('"', '"'),
    ("'", "'"),
    ("`", "`"),
    ("“", "”"),
    ("‘", "’"),
)


def _contains_quoted_text(value: str) -> bool:
    for opening, closing in _QUOTE_PAIRS:
        if opening == closing:
            if value.count(opening) >= 2:
                return True
        elif opening in value and closing in value:
            return True
    return False


def _is_non_routing_reference(normalized: str) -> bool:
    folded = normalized.casefold()
    if _contains_quoted_text(normalized):
        return True
    if any(folded.startswith(prefix) for prefix in _EXAMPLE_PREFIXES):
        return True
    return (
        _THAI_NEGATION_RE.match(normalized) is not None
        or _ENGLISH_NEGATION_RE.match(normalized) is not None
    )


def _fullmatch_any(patterns: tuple[re.Pattern[str], ...], value: str) -> bool:
    return any(pattern.fullmatch(value) is not None for pattern in patterns)


class GmailChatIntentRouter:
    """Recognize bounded D77 queries through deterministic D85 read UX grammar."""

    @staticmethod
    def has_signal(message: object) -> bool:
        if not isinstance(message, str) or not message.strip():
            return False
        normalized = " ".join(message.strip().split())
        if _is_non_routing_reference(normalized):
            return False
        folded = normalized.casefold()
        return (
            "อีเมล" in folded
            or "เมล" in folded
            or re.search(r"\bgmail\b", folded) is not None
            or re.search(r"\bemails?\b", folded) is not None
        )

    def classify(self, message: object) -> ChatPluginIntentOutcome:
        if not isinstance(message, str) or not message.strip():
            return ChatPluginIntentOutcome(status="none")

        normalized = " ".join(message.strip().split())

        if _is_non_routing_reference(normalized):
            return ChatPluginIntentOutcome(status="none")

        folded = normalized.casefold()

        if any(phrase in folded for phrase in _UNSUPPORTED_PHRASES):
            return ChatPluginIntentOutcome(status="invalid")

        if not self.has_signal(normalized):
            return ChatPluginIntentOutcome(status="none")
        from_matches = [
            match
            for pattern in _FROM_PATTERNS
            if (match := pattern.fullmatch(normalized)) is not None
        ]
        recent = _fullmatch_any(_RECENT_PATTERNS, normalized)
        unread = _fullmatch_any(_UNREAD_PATTERNS, normalized)

        mode_count = int(bool(from_matches)) + int(recent) + int(unread)
        if mode_count != 1:
            return ChatPluginIntentOutcome(status="invalid")

        if from_matches:
            email_tokens = _EMAIL_TOKEN_RE.findall(normalized)
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

    def context_messages_for_approved(
        self,
        binding: ChatPluginActionBinding,
        outcome: ExecutionApprovalDecisionOutcome,
    ) -> tuple[GmailContextMessage, ...] | None:
        """Project only a strictly validated approved Gmail result for D78."""
        if binding.gmail_query is None:
            return None
        execution = outcome.execution
        result = execution.result
        if (
            execution.status != "completed"
            or result is None
            or result.status != "succeeded"
        ):
            return None
        output = result.output
        if not isinstance(output, Mapping) or set(output) != {"content"}:
            return None
        content = output.get("content")
        if not isinstance(content, str):
            return None
        parsed = self._validated_result(content)
        if parsed is None:
            return None

        projected: list[GmailContextMessage] = []
        for message in parsed.messages:
            text = (message.body or message.snippet)[
                :CROSS_CONNECTOR_GMAIL_MAX_TEXT_CHARS
            ]
            try:
                projected.append(
                    GmailContextMessage(
                        sender=message.sender,
                        subject=message.subject,
                        received_at=message.received_at,
                        unread=message.unread,
                        text=text,
                    )
                )
            except (TypeError, ValueError):
                return None
        return tuple(projected)

    def display_messages_for_approved(
        self,
        binding: ChatPluginActionBinding,
        outcome: ExecutionApprovalDecisionOutcome,
    ) -> tuple[GmailReadDisplayMessage, ...] | None:
        """Return validated transient display data; never persistence authority."""
        if binding.gmail_query is None:
            return None
        execution = outcome.execution
        result = execution.result
        if (
            execution.status != "completed"
            or result is None
            or result.status != "succeeded"
        ):
            return None
        output = result.output
        if not isinstance(output, Mapping) or set(output) != {"content"}:
            return None
        content = output.get("content")
        if not isinstance(content, str):
            return None
        parsed = self._validated_result(content)
        if parsed is None:
            return None

        try:
            return tuple(
                GmailReadDisplayMessage(
                    sender=message.sender,
                    subject=message.subject,
                    received_at=message.received_at,
                    unread=message.unread,
                    snippet=message.snippet,
                    body=message.body,
                )
                for message in parsed.messages
            )
        except (TypeError, ValueError):
            return None

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
