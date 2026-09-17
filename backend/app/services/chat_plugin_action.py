"""D61 deterministic Chat-to-Plugin intent, enablement, and completion."""

from __future__ import annotations

import json
import re
import threading
from collections.abc import Mapping
from datetime import datetime, timezone
from uuid import UUID

from app.connectors.github_public_repository import validate_repository_reference
from app.contracts.gmail import (
    GMAIL_PLUGIN_ID,
    GMAIL_PLUGIN_VERSION,
    GMAIL_READ_CAPABILITY_NAME,
)
from app.contracts.google_calendar import (
    GOOGLE_CALENDAR_CAPABILITY_NAME,
    GOOGLE_CALENDAR_PLUGIN_ID,
    GOOGLE_CALENDAR_PLUGIN_VERSION,
)
from app.contracts.chat_plugin_action import (
    ChatPluginActionBinding,
    ChatPluginActionCompletion,
    ChatPluginIntentOutcome,
)
from app.contracts.execution_approval import ExecutionApprovalDecisionOutcome
from app.services.chat_calendar import (
    CalendarChatCompletionComposer,
    CalendarChatIntentRouter,
)
from app.services.chat_gmail import (
    GmailChatCompletionComposer,
    GmailChatIntentRouter,
)
from app.services.conversations import ConversationService
from app.services.cross_connector_context import (
    CrossConnectorContextStore,
)
from app.services.plugin_governance import PluginGovernanceService
from app.services.plugin_loading import PluginLoadingService
from app.services.plugin_module_exposure import PluginModuleExposureService
from app.services.plugin_permission_binding import PluginPermissionBindingService
from app.services.plugin_registration_activation import (
    PluginRegistrationActivationService,
)


GITHUB_PUBLIC_REPO_PLUGIN_ID = "github_public_repo"
GITHUB_PUBLIC_REPO_PLUGIN_VERSION = "1.0.0"
GITHUB_PUBLIC_REPO_CAPABILITY_NAME = "repository_metadata"
GITHUB_PUBLIC_REPO_ADAPTER_ID = "module.plugin.github_public_repo"
GITHUB_PUBLIC_REPO_OPERATION = "get_repository_metadata"
GITHUB_PUBLIC_REPO_CAPABILITY_ID = (
    "exec.plugin.github_public_repo.repository_metadata"
)

CHAT_PLUGIN_BINDING_MAX_ITEMS = 256

_REPOSITORY_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9._/-])"
    r"([A-Za-z0-9][A-Za-z0-9._-]{0,99}/"
    r"[A-Za-z0-9][A-Za-z0-9._-]{0,99})"
    r"(?![A-Za-z0-9._/-])"
)

_REQUIRED_RESULT_KEYS = frozenset(
    {
        "archived",
        "default_branch",
        "description",
        "fork",
        "forks_count",
        "full_name",
        "html_url",
        "language",
        "license",
        "open_issues_count",
        "stargazers_count",
        "updated_at",
        "visibility",
    }
)


class ChatPluginIntentRouter:
    """Recognize narrow deterministic GitHub, Gmail, or Calendar requests."""

    _signals = (
        "repository",
        "repo",
        "metadata",
        "stars",
        "star",
        "license",
        "branch",
        "language",
        "รีโป",
        "ดาว",
        "ไลเซนส์",
    )

    def __init__(
        self,
        *,
        calendar_router: CalendarChatIntentRouter | None = None,
        gmail_router: GmailChatIntentRouter | None = None,
    ) -> None:
        self._calendar_router = calendar_router or CalendarChatIntentRouter()
        self._gmail_router = gmail_router or GmailChatIntentRouter()

    def is_gmail_request(self, message: object) -> bool:
        return self._gmail_router.has_signal(message)

    def classify(self, message: object) -> ChatPluginIntentOutcome:
        if not isinstance(message, str) or not message.strip():
            return ChatPluginIntentOutcome(status="none")

        normalized = message.strip()
        folded = normalized.casefold()
        github_signal = (
            "github" in folded
            and any(signal in folded for signal in self._signals)
        )
        gmail_signal = self._gmail_router.has_signal(normalized)
        calendar_outcome = self._calendar_router.classify(normalized)
        calendar_signal = (
            calendar_outcome.status != "none"
            or "google calendar" in folded
            or "ปฏิทิน" in folded
            or "นัด" in folded
        )

        if sum((github_signal, gmail_signal, calendar_signal)) > 1:
            return ChatPluginIntentOutcome(status="invalid")

        if github_signal:
            return self._classify_github(normalized)
        if gmail_signal:
            return self._gmail_router.classify(normalized)
        return calendar_outcome

    @staticmethod
    def _classify_github(normalized: str) -> ChatPluginIntentOutcome:
        folded = normalized.casefold()
        if "http://" in folded or "https://" in folded:
            return ChatPluginIntentOutcome(status="invalid")

        candidates: list[str] = []
        for match in _REPOSITORY_TOKEN_RE.finditer(normalized):
            candidate = match.group(1)
            try:
                owner, repository = validate_repository_reference(candidate)
            except Exception:
                continue
            canonical = f"{owner}/{repository}"
            if canonical not in candidates:
                candidates.append(canonical)

        if len(candidates) != 1:
            return ChatPluginIntentOutcome(status="invalid")

        return ChatPluginIntentOutcome(
            status="matched",
            repository_reference=candidates[0],
        )


