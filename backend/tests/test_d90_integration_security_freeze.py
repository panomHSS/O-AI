from __future__ import annotations

import inspect
from pathlib import Path
from typing import get_args

from app.contracts.automation_delivery import AutomationDeliveryStatus
from app.services.chat_gmail import GmailChatIntentRouter
from app.services.connector_error_semantics import project_safe_connector_error
from app.services.gmail_send_approval import (
    GmailSendApprovalService,
    GmailSendApprovalStore,
)
from app.services.gmail_send_execution import GmailSendExecutionClaimStore


BACKEND = Path(__file__).resolve().parents[1]


def _source(relative: str) -> str:
    return (BACKEND / relative).read_text(
        encoding="utf-8-sig"
    ).replace("\r\n", "\n")


def test_d90_d81_runtime_truth_remains_non_authoritative() -> None:
    diagnostics = _source("app/services/runtime_diagnostics.py")
    api = _source("app/api/v1/diagnostics.py")
    combined = api + "\n" + diagnostics

    for marker in (
        "write_chat_routable=False",
        "execution_authority=False",
        "local_reminder_chat_routable=False",
        "connector_actions_implemented=False",
        "ai_actions_implemented=False",
    ):
        assert marker in diagnostics

    for forbidden in (
        "CredentialAccessBroker",
        "AIRuntime",
        "ToolRuntime",
        "ModuleRuntime",
        ".execute(",
    ):
        assert forbidden not in combined


def test_d90_d82_connector_error_projection_is_exact_and_fail_closed() -> None:
    source = inspect.getsource(project_safe_connector_error)

    for marker in (
        "_EXPECTED_EXCEPTION_TYPE_BY_SUBJECT",
        "type(error) is not expected_type",
        "safe_connector_codes_for_subject",
        "return None",
    ):
        assert marker in source

    assert project_safe_connector_error(
        plugin_id="unknown.plugin",
        plugin_version="0",
        capability_name="unknown",
        error=RuntimeError("secret provider detail"),
    ) is None


def test_d90_d83_d84_calendar_chat_has_no_direct_external_authority() -> None:
    bridge = _source("app/services/chat_calendar_write.py")
    ux = _source("app/services/calendar_write_chat_ux.py")
    combined = bridge + "\n" + ux

    for forbidden in (
        "CredentialAccessBroker",
        "GoogleCalendarWriteClient",
        "GoogleCalendarPlugin",
        "AIRuntime",
        "AutomationApprovalService",
        "GmailSendExecutionService",
        "urllib.request",
        "requests.",
        "httpx.",
    ):
        assert forbidden not in combined


def test_d90_d85_gmail_read_chat_cannot_become_send_lane() -> None:
    router = GmailChatIntentRouter()
    for request in (
        "send email",
        "send mail",
        "ส่งอีเมล",
        "ส่งเมล",
        "reply",
        "forward",
        "draft",
        "compose",
    ):
        assert router.classify(request).status == "invalid"

    source = _source("app/services/chat_gmail.py")
    for forbidden in (
        "GmailSendExecutionService",
        "GmailSendApprovalService",
        "gmail-send-executions",
        "GMAIL_SEND_ADAPTER_ID",
        "gmail.send",
    ):
        assert forbidden not in source


def test_d90_d86_send_contract_is_data_only() -> None:
    source = _source("app/contracts/gmail_send.py")

    for forbidden in (
        "CredentialAccessBroker",
        "GmailSendExecutionService",
        "GmailSendApprovalService",
        "GmailSendClient",
        "urllib.request",
        "requests.",
        "httpx.",
    ):
        assert forbidden not in source


def test_d90_d87_approval_is_not_execution_authority() -> None:
    for cls in (GmailSendApprovalStore, GmailSendApprovalService):
        for forbidden in (
            "execute",
            "send",
            "claim",
            "retry",
            "resend",
        ):
            assert not hasattr(cls, forbidden)

    source = _source("app/services/gmail_send_approval.py")
    for forbidden in (
        "GmailSendExecutionService",
        "GmailSendClient",
        "CredentialAccessBroker",
        ".claim(",
        ".execute(",
        "urllib.request",
    ):
        assert forbidden not in source


