from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"


def read(relative: str) -> str:
    return (FRONTEND / relative).read_text(encoding="utf-8-sig")


def test_delivery_tray_uses_fixed_bounded_read_polling() -> None:
    component = read("components/automations/reminder-delivery-tray.tsx")
    client = read("lib/api-client.ts")

    assert "const POLL_INTERVAL_MS = 30_000;" in component
    assert "const DELIVERY_FETCH_LIMIT = 20;" in component
    assert "const MAX_VISIBLE_DELIVERIES = 5;" in component
    assert "getAutomationDeliveries()" in component
    assert "window.setInterval(poll, POLL_INTERVAL_MS)" in component
    assert '"/automation-deliveries?limit=20"' in client


def test_delivery_tray_supports_only_terminal_delivery_statuses() -> None:
    types = read("types/automations.ts")
    component = read("components/automations/reminder-delivery-tray.tsx")

    assert '"delivered" | "missed" | "indeterminate"' in types
    delivery_type = types[
        types.index("export type AutomationDeliveryStatus"):
        types.index("export interface AutomationDelivery")
    ]
    assert '"claimed"' not in delivery_type
    assert 'status === "delivered"' in component
    assert 'status === "missed"' in component
    assert "Reminder state indeterminate" in component


def test_seen_dedupe_stores_only_bounded_run_ids() -> None:
    component = read("components/automations/reminder-delivery-tray.tsx")

    assert 'SEEN_STORAGE_KEY = "oai.automationSeenRunIds.v1"' in component
    assert "const MAX_SEEN_RUN_IDS = 100;" in component
    assert "item.run_id" in component
    assert "JSON.stringify(values.slice(-MAX_SEEN_RUN_IDS))" in component

    storage_write = component[
        component.index("function writeSeenRunIds"):
        component.index("function statusTitle")
    ]
    assert "message" not in storage_write
    assert "scheduled_for" not in storage_write
    assert "automation_id" not in storage_write


def test_delivery_tray_truthfully_explains_terminal_states() -> None:
    component = read("components/automations/reminder-delivery-tray.tsx")

    assert "does not mean the owner acknowledged it" in component
    assert "No catch-up run was executed." in component
    assert "No automatic retry is allowed." in component
    assert "not backend" in component
    assert "acknowledgement" in component


def test_delivery_tray_has_no_mutation_or_execution_authority() -> None:
    component = read("components/automations/reminder-delivery-tray.tsx")

    for forbidden in (
        "createAutomationProposal",
        "approveAutomationProposal",
        "denyAutomationProposal",
        "cancelAutomation",
        "sendChatMessage",
        "gmail",
        "calendar",
        "AIRuntime",
        "ToolRuntime",
        "ModuleRuntime",
        "CredentialAccessBroker",
        "Notification.requestPermission",
        "navigator.serviceWorker",
        "fetch(",
        "POST",
        "PATCH",
        "PUT",
        "DELETE",
    ):
        assert forbidden not in component


def test_delivery_client_is_fixed_read_only_request() -> None:
    client = read("lib/api-client.ts")
    start = client.index("export function getAutomationDeliveries")
    section = client[start:]

    assert '"/automation-deliveries?limit=20"' in section
    assert 'method: "GET"' in section
    assert '"X-OAI-Local-Request": "1"' in section
    for forbidden in (
        'method: "POST"',
        'method: "PATCH"',
        'method: "PUT"',
        'method: "DELETE"',
        "body:",
    ):
        assert forbidden not in section


def test_global_layout_mounts_delivery_tray() -> None:
    layout = read("app/layout.tsx")
    assert 'import { ReminderDeliveryTray }' in layout
    assert "<ReminderDeliveryTray />" in layout