class ChatPluginActionBindingStore:
    """Bounded process-local correlation only; grants no execution authority."""

    def __init__(
        self,
        *,
        max_items: int = CHAT_PLUGIN_BINDING_MAX_ITEMS,
    ) -> None:
        if (
            isinstance(max_items, bool)
            or not isinstance(max_items, int)
            or max_items < 1
        ):
            raise ValueError("max_items must be a positive integer.")
        self._max_items = max_items
        self._items: dict[str, ChatPluginActionBinding] = {}
        self._lock = threading.Lock()

    def add(self, binding: ChatPluginActionBinding) -> ChatPluginActionBinding:
        if not isinstance(binding, ChatPluginActionBinding):
            raise TypeError("binding must be a ChatPluginActionBinding.")
        now = datetime.now(timezone.utc)
        with self._lock:
            self._cleanup_expired(now)
            existing = self._items.get(binding.approval_id)
            if existing is not None:
                if existing != binding:
                    raise ValueError("approval_id is already bound differently.")
                return existing
            if len(self._items) >= self._max_items:
                raise RuntimeError("chat_plugin_binding_store_full")
            self._items[binding.approval_id] = binding
            return binding

    def consume(self, approval_id: str) -> ChatPluginActionBinding | None:
        if (
            not isinstance(approval_id, str)
            or not approval_id
            or approval_id != approval_id.strip()
        ):
            return None
        now = datetime.now(timezone.utc)
        with self._lock:
            self._cleanup_expired(now)
            return self._items.pop(approval_id, None)

    def resolve(self, approval_id: str) -> ChatPluginActionBinding | None:
        if not isinstance(approval_id, str) or not approval_id:
            return None
        now = datetime.now(timezone.utc)
        with self._lock:
            self._cleanup_expired(now)
            return self._items.get(approval_id)

    def has_pending_calendar_binding(
        self,
        conversation_id: UUID,
    ) -> bool:
        if not isinstance(conversation_id, UUID):
            return False
        now = datetime.now(timezone.utc)
        with self._lock:
            self._cleanup_expired(now)
            return any(
                binding.conversation_id == conversation_id
                and binding.calendar_window is not None
                for binding in self._items.values()
            )

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def _cleanup_expired(self, now: datetime) -> None:
        expired = [
            approval_id
            for approval_id, binding in self._items.items()
            if now >= binding.expires_at
        ]
        for approval_id in expired:
            self._items.pop(approval_id, None)


