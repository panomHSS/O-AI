from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.adapters.gmail_send_module import GmailSendModuleAdapter
from app.api.dependencies import get_gmail_send_execution_service
from app.api.v1.gmail_send_executions import router
from app.connectors.gmail_send import (
    GMAIL_SEND_ERROR_INDETERMINATE,
    GmailSendConnectorError,
    GmailSendProviderResult,
)
from app.contracts.capability_permission import ExecutableCapabilityPermission
from app.contracts.credential import CredentialProfile
from app.contracts.gmail import (
    GMAIL_CREDENTIAL_AUTH_SCHEME,
    GMAIL_CREDENTIAL_PROVIDER_ID,
    GMAIL_PLUGIN_ID,
    GMAIL_PLUGIN_VERSION,
)
from app.contracts.gmail_send import (
    GMAIL_SEND_OPERATION,
    GmailSendDraft,
    GmailSendRequest,
)
from app.contracts.gmail_send_execution import (
    GMAIL_SEND_ADAPTER_ID,
    GMAIL_SEND_CAPABILITY_ID,
    GMAIL_SEND_CAPABILITY_NAME,
    GMAIL_SEND_CREDENTIAL_PROFILE_ID,
    GMAIL_SEND_CREDENTIAL_SCOPE,
    GMAIL_SEND_CREDENTIAL_SECRET_REF,
)
from app.services.adapter_registry import AdapterRegistry
from app.services.capability_permission_policy import CapabilityPermissionPolicy
from app.services.credential_access_broker import (
    CredentialAccessBroker,
    StaticCredentialSecretSource,
)
from app.services.credential_profile_catalog import CredentialProfileCatalog
from app.services.execution_guard import ExecutionGuard
from app.services.gmail_send_approval import (
    GmailSendApprovalService,
    GmailSendApprovalStore,
)
from app.services.gmail_send_execution import GmailSendExecutionClaimStore
from app.services.gmail_send_execution_service import GmailSendExecutionService
from app.services.module_runtime import ModuleRuntime


HEADER = {"X-OAI-Local-Request": "1"}
NOW = datetime(2026, 9, 18, 12, 0, tzinfo=timezone.utc)


class FakeClient:
    def __init__(self, *, error=None) -> None:
        self.error = error
        self.calls = 0

    def send_message(self, access_token, *, sender, request):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return GmailSendProviderResult(message_id="gmail-message-id-api")


def build_service(provider):
    approval_store = GmailSendApprovalStore(clock=lambda: NOW)
    execution_store = GmailSendExecutionClaimStore(clock=lambda: NOW)
    profile = CredentialProfile(
        profile_id=GMAIL_SEND_CREDENTIAL_PROFILE_ID,
        plugin_id=GMAIL_PLUGIN_ID,
        plugin_version=GMAIL_PLUGIN_VERSION,
        capability_name=GMAIL_SEND_CAPABILITY_NAME,
        provider_id=GMAIL_CREDENTIAL_PROVIDER_ID,
        auth_scheme=GMAIL_CREDENTIAL_AUTH_SCHEME,
        required_scopes=(GMAIL_SEND_CREDENTIAL_SCOPE,),
        secret_ref=GMAIL_SEND_CREDENTIAL_SECRET_REF,
    )
    broker = CredentialAccessBroker(
        profile_catalog=CredentialProfileCatalog((profile,)),
        secret_source=StaticCredentialSecretSource(
            {
                GMAIL_SEND_CREDENTIAL_SECRET_REF: SecretStr(
                    "api-send-access-token"
                )
            }
        ),
    )
    adapter = GmailSendModuleAdapter(
        credential_broker=broker,
        client=provider,
    )
    registry = AdapterRegistry((adapter,))
    policy = CapabilityPermissionPolicy(
        registry=registry,
        permissions=(
            ExecutableCapabilityPermission(
                capability_id=GMAIL_SEND_CAPABILITY_ID,
                target_kind="module",
                adapter_id=GMAIL_SEND_ADAPTER_ID,
                operation=GMAIL_SEND_OPERATION,
                effect="external_side_effect",
                data_class="owner_data",
                owner_approval_required=True,
            ),
        ),
    )
    service = GmailSendExecutionService(
        approval_store=approval_store,
        execution_store=execution_store,
        guard=ExecutionGuard(
            registry=registry,
            permission_policy=policy,
        ),
        runtime=ModuleRuntime(registry=registry),
        sender="owner@example.com",
        enabled=True,
    )
    return service, approval_store, execution_store


