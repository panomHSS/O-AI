from __future__ import annotations

import inspect
from pathlib import Path

from app.core.config import Settings
from app.schemas.gmail_send_executions import (
    GmailSendExecutionRequest,
    GmailSendExecutionResponse,
)
from app.services.gmail_send_approval import (
    GmailSendApprovalService,
    GmailSendApprovalStore,
)


BACKEND = Path(__file__).resolve().parents[1]
APP = BACKEND / "app"


def production_sources() -> dict[str, str]:
    return {
        str(path.relative_to(BACKEND)).replace("\\", "/"):
            path.read_text(encoding="utf-8-sig")
        for path in APP.rglob("*.py")
    }


def test_owner_execution_transport_has_exact_bounded_surface() -> None:
    assert set(GmailSendExecutionRequest.model_fields) == {
        "approval_id",
        "send_digest",
    }
    assert set(GmailSendExecutionResponse.model_fields) == {
        "approval_id",
        "send_digest",
        "status",
        "reason_code",
        "provider_attempted",
        "message_id",
    }

    request_fields = set(GmailSendExecutionRequest.model_fields)
    for forbidden_field in (
        "recipient",
        "subject",
        "body",
        "sender",
        "credential",
        "access_token",
        "oauth_scope",
        "retry",
        "resend",
        "force",
        "cc",
        "bcc",
        "html",
        "attachments",
    ):
        assert forbidden_field not in request_fields

    request_source = (
        APP / "schemas/gmail_send_executions.py"
    ).read_text(encoding="utf-8-sig").lower()
    for forbidden_marker in (
        "\n    recipient:",
        "\n    subject:",
        "\n    body:",
        "\n    sender:",
        "\n    credential:",
        "\n    access_token:",
        "\n    oauth_scope:",
        "\n    retry:",
        "\n    resend:",
        "\n    force:",
        "\n    cc:",
        "\n    bcc:",
        "\n    html:",
        "\n    attachments:",
    ):
        assert forbidden_marker not in request_source


def test_deployment_gates_default_fail_closed() -> None:
    assert (
        Settings.model_fields["oai_gmail_send_enabled"].default
        is False
    )
    assert (
        Settings.model_fields["oai_gmail_send_from_address"].default
        is None
    )


def test_gmail_send_scope_and_provider_endpoint_are_confined() -> None:
    sources = production_sources()

    send_scope = "https://www.googleapis.com/auth/gmail.send"
    scope_offenders = sorted(
        path for path, source in sources.items()
        if send_scope in source
    )
    assert scope_offenders == [
        "app/contracts/gmail_send_execution.py"
    ]

    endpoint = (
        "https://gmail.googleapis.com/"
        "gmail/v1/users/me/messages/send"
    )
    endpoint_offenders = sorted(
        path for path, source in sources.items()
        if endpoint in source
    )
    assert endpoint_offenders == ["app/connectors/gmail_send.py"]

    for forbidden_scope in (
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://mail.google.com/",
    ):
        assert not any(
            forbidden_scope in source for source in sources.values()
        )


def test_gmail_read_lane_never_acquires_send_scope() -> None:
    source = (
        APP / "api/v1/gmail_oauth.py"
    ).read_text(encoding="utf-8-sig")
    assert "gmail.send" not in source
    assert "gmail_send_executions" not in source
    assert "GmailSendExecutionService" not in source


def test_d87_approval_remains_non_execution_authority() -> None:
    assert not hasattr(GmailSendApprovalStore, "claim_approved")
    assert not hasattr(GmailSendApprovalStore, "execute")
    assert not hasattr(GmailSendApprovalStore, "send")
    assert not hasattr(GmailSendApprovalService, "execute")
    assert not hasattr(GmailSendApprovalService, "send")


def test_d88_execution_order_is_authorize_then_claim_then_runtime() -> None:
    source = (
        APP / "services/gmail_send_execution_service.py"
    ).read_text(encoding="utf-8-sig")

    get_approved = source.index(
        "self._approval_store.get_approved("
    )
    authorize = source.index("self._guard.authorize(")
    claim = source.index("self._execution_store.claim(")
    runtime = source.index("self._runtime.execute(")
    complete = source.index("self._execution_store.complete(")

    assert get_approved < authorize < claim < runtime < complete