class FirstPartyPluginEnablementService:
    """Materialize only the owner-configured exact first-party D59 lifecycle."""

    def __init__(
        self,
        *,
        governance: PluginGovernanceService,
        loading: PluginLoadingService,
        exposure: PluginModuleExposureService,
        binding: PluginPermissionBindingService,
        activation: PluginRegistrationActivationService,
    ) -> None:
        self._governance = governance
        self._loading = loading
        self._exposure = exposure
        self._binding = binding
        self._activation = activation

    def ensure_github_public_repository_enabled(
        self,
        enabled: bool,
    ) -> None:
        if type(enabled) is not bool:
            raise TypeError("enabled must be an exact bool.")
        if not enabled:
            return

        self._governance.admit(
            GITHUB_PUBLIC_REPO_PLUGIN_ID,
            GITHUB_PUBLIC_REPO_PLUGIN_VERSION,
        )
        self._loading.load(
            GITHUB_PUBLIC_REPO_PLUGIN_ID,
            GITHUB_PUBLIC_REPO_PLUGIN_VERSION,
        )
        self._exposure.expose(
            GITHUB_PUBLIC_REPO_PLUGIN_ID,
            GITHUB_PUBLIC_REPO_PLUGIN_VERSION,
            GITHUB_PUBLIC_REPO_CAPABILITY_NAME,
        )
        self._binding.bind(
            GITHUB_PUBLIC_REPO_PLUGIN_ID,
            GITHUB_PUBLIC_REPO_PLUGIN_VERSION,
            GITHUB_PUBLIC_REPO_CAPABILITY_NAME,
        )
        self._activation.activate(
            GITHUB_PUBLIC_REPO_PLUGIN_ID,
            GITHUB_PUBLIC_REPO_PLUGIN_VERSION,
            GITHUB_PUBLIC_REPO_CAPABILITY_NAME,
        )

    def ensure_google_calendar_enabled(
        self,
        enabled: bool,
    ) -> None:
        """Materialize D63 lifecycle metadata without reading credentials."""
        if type(enabled) is not bool:
            raise TypeError("enabled must be an exact bool.")
        if not enabled:
            return

        self._governance.admit(
            GOOGLE_CALENDAR_PLUGIN_ID,
            GOOGLE_CALENDAR_PLUGIN_VERSION,
        )
        self._loading.load(
            GOOGLE_CALENDAR_PLUGIN_ID,
            GOOGLE_CALENDAR_PLUGIN_VERSION,
        )
        self._exposure.expose(
            GOOGLE_CALENDAR_PLUGIN_ID,
            GOOGLE_CALENDAR_PLUGIN_VERSION,
            GOOGLE_CALENDAR_CAPABILITY_NAME,
        )
        self._binding.bind(
            GOOGLE_CALENDAR_PLUGIN_ID,
            GOOGLE_CALENDAR_PLUGIN_VERSION,
            GOOGLE_CALENDAR_CAPABILITY_NAME,
        )
        self._activation.activate(
            GOOGLE_CALENDAR_PLUGIN_ID,
            GOOGLE_CALENDAR_PLUGIN_VERSION,
            GOOGLE_CALENDAR_CAPABILITY_NAME,
        )

    def ensure_gmail_enabled(self, enabled: bool) -> None:
        """Materialize D77 Gmail read lifecycle without credential resolution."""
        if type(enabled) is not bool:
            raise TypeError("enabled must be an exact bool.")
        if not enabled:
            return
        self._governance.admit(GMAIL_PLUGIN_ID, GMAIL_PLUGIN_VERSION)
        self._loading.load(GMAIL_PLUGIN_ID, GMAIL_PLUGIN_VERSION)
        self._exposure.expose(
            GMAIL_PLUGIN_ID,
            GMAIL_PLUGIN_VERSION,
            GMAIL_READ_CAPABILITY_NAME,
        )
        self._binding.bind(
            GMAIL_PLUGIN_ID,
            GMAIL_PLUGIN_VERSION,
            GMAIL_READ_CAPABILITY_NAME,
        )
        self._activation.activate(
            GMAIL_PLUGIN_ID,
            GMAIL_PLUGIN_VERSION,
            GMAIL_READ_CAPABILITY_NAME,
        )