def approve(store):
    approvals = GmailSendApprovalService(store=store)
    proposal = approvals.propose(
        GmailSendRequest(
            message=GmailSendDraft(
                recipient="recipient@example.com",
                subject="Owner-approved subject",
                body="Owner-approved body\n",
            )
        )
    ).proposal
    outcome = approvals.approve(
        proposal.approval_id,
        proposal.send_digest,
    )
    assert outcome.approved is not None
    return outcome.approved


def client_for(service):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[
        get_gmail_send_execution_service
    ] = lambda: service
    return TestClient(app)


def test_local_marker_required_and_extra_fields_forbidden() -> None:
    provider = FakeClient()
    service, approval_store, execution_store = build_service(provider)
    approved = approve(approval_store)
    client = client_for(service)
    payload = {
        "approval_id": approved.approval_id,
        "send_digest": approved.send_digest,
    }

    missing = client.post(
        "/api/v1/gmail-send-executions",
        json=payload,
    )
    assert missing.status_code == 403
    assert execution_store.record_count == 0
    assert provider.calls == 0

    for field in (
        "recipient",
        "subject",
        "body",
        "from",
        "sender",
        "token",
        "credential",
        "retry",
        "force",
        "provider",
        "message_id",
    ):
        response = client.post(
            "/api/v1/gmail-send-executions",
            headers=HEADER,
            json={**payload, field: "forbidden"},
        )
        assert response.status_code == 422
    assert execution_store.record_count == 0
    assert provider.calls == 0


def test_success_once_replay_blocked_and_no_sensitive_echo() -> None:
    provider = FakeClient()
    service, approval_store, _ = build_service(provider)
    approved = approve(approval_store)
    client = client_for(service)
    payload = {
        "approval_id": approved.approval_id,
        "send_digest": approved.send_digest,
    }

    first = client.post(
        "/api/v1/gmail-send-executions",
        headers=HEADER,
        json=payload,
    )
    second = client.post(
        "/api/v1/gmail-send-executions",
        headers=HEADER,
        json=payload,
    )

    assert first.status_code == 200, first.text
    assert first.json()["data"] == {
        "approval_id": approved.approval_id,
        "send_digest": approved.send_digest,
        "status": "succeeded",
        "reason_code": "gmail_send_succeeded",
        "provider_attempted": True,
        "message_id": "gmail-message-id-api",
    }
    assert second.status_code == 409
    assert second.json()["detail"] == (
        "gmail_send_execution_already_claimed"
    )
    assert provider.calls == 1
    assert "api-send-access-token" not in first.text
    assert "Owner-approved body" not in first.text
    assert "recipient@example.com" not in first.text


def test_wrong_digest_and_not_approved_never_reach_provider() -> None:
    provider = FakeClient()
    service, approval_store, execution_store = build_service(provider)
    approved = approve(approval_store)
    client = client_for(service)
    wrong = "0" * 64
    if wrong == approved.send_digest:
        wrong = "f" * 64

    response = client.post(
        "/api/v1/gmail-send-executions",
        headers=HEADER,
        json={
            "approval_id": approved.approval_id,
            "send_digest": wrong,
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"] == (
        "gmail_send_execution_digest_mismatch"
    )
    assert execution_store.record_count == 0

    approvals = GmailSendApprovalService(store=approval_store)
    pending = approvals.propose(
        GmailSendRequest(
            message=GmailSendDraft(
                recipient="pending@example.com",
                subject="Pending",
                body="Pending body",
            )
        )
    ).proposal
    response = client.post(
        "/api/v1/gmail-send-executions",
        headers=HEADER,
        json={
            "approval_id": pending.approval_id,
            "send_digest": pending.send_digest,
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"] == (
        "gmail_send_execution_not_approved"
    )
    assert provider.calls == 0


def test_indeterminate_is_terminal_and_never_retried() -> None:
    provider = FakeClient(
        error=GmailSendConnectorError(
            GMAIL_SEND_ERROR_INDETERMINATE,
            provider_attempted=True,
            indeterminate=True,
        )
    )
    service, approval_store, _ = build_service(provider)
    approved = approve(approval_store)
    client = client_for(service)
    payload = {
        "approval_id": approved.approval_id,
        "send_digest": approved.send_digest,
    }

    first = client.post(
        "/api/v1/gmail-send-executions",
        headers=HEADER,
        json=payload,
    )
    second = client.post(
        "/api/v1/gmail-send-executions",
        headers=HEADER,
        json=payload,
    )

    assert first.status_code == 200
    assert first.json()["data"]["status"] == "indeterminate"
    assert first.json()["data"]["provider_attempted"] is True
    assert first.json()["data"]["message_id"] is None
    assert second.status_code == 409
    assert provider.calls == 1
