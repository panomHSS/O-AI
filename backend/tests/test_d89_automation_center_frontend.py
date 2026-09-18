from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"


def read(relative: str) -> str:
    return (FRONTEND / relative).read_text(encoding="utf-8-sig")


def test_automation_center_routes_only_through_d79_owner_apis() -> None:
    client = read("lib/api-client.ts")
    start = client.index("export function getAutomationSettings")
    automation_section = client[start:]
    for marker in (
        '"/automation-settings"',
        '"/automations"',
        '"/automation-proposals"',
        "/approve`",
        "/deny`",
        "/cancel`",
    ):
        assert marker in automation_section

    for forbidden in (
        "gmail-send-executions",
        "calendar-write-executions",
        "execution-approvals",
        '"/chat"',
        "AIRuntime",
        "ModuleRuntime",
        "ToolRuntime",
        "CredentialAccessBroker",
    ):
        assert forbidden not in automation_section


def test_automation_center_has_exact_preview_before_structured_decision() -> None:
    page = read("app/automations/page.tsx")
    assert "exact server preview" in page.lower()
    assert "definition.definition_digest" in page
    assert "approveAutomationProposal(" in page
    assert "denyAutomationProposal(" in page
    assert "createAutomationProposal(payload)" in page
    assert "Creating this proposal does not activate the reminder." in page


def test_automation_center_once_timezone_mismatch_fails_closed() -> None:
    page = read("app/automations/page.tsx")
    assert "onceTimeZoneMatches" in page
    assert "localTimeZone === settings.owner_timezone" in page
    assert "One-time creation is blocked" in page
    assert 'type="datetime-local"' in page
    assert "new Date(onceLocal).toISOString()" in page


def test_automation_center_has_no_delivery_polling_or_run_again() -> None:
    page = read("app/automations/page.tsx")
    for forbidden in (
        "setInterval(",
        "setTimeout(",
        "automation-deliveries",
        "Run Again",
        "Retry",
        "navigator.serviceWorker",
        "Notification.requestPermission",
        "localStorage",
        "dangerouslySetInnerHTML",
    ):
        assert forbidden not in page


def test_cancel_is_only_rendered_for_approved_definition() -> None:
    page = read("app/automations/page.tsx")
    assert 'definition.status === "approved"' in page
    assert "cancelAutomation(definition.automation_id)" in page
    assert "Cancellation is terminal" in page
    assert "re-enabling requires a new proposal" in page.lower()


def test_navigation_exposes_automation_center() -> None:
    layout = read("app/layout.tsx")
    assert 'href="/automations"' in layout
    assert ">Automations</Link>" in layout


def test_automation_types_do_not_contain_execution_connector_authority() -> None:
    types = read("types/automations.ts")
    for forbidden in (
        "gmail",
        "calendar",
        "credential",
        "adapter_id",
        "capability_id",
        "execution",
        "retry",
        "resend",
    ):
        assert forbidden not in types.lower()