def test_execution_claim_store_exposes_no_retry_reset_or_release() -> None:
    from app.services.gmail_send_execution import (
        GmailSendExecutionClaimStore,
    )

    for forbidden in (
        "retry",
        "reset",
        "release",
        "unclaim",
        "reopen",
    ):
        assert not hasattr(GmailSendExecutionClaimStore, forbidden)

    source = inspect.getsource(GmailSendExecutionClaimStore).lower()
    for forbidden_call in (
        "def retry",
        "def reset",
        "def release",
        "def unclaim",
        "def reopen",
    ):
        assert forbidden_call not in source


def test_owner_api_requires_local_marker_and_is_execution_only() -> None:
    source = (
        APP / "api/v1/gmail_send_executions.py"
    ).read_text(encoding="utf-8-sig")
    assert 'prefix="/gmail-send-executions"' in source
    assert "require_local_gmail_send_request_marker" in source
    assert "get_gmail_send_execution_service" in source

    for forbidden in (
        "GmailSendDraft",
        "GmailSendRequest(",
        "GmailSendApprovalService",
        "approve_gmail_send",
        "deny_gmail_send",
        "recipient=",
        "subject=",
        "body=",
        "retry",
        "resend",
        "force_send",
    ):
        assert forbidden not in source


def test_private_execution_wiring_does_not_enter_generic_catalog() -> None:
    dependencies = (
        APP / "api/dependencies.py"
    ).read_text(encoding="utf-8-sig")
    policy = (
        APP / "services/capability_permission_policy.py"
    ).read_text(encoding="utf-8-sig")

    for marker in (
        "get_gmail_send_private_registry",
        "get_gmail_send_private_permission_policy",
        "get_gmail_send_private_guard",
        "get_gmail_send_private_runtime",
        "get_gmail_send_execution_claim_store",
        "get_gmail_send_execution_service",
    ):
        assert marker in dependencies

    assert "exec.gmail.send_message" not in policy
    assert "module.gmail.send_message" not in policy


def test_chat_frontend_and_automation_gain_no_send_authority() -> None:
    sources = production_sources()
    forbidden_markers = (
        "GmailSendExecutionService",
        "get_gmail_send_execution_service",
        "gmail-send-executions",
        "GMAIL_SEND_ADAPTER_ID",
    )

    allowed = {
        "app/api/dependencies.py",
        "app/api/router.py",
        "app/api/v1/gmail_send_executions.py",
        "app/services/gmail_send_execution_service.py",
        "app/services/gmail_send_execution.py",
        "app/contracts/gmail_send_execution.py",
        "app/adapters/gmail_send_module.py",
    }

    offenders = []
    for path, source in sources.items():
        if path in allowed:
            continue
        lowered = path.lower()
        if (
            "chat" in lowered
            or "automation" in lowered
            or "frontend" in lowered
        ) and any(marker in source for marker in forbidden_markers):
            offenders.append(path)
    assert offenders == []


def test_runtime_truth_separates_backend_from_chat_authority() -> None:
    source = (
        APP / "services/runtime_diagnostics.py"
    ).read_text(encoding="utf-8-sig")
    assert "write_implemented=True" in source
    assert "write_chat_routable=False" in source
    assert "execution_authority=False" in source

    composer = (
        APP / "services/chat_runtime_capability.py"
    ).read_text(encoding="utf-8-sig")
    assert "Write/Send backend" in composer
    assert "Write/Send via Chat" in composer


def test_provider_connector_is_single_attempt_no_proxy_no_redirect() -> None:
    source = (
        APP / "connectors/gmail_send.py"
    ).read_text(encoding="utf-8-sig")

    assert source.count(
        "https://gmail.googleapis.com/"
        "gmail/v1/users/me/messages/send"
    ) == 1
    assert "method=\"POST\"" in source
    assert "urllib.request.ProxyHandler({})" in source
    assert "class _NoRedirectHandler" in source
    assert "for attempt" not in source
    assert "while " not in source

    for forbidden in (
        "requests.",
        "httpx.",
        "gmail.modify",
        "gmail.compose",
        "https://mail.google.com/",
        "drafts.send",
        "resend",
    ):
        assert forbidden not in source
