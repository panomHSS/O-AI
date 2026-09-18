from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


def read_backend(relative: str) -> str:
    return (BACKEND / relative).read_text(encoding="utf-8-sig")


def read_frontend(relative: str) -> str:
    return (FRONTEND / relative).read_text(encoding="utf-8-sig")


def test_d89_delivery_service_is_read_only_and_cross_authority_free() -> None:
    source = read_backend("app/services/automation_delivery.py")

    for forbidden in (
        "AutomationRunService",
        "AIRuntime",
        "ToolRuntime",
        "ModuleRuntime",
        "ExecutionPlanner",
        "ExecutionGuard",
        "CredentialAccessBroker",
        "ConversationService",
        "GmailPlugin",
        "GoogleCalendarPlugin",
        "GmailSend",
        "CalendarWrite",
        ".commit(",
        ".rollback(",
        "add_run(",
        "transition_claimed_run(",
        "advance_if_due(",
    ):
        assert forbidden not in source


def test_d89_delivery_api_is_projection_not_execution() -> None:
    source = read_backend("app/api/v1/automations.py")
    delivery_start = source.index('"/automation-deliveries"')
    delivery_section = source[delivery_start:]

    assert "AutomationDeliveryService" in delivery_section
    assert "service.list_deliveries(limit=limit)" in delivery_section

    for forbidden in (
        "AutomationRunService",
        "AIRuntime",
        "ToolRuntime",
        "ModuleRuntime",
        "CredentialAccessBroker",
        "GmailPlugin",
        "GoogleCalendarPlugin",
        "send(",
        "execute(",
        "retry",
    ):
        assert forbidden not in delivery_section


def test_delivery_tray_has_presentation_authority_only() -> None:
    source = read_frontend(
        "components/automations/reminder-delivery-tray.tsx"
    )

    assert "getAutomationDeliveries()" in source
    assert "run_id" in source
    assert "localStorage" in source
    assert "not backend" in source
    assert "acknowledgement" in source

    for forbidden in (
        "createAutomationProposal",
        "approveAutomationProposal",
        "denyAutomationProposal",
        "cancelAutomation",
        "sendChatMessage",
        "gmail",
        "calendar",
        "Notification.requestPermission",
        "navigator.serviceWorker",
        "Run Again",
        "Retry",
    ):
        assert forbidden not in source


def test_automation_center_does_not_gain_delivery_execution_authority() -> None:
    source = read_frontend("app/automations/page.tsx")

    for forbidden in (
        "getAutomationDeliveries",
        "setInterval(",
        "sendChatMessage",
        "gmail-send-executions",
        "calendar-write-executions",
        "execution-approvals",
        "Run Again",
        "Retry",
    ):
        assert forbidden not in source


def test_d81_truth_is_additive_and_never_an_execution_grant() -> None:
    schema = read_backend("app/schemas/diagnostics.py")
    service = read_backend("app/services/runtime_diagnostics.py")

    assert 'contract_version: Literal["1"] = "1"' in schema
    assert (
        "local_reminder_delivery_ui_implemented: Literal[True] = True"
        in schema
    )
    assert "local_reminder_chat_routable: Literal[False] = False" in schema
    assert "connector_actions_implemented: Literal[False] = False" in schema
    assert "ai_actions_implemented: Literal[False] = False" in schema
    assert "execution_authority: Literal[False] = False" in schema

    assert "local_reminder_delivery_ui_implemented=True" in service
    assert "local_reminder_chat_routable=False" in service
    assert "connector_actions_implemented=False" in service
    assert "ai_actions_implemented=False" in service
    assert "execution_authority=False" in service


def test_d89_automation_files_do_not_reference_connector_secrets() -> None:
    sources = "\n".join(
        (
            read_backend("app/contracts/automation_delivery.py"),
            read_backend("app/services/automation_delivery.py"),
            read_frontend("types/automations.ts"),
            read_frontend(
                "components/automations/reminder-delivery-tray.tsx"
            ),
        )
    ).lower()

    for forbidden in (
        "access_token",
        "refresh_token",
        "client_secret",
        "oauth_token",
        "credential_secret",
        "authorization: bearer",
    ):
        assert forbidden not in sources
