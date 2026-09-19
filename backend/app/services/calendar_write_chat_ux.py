"""D84 Calendar Write Chat UX orchestration foundation.

This module composes the frozen D83 deterministic create candidate with D73
proposal/owner-decision services and the existing D74 create executor boundary.
It does not parse new Calendar grammar, construct credentials, call connectors,
invoke AI, or implement retries.
"""

from __future__ import annotations

import hmac
import threading
import unicodedata
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID

from app.contracts.calendar_write_chat import CalendarWriteChatParseOutcome
from app.contracts.calendar_write_chat_ux import (
    CalendarWriteChatBinding,
    CalendarWriteChatDecisionOutcome,
    CalendarWriteChatProposalOutcome,
)
from app.contracts.google_calendar_create_execution import (
    CalendarCreateExecutionOutcome,
)
from app.contracts.google_calendar_write import (
    GoogleCalendarCreateEventRequest,
)
from app.services.calendar_write_approval import (
    CalendarWriteApprovalError,
    CalendarWriteApprovalService,
)


D84_CALENDAR_WRITE_BINDING_MAX_ITEMS = 128

_PLAINTEXT_APPROVE = frozenset(
    {
        "อนุมัติ",
        "อนุมัติครับ",
        "อนุมัติครับผม",
        "อนุมัติค่ะ",
        "อนุมัติคะ",
        "approve",
        "approved",
    }
)
_PLAINTEXT_DENY = frozenset(
    {
        "ไม่อนุมัติ",
        "ไม่อนุมัติครับ",
        "ไม่อนุมัติค่ะ",
        "ปฏิเสธ",
        "ปฏิเสธครับ",
        "ปฏิเสธค่ะ",
        "ยกเลิก",
        "ยกเลิกครับ",
        "deny",
        "denied",
        "cancel",
    }
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_plaintext(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()
    return " ".join(normalized.split()).casefold()


class CalendarCreateExecutor(Protocol):
    def execute_create(
        self,
        approval_id: str,
        write_digest: str,
    ) -> CalendarCreateExecutionOutcome:
        ...


class CalendarWriteChatUXError(RuntimeError):
    reason_code = "calendar_write_chat_ux_error"


class CalendarWriteChatUXPendingProposalError(CalendarWriteChatUXError):
    reason_code = "calendar_write_chat_pending_proposal_exists"


class CalendarWriteChatUXBindingNotFoundError(CalendarWriteChatUXError):
    reason_code = "calendar_write_chat_binding_not_found"


class CalendarWriteChatUXBindingDigestMismatchError(CalendarWriteChatUXError):
    reason_code = "calendar_write_chat_binding_digest_mismatch"


class CalendarWriteChatUXBindingCollisionError(CalendarWriteChatUXError):
    reason_code = "calendar_write_chat_binding_collision"


class CalendarWriteChatUXBindingStoreFullError(CalendarWriteChatUXError):
    reason_code = "calendar_write_chat_binding_store_full"


class CalendarWriteChatUXCandidateInvalidError(CalendarWriteChatUXError):
    reason_code = "calendar_write_chat_candidate_invalid"


class CalendarWriteChatBindingStore:
    """Bounded process-local D84 correlation only; grants no authority."""

    def __init__(
        self,
        *,
        max_items: int = D84_CALENDAR_WRITE_BINDING_MAX_ITEMS,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        if (
            isinstance(max_items, bool)
            or not isinstance(max_items, int)
            or max_items < 1
        ):
            raise ValueError("max_items must be a positive integer.")
        self._max_items = max_items
        self._clock = clock
        self._items: dict[str, CalendarWriteChatBinding] = {}
        self._lock = threading.Lock()

    @property
    def record_count(self) -> int:
        now = self._now()
        with self._lock:
            self._cleanup(now)
            return len(self._items)

    def add(
        self,
        binding: CalendarWriteChatBinding,
    ) -> CalendarWriteChatBinding:
        if not isinstance(binding, CalendarWriteChatBinding):
            raise TypeError("binding must be CalendarWriteChatBinding.")
        now = self._now()
        with self._lock:
            self._cleanup(now)
            existing = self._items.get(binding.approval_id)
            if existing is not None:
                if existing == binding:
                    return existing
                raise CalendarWriteChatUXBindingCollisionError(
                    "approval_id is already bound differently."
                )
            if any(
                item.conversation_id == binding.conversation_id
                for item in self._items.values()
            ):
                raise CalendarWriteChatUXPendingProposalError(
                    "conversation already has a pending Calendar write."
                )
            if len(self._items) >= self._max_items:
                raise CalendarWriteChatUXBindingStoreFullError(
                    "Calendar write Chat binding capacity is full."
                )
            if binding.expires_at <= now:
                raise CalendarWriteChatUXBindingNotFoundError(
                    "Calendar write Chat binding is already expired."
                )
            self._items[binding.approval_id] = binding
            return binding

    def pending_for_conversation(
        self,
        conversation_id: UUID | None,
    ) -> CalendarWriteChatBinding | None:
        if not isinstance(conversation_id, UUID):
            return None
        now = self._now()
        with self._lock:
            self._cleanup(now)
            for binding in self._items.values():
                if binding.conversation_id == conversation_id:
                    return binding
            return None

    def resolve(
        self,
        approval_id: str,
        write_digest: str,
    ) -> CalendarWriteChatBinding:
        if (
            not isinstance(approval_id, str)
            or not approval_id
            or approval_id != approval_id.strip()
        ):
            raise CalendarWriteChatUXBindingNotFoundError(
                "Calendar write Chat binding is unavailable."
            )
        if not isinstance(write_digest, str):
            raise CalendarWriteChatUXBindingDigestMismatchError(
                "Calendar write Chat digest does not match."
            )
        now = self._now()
        with self._lock:
            self._cleanup(now)
            binding = self._items.get(approval_id)
            if binding is None:
                raise CalendarWriteChatUXBindingNotFoundError(
                    "Calendar write Chat binding is unavailable."
                )
            if not hmac.compare_digest(binding.write_digest, write_digest):
                raise CalendarWriteChatUXBindingDigestMismatchError(
                    "Calendar write Chat digest does not match."
                )
            return binding

    def consume(
        self,
        approval_id: str,
        write_digest: str,
    ) -> CalendarWriteChatBinding:
        now = self._now()
        with self._lock:
            self._cleanup(now)
            binding = self._items.get(approval_id)
            if binding is None:
                raise CalendarWriteChatUXBindingNotFoundError(
                    "Calendar write Chat binding is unavailable."
                )
            if not isinstance(write_digest, str) or not hmac.compare_digest(
                binding.write_digest,
                write_digest,
            ):
                raise CalendarWriteChatUXBindingDigestMismatchError(
                    "Calendar write Chat digest does not match."
                )
            self._items.pop(approval_id, None)
            return binding

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def _now(self) -> datetime:
        now = self._clock()
        if (
            not isinstance(now, datetime)
            or now.tzinfo is None
            or now.utcoffset() is None
        ):
            raise ValueError("clock must return a timezone-aware datetime.")
        return now

    def _cleanup(self, now: datetime) -> None:
        expired = [
            approval_id
            for approval_id, binding in self._items.items()
            if now >= binding.expires_at
        ]
        for approval_id in expired:
            self._items.pop(approval_id, None)


class CalendarWriteChatUXResponseComposer:
    """Deterministic D84 owner wording; never uses provider or AI text."""

    def proposal(self, language: str) -> str:
        if language == "en":
            return (
                "Calendar create preview is ready for structured owner review. "
                "No Calendar write has occurred. Use the Approve or Deny button."
            )
        return (
            "เตรียม Calendar create preview สำหรับการตรวจสอบของเจ้าของแล้วครับ "
            "ยังไม่มีการเขียน Calendar กรุณาตัดสินใจด้วยปุ่ม Approve หรือ Deny"
        )

    def plaintext_decision_required(self, language: str) -> str:
        if language == "en":
            return (
                "This Calendar write must be decided with the structured "
                "Approve/Deny controls. Plain Chat text has no D73 decision "
                "authority and no Calendar write was performed."
            )
        return (
            "Calendar write นี้ต้องตัดสินใจผ่านปุ่ม Approve/Deny "
            "ใน structured approval card ครับ ข้อความใน Chat "
            "ไม่มีสิทธิ์ตัดสินใจ D73 และยังไม่มีการเขียน Calendar"
        )

    def denied(self, language: str) -> str:
        if language == "en":
            return (
                "Calendar create was denied by the owner. "
                "No Calendar write was performed."
            )
        return (
            "เจ้าของปฏิเสธ Calendar create นี้แล้วครับ "
            "ไม่มีการเขียน Calendar"
        )

    def execution(
        self,
        *,
        language: str,
        status: str,
        reason_code: str,
    ) -> str:
        if status == "succeeded":
            if language == "en":
                return "Calendar event was created successfully."
            return "สร้างนัดใน Calendar สำเร็จแล้วครับ"

        if status == "indeterminate":
            if language == "en":
                return (
                    "The Calendar create outcome is indeterminate. "
                    "O-AI will not retry automatically. Check Calendar before "
                    "submitting a new request."
                )
            return (
                "ไม่สามารถยืนยันได้ว่าการสร้างนัดสำเร็จหรือไม่ครับ "
                "O-AI จะไม่ retry อัตโนมัติ กรุณาตรวจ Calendar "
                "ก่อนส่งคำขอใหม่"
            )

        safe_en = {
            "calendar_create_credential_unavailable": (
                "Calendar create failed because the required credential "
                "was unavailable. No automatic retry will occur."
            ),
            "calendar_create_provider_rejected": (
                "Calendar create was rejected by the provider. "
                "No automatic retry will occur."
            ),
            "calendar_create_invalid_request": (
                "Calendar create failed because the bounded request was invalid. "
                "No automatic retry will occur."
            ),
            "calendar_create_parameters_invalid": (
                "Calendar create failed because execution parameters were invalid. "
                "No automatic retry will occur."
            ),
            "calendar_create_execution_failed": (
                "Calendar create failed. No automatic retry will occur."
            ),
        }
        safe_th = {
            "calendar_create_credential_unavailable": (
                "สร้างนัดไม่สำเร็จเพราะ credential ที่จำเป็นไม่พร้อมใช้งานครับ "
                "ระบบจะไม่ retry อัตโนมัติ"
            ),
            "calendar_create_provider_rejected": (
                "ผู้ให้บริการปฏิเสธการสร้างนัดครับ ระบบจะไม่ retry อัตโนมัติ"
            ),
            "calendar_create_invalid_request": (
                "สร้างนัดไม่สำเร็จเพราะคำขอแบบ bounded ไม่ถูกต้องครับ "
                "ระบบจะไม่ retry อัตโนมัติ"
            ),
            "calendar_create_parameters_invalid": (
                "สร้างนัดไม่สำเร็จเพราะ execution parameters ไม่ถูกต้องครับ "
                "ระบบจะไม่ retry อัตโนมัติ"
            ),
            "calendar_create_execution_failed": (
                "สร้างนัดไม่สำเร็จครับ ระบบจะไม่ retry อัตโนมัติ"
            ),
        }
        if language == "en":
            return safe_en.get(
                reason_code,
                "Calendar create failed. No automatic retry will occur.",
            )
        return safe_th.get(
            reason_code,
            "สร้างนัดไม่สำเร็จครับ ระบบจะไม่ retry อัตโนมัติ",
        )


class CalendarWriteChatUXService:
    """Compose D83 -> D73 -> structured owner decision -> existing D74."""

    def __init__(
        self,
        *,
        approval_service: CalendarWriteApprovalService,
        binding_store: CalendarWriteChatBindingStore,
        create_executor: CalendarCreateExecutor,
        composer: CalendarWriteChatUXResponseComposer | None = None,
    ) -> None:
        if not isinstance(approval_service, CalendarWriteApprovalService):
            raise TypeError(
                "approval_service must be CalendarWriteApprovalService."
            )
        if not isinstance(binding_store, CalendarWriteChatBindingStore):
            raise TypeError(
                "binding_store must be CalendarWriteChatBindingStore."
            )
        execute_create = getattr(create_executor, "execute_create", None)
        if not callable(execute_create):
            raise TypeError("create_executor must expose execute_create().")
        self._approval_service = approval_service
        self._binding_store = binding_store
        self._create_executor = create_executor
        self._composer = composer or CalendarWriteChatUXResponseComposer()

    def propose_candidate(
        self,
        *,
        candidate: CalendarWriteChatParseOutcome,
        conversation_id: UUID,
    ) -> CalendarWriteChatProposalOutcome:
        if not isinstance(candidate, CalendarWriteChatParseOutcome):
            raise TypeError(
                "candidate must be CalendarWriteChatParseOutcome."
            )
        if not isinstance(conversation_id, UUID):
            raise TypeError("conversation_id must be a UUID.")
        if (
            candidate.disposition != "supported_create"
            or candidate.language not in {"th", "en"}
            or not isinstance(
                candidate.request,
                GoogleCalendarCreateEventRequest,
            )
        ):
            raise CalendarWriteChatUXCandidateInvalidError(
                "Only an exact D83 supported_create candidate is accepted."
            )
        if self._binding_store.pending_for_conversation(
            conversation_id
        ) is not None:
            raise CalendarWriteChatUXPendingProposalError(
                "conversation already has a pending Calendar write."
            )

        proposal_outcome = self._approval_service.propose(candidate.request)
        proposal = proposal_outcome.proposal
        binding = CalendarWriteChatBinding(
            approval_id=proposal.approval_id,
            write_digest=proposal.write_digest,
            conversation_id=conversation_id,
            language=candidate.language,
            expires_at=proposal.expires_at,
        )
        try:
            self._binding_store.add(binding)
        except CalendarWriteChatUXError:
            self._neutralize_orphan(
                proposal.approval_id,
                proposal.write_digest,
            )
            raise
        except Exception as error:
            self._neutralize_orphan(
                proposal.approval_id,
                proposal.write_digest,
            )
            raise CalendarWriteChatUXBindingCollisionError(
                "Calendar write Chat binding failed closed."
            ) from error

        return CalendarWriteChatProposalOutcome(
            conversation_id=conversation_id,
            status="pending_approval",
            reason_code="calendar_write_owner_decision_required",
            proposal=proposal,
            reply=self._composer.proposal(candidate.language),
        )

    def plaintext_decision_kind(
        self,
        *,
        conversation_id: UUID | None,
        message: object,
    ) -> str:
        binding = self._binding_store.pending_for_conversation(
            conversation_id
        )
        if binding is None or not isinstance(message, str):
            return "none"
        key = _normalize_plaintext(message)
        if key in _PLAINTEXT_APPROVE:
            return "approve"
        if key in _PLAINTEXT_DENY:
            return "deny"
        return "none"

    def plaintext_decision_reply(
        self,
        *,
        conversation_id: UUID,
        message: str,
    ) -> str:
        kind = self.plaintext_decision_kind(
            conversation_id=conversation_id,
            message=message,
        )
        if kind == "none":
            raise ValueError(
                "No pending D84 plaintext decision guard matches this message."
            )
        binding = self._binding_store.pending_for_conversation(
            conversation_id
        )
        if binding is None:
            raise CalendarWriteChatUXBindingNotFoundError(
                "Calendar write Chat binding is unavailable."
            )
        return self._composer.plaintext_decision_required(binding.language)

    def decision_binding(
        self,
        *,
        approval_id: str,
        write_digest: str,
    ) -> CalendarWriteChatBinding:
        """Resolve non-authoritative Chat correlation before owner decision."""
        return self._binding_store.resolve(
            approval_id,
            write_digest,
        )

    def deny(
        self,
        *,
        approval_id: str,
        write_digest: str,
    ) -> CalendarWriteChatDecisionOutcome:
        binding = self._binding_store.resolve(
            approval_id,
            write_digest,
        )
        self._approval_service.deny(approval_id, write_digest)
        self._binding_store.consume(approval_id, write_digest)
        return CalendarWriteChatDecisionOutcome(
            conversation_id=binding.conversation_id,
            approval_id=approval_id,
            write_digest=write_digest,
            decision="denied",
            status="denied",
            reason_code="owner_denied",
            reply=self._composer.denied(binding.language),
        )

    def approve(
        self,
        *,
        approval_id: str,
        write_digest: str,
    ) -> CalendarWriteChatDecisionOutcome:
        binding = self._binding_store.resolve(
            approval_id,
            write_digest,
        )
        self._approval_service.approve(approval_id, write_digest)

        try:
            execution = self._create_executor.execute_create(
                approval_id,
                write_digest,
            )
            if not isinstance(execution, CalendarCreateExecutionOutcome):
                raise TypeError(
                    "create executor returned an invalid D74 outcome."
                )
            if (
                execution.approval_id != approval_id
                or not hmac.compare_digest(
                    execution.write_digest,
                    write_digest,
                )
            ):
                raise ValueError(
                    "D74 execution outcome does not match D84 decision."
                )
        except Exception:
            self._binding_store.consume(approval_id, write_digest)
            return CalendarWriteChatDecisionOutcome(
                conversation_id=binding.conversation_id,
                approval_id=approval_id,
                write_digest=write_digest,
                decision="approved",
                status="indeterminate",
                reason_code="calendar_create_indeterminate",
                reply=self._composer.execution(
                    language=binding.language,
                    status="indeterminate",
                    reason_code="calendar_create_indeterminate",
                ),
            )

        self._binding_store.consume(approval_id, write_digest)
        return CalendarWriteChatDecisionOutcome(
            conversation_id=binding.conversation_id,
            approval_id=approval_id,
            write_digest=write_digest,
            decision="approved",
            status=execution.status,
            reason_code=execution.reason_code,
            reply=self._composer.execution(
                language=binding.language,
                status=execution.status,
                reason_code=execution.reason_code,
            ),
            event_id=execution.event_id,
        )

    def pending_binding(
        self,
        conversation_id: UUID | None,
    ) -> CalendarWriteChatBinding | None:
        return self._binding_store.pending_for_conversation(
            conversation_id
        )

    def _neutralize_orphan(
        self,
        approval_id: str,
        write_digest: str,
    ) -> None:
        try:
            self._approval_service.deny(
                approval_id,
                write_digest,
            )
        except CalendarWriteApprovalError:
            # D84 grants no authority from an orphan.  The D73 state machine
            # remains authoritative; no D74 call is made here.
            return


__all__ = [
    "D84_CALENDAR_WRITE_BINDING_MAX_ITEMS",
    "CalendarCreateExecutor",
    "CalendarWriteChatBindingStore",
    "CalendarWriteChatUXBindingCollisionError",
    "CalendarWriteChatUXBindingDigestMismatchError",
    "CalendarWriteChatUXBindingNotFoundError",
    "CalendarWriteChatUXBindingStoreFullError",
    "CalendarWriteChatUXCandidateInvalidError",
    "CalendarWriteChatUXError",
    "CalendarWriteChatUXPendingProposalError",
    "CalendarWriteChatUXResponseComposer",
    "CalendarWriteChatUXService",
]