def test_d90_d88_execution_remains_authorize_claim_execute_single_shot() -> None:
    source = _source("app/services/gmail_send_execution_service.py")

    order = (
        source.index("self._approval_store.get_approved("),
        source.index("self._guard.authorize("),
        source.index("self._execution_store.claim("),
        source.index("self._runtime.execute("),
        source.index("self._execution_store.complete("),
    )
    assert order == tuple(sorted(order))

    for forbidden in (
        "retry(",
        "resend(",
        "release(",
        "unclaim(",
        "reopen(",
    ):
        assert forbidden not in source

    for forbidden in ("retry", "reset", "release", "unclaim", "reopen"):
        assert not hasattr(GmailSendExecutionClaimStore, forbidden)


def test_d90_d88_transport_and_scope_remain_bounded() -> None:
    connector = _source("app/connectors/gmail_send.py")
    execution_contract = _source("app/contracts/gmail_send_execution.py")
    gmail_read_contract = _source("app/contracts/gmail.py")
    all_source = connector + "\n" + execution_contract + "\n" + gmail_read_contract

    assert "gmail/v1/users/me/messages/send" in connector
    assert 'method="POST"' in connector
    assert "urllib.request.ProxyHandler({})" in connector
    assert "_NoRedirectHandler" in connector
    assert "gmail.readonly" in gmail_read_contract
    assert "gmail.send" in execution_contract

    for forbidden in (
        "gmail.modify",
        "gmail.compose",
        "https://mail.google.com/",
        "for attempt",
        "sleep(",
    ):
        assert forbidden not in all_source


def test_d90_d89_delivery_status_and_terminal_query_are_layer_locked() -> None:
    assert set(get_args(AutomationDeliveryStatus)) == {
        "delivered",
        "missed",
        "indeterminate",
    }

    repository = _source("app/repositories/automations.py")
    delivery = _source("app/services/automation_delivery.py")

    for marker in (
        "def list_terminal_runs_newest(",
        "AutomationRunRecord.status.in_(",
        '("delivered", "missed", "indeterminate")',
    ):
        assert marker in repository

    for marker in (
        "list_terminal_runs_newest(",
        "AutomationDeliveryView(",
        "status=run.status",
        "message=definition.message",
    ):
        assert marker in delivery


def test_d90_d89_automation_has_zero_cross_authority_bridge() -> None:
    paths = (
        "app/api/v1/automations.py",
        "app/services/automation_delivery.py",
        "app/services/automation_run_service.py",
        "app/services/automation_scheduler.py",
    )
    combined = "\n".join(_source(path) for path in paths)

    for forbidden in (
        "GmailSendExecutionService",
        "GmailSendApprovalService",
        "GoogleCalendarWriteClient",
        "CalendarCreateExecutionService",
        "CalendarUpdateDeleteExecutionService",
        "CredentialAccessBroker",
        "AIRuntime",
        "ToolRuntime",
        "ModuleRuntime",
        "CrossConnectorContextStore",
    ):
        assert forbidden not in combined


def test_d90_private_send_capability_stays_outside_generic_policy() -> None:
    dependencies = _source("app/api/dependencies.py")
    policy = _source("app/services/capability_permission_policy.py")

    for marker in (
        "get_gmail_send_private_registry",
        "get_gmail_send_private_permission_policy",
        "get_gmail_send_private_guard",
        "get_gmail_send_private_runtime",
        "get_gmail_send_execution_service",
    ):
        assert marker in dependencies

    assert "exec.gmail.send_message" not in policy
    assert "module.gmail.send_message" not in policy


def test_d90_composition_root_wiring_does_not_merge_authority_domains() -> None:
    dependencies = _source("app/api/dependencies.py")

    for marker in (
        "get_automation_approval_service",
        "get_automation_delivery_service",
        "get_calendar_write_chat_service",
        "get_gmail_send_execution_service",
    ):
        assert marker in dependencies

    automation_service = _source("app/services/automation_delivery.py")
    calendar_bridge = _source("app/services/chat_calendar_write.py")
    gmail_send = _source("app/services/gmail_send_execution_service.py")

    assert "GmailSendExecutionService" not in automation_service
    assert "AutomationApprovalService" not in calendar_bridge
    assert "AutomationApprovalService" not in gmail_send