class ChatPluginActionCompletionService:
    """Turn a decided D45 Plugin result into one persisted safe Chat reply."""

    def __init__(
        self,
        *,
        conversation_service: ConversationService,
        binding_store: ChatPluginActionBindingStore,
        calendar_composer: CalendarChatCompletionComposer | None = None,
        gmail_composer: GmailChatCompletionComposer | None = None,
        cross_connector_context_store: CrossConnectorContextStore | None = None,
    ) -> None:
        self._conversation_service = conversation_service
        self._binding_store = binding_store
        self._calendar_composer = (
            calendar_composer or CalendarChatCompletionComposer()
        )
        self._gmail_composer = gmail_composer or GmailChatCompletionComposer()
        self._cross_connector_context_store = cross_connector_context_store

    def complete(
        self,
        approval_id: str,
        outcome: ExecutionApprovalDecisionOutcome,
    ) -> ChatPluginActionCompletion | None:
        if not isinstance(outcome, ExecutionApprovalDecisionOutcome):
            raise TypeError(
                "outcome must be an ExecutionApprovalDecisionOutcome."
            )
        if outcome.approval_id != approval_id:
            raise ValueError("approval outcome does not match approval_id.")

        binding = self._binding_store.consume(approval_id)
        if binding is None:
            return None

        if outcome.decision == "denied":
            if binding.gmail_query is not None:
                reply = self._gmail_composer.DENIED_REPLY
            elif binding.calendar_window is not None:
                reply = self._calendar_composer.DENIED_REPLY
            else:
                reply = (
                    "ยกเลิกการเรียก GitHub connector "
                    "ตามการตัดสินใจของเจ้าของแล้วครับ"
                )
        else:
            reply = self._reply_for_approved(binding, outcome)

        persisted_reply = reply
        if outcome.decision == "approved":
            if binding.gmail_query is not None:
                persisted_reply = self._gmail_composer.HISTORY_SAFE_REPLY
            elif binding.calendar_window is not None:
                persisted_reply = self._calendar_composer.HISTORY_SAFE_REPLY

        self._conversation_service.complete_turn(
            str(binding.conversation_id),
            persisted_reply,
        )
        self._capture_cross_connector_context(binding, outcome)
        return ChatPluginActionCompletion(
            conversation_id=binding.conversation_id,
            reply=reply,
        )

    def _capture_cross_connector_context(
        self,
        binding: ChatPluginActionBinding,
        outcome: ExecutionApprovalDecisionOutcome,
    ) -> None:
        store = self._cross_connector_context_store
        if store is None or outcome.decision != "approved":
            return
        try:
            if binding.gmail_query is not None:
                messages = self._gmail_composer.context_messages_for_approved(
                    binding,
                    outcome,
                )
                if messages is not None:
                    store.capture_gmail(
                        binding.conversation_id,
                        messages,
                    )
                return
            if binding.calendar_window is not None:
                events = self._calendar_composer.context_events_for_approved(
                    binding,
                    outcome,
                )
                if events is not None:
                    store.capture_calendar(
                        binding.conversation_id,
                        events,
                    )
        except (TypeError, ValueError, RuntimeError):
            return

    def _reply_for_approved(
        self,
        binding: ChatPluginActionBinding,
        outcome: ExecutionApprovalDecisionOutcome,
    ) -> str:
        if binding.gmail_query is not None:
            return self._gmail_composer.reply_for_approved(
                binding,
                outcome,
            )
        if binding.calendar_window is not None:
            return self._calendar_composer.reply_for_approved(
                binding,
                outcome,
            )

        execution = outcome.execution
        result = execution.result
        if (
            execution.status != "completed"
            or result is None
            or result.status != "succeeded"
        ):
            return (
                "ไม่สามารถอ่านข้อมูลสดจาก GitHub "
                "ได้ในครั้งนี้ครับ"
            )

        payload = self._validated_payload(
            result.output,
            binding.repository_reference,
        )
        if payload is None:
            return (
                "ไม่สามารถอ่านข้อมูลสดจาก GitHub "
                "ได้ในครั้งนี้ครับ"
            )

        description = self._display_nullable(payload["description"])
        language = self._display_nullable(payload["language"])
        license_id = self._display_nullable(payload["license"])
        return "\n".join(
            (
                "ตรวจข้อมูลสดจาก GitHub ให้แล้วครับ",
                f"Repository: {self._one_line(payload['full_name'])}",
                f"Description: {description}",
                f"Language: {language}",
                "Default branch: "
                f"{self._one_line(payload['default_branch'])}",
                "Stars: "
                f"{payload['stargazers_count']:,}",
                "Forks: "
                f"{payload['forks_count']:,}",
                "Open issues: "
                f"{payload['open_issues_count']:,}",
                f"License: {license_id}",
                f"Updated: {self._one_line(payload['updated_at'])}",
                f"URL: {self._one_line(payload['html_url'])}",
            )
        )

    @classmethod
    def _validated_payload(
        cls,
        output: Mapping[str, object],
        repository_reference: str,
    ) -> dict[str, object] | None:
        if not isinstance(output, Mapping) or set(output) != {"content"}:
            return None
        content = output.get("content")
        if not isinstance(content, str):
            return None
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        if set(payload) != _REQUIRED_RESULT_KEYS:
            return None

        full_name = payload.get("full_name")
        if (
            not isinstance(full_name, str)
            or full_name.casefold() != repository_reference.casefold()
        ):
            return None
        if payload.get("visibility") != "public":
            return None
        if payload.get("html_url") != f"https://github.com/{full_name}":
            return None

        for key in ("archived", "fork"):
            if type(payload.get(key)) is not bool:
                return None
        for key in (
            "stargazers_count",
            "forks_count",
            "open_issues_count",
        ):
            value = payload.get(key)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                return None
        for key in (
            "full_name",
            "default_branch",
            "updated_at",
            "html_url",
        ):
            value = payload.get(key)
            if not isinstance(value, str) or not value:
                return None
        for key in ("description", "language", "license"):
            value = payload.get(key)
            if value is not None and not isinstance(value, str):
                return None

        return payload

    @staticmethod
    def _one_line(value: object) -> str:
        if not isinstance(value, str):
            return "—"
        normalized = " ".join(value.split())
        return normalized or "—"

    @classmethod
    def _display_nullable(cls, value: object) -> str:
        if value is None:
            return "—"
        return cls._one_line(value)
