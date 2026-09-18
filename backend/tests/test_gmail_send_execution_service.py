from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from pydantic import SecretStr

from app.adapters.gmail_send_module import GmailSendModuleAdapter
from app.connectors.gmail_send import (
    GMAIL_SEND_ERROR_INDETERMINATE,
    GMAIL_SEND_ERROR_PROVIDER_REJECTED,
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
from app.services.credential_access_broker import CredentialAccessBroker
from app.services.credential_profile_catalog import CredentialProfileCatalog
from app.services.execution_guard import ExecutionGuard
from app.services.gmail_send_approval import (
    GmailSendApprovalService,
    GmailSendApprovalStore,
)
from app.services.gmail_send_execution import (
    GmailSendExecutionAlreadyClaimedError,
    GmailSendExecutionClaimStore,
)
from app.services.gmail_send_execution_service import (
    GmailSendExecutionAuthorizationError,
    GmailSendExecutionDisabledError,
    GmailSendExecutionDigestMismatchError,
    GmailSendExecutionNotApprovedError,
    GmailSendExecutionSenderNotConfiguredError,
    GmailSendExecutionService,
)
from app.services.module_runtime import ModuleRuntime


NOW = datetime(2026, 9, 18, 12, 0, tzinfo=timezone.utc)
SENDER = "owner@example.com"


class FakeClient:
    def __init__(self, *, error=None) -> None:
        self.error = error
        self.calls = 0
        self.lock = threading.Lock()

    def send_message(self, access_token, *, sender, request):
        with self.lock:
            self.calls += 1
        if self.error is not None:
            raise self.error
        return GmailSendProviderResult(message_id="gmail-message-id-1")


class ClaimCheckingSecretSource:
    def __init__(self, store, approval_id) -> None:
        self.store = store
        self.approval_id = approval_id
        self.calls = 0

    def resolve(self, secret_ref):
        self.calls += 1
        assert secret_ref == GMAIL_SEND_CREDENTIAL_SECRET_REF
        assert self.store.state(self.approval_id) == "claimed"
        return SecretStr("send-access-token")


class EmptySecretSource:
    def resolve(self, secret_ref):
        return None


def create_approved(store):
    approvals = GmailSendApprovalService(store=store)
    proposal = approvals.propose(
        GmailSendRequest(
            message=GmailSendDraft(
                recipient="recipient@example.com",
                subject="D88 Batch 04",
                body="Exact body\n",
            )
        )
    ).proposal
    outcome = approvals.approve(
        proposal.approval_id,
        proposal.send_digest,
    )
    assert outcome.approved is not None
    return outcome.approved


def send_profile():
    return CredentialProfile(
        profile_id=GMAIL_SEND_CREDENTIAL_PROFILE_ID,
        plugin_id=GMAIL_PLUGIN_ID,
        plugin_version=GMAIL_PLUGIN_VERSION,
        capability_name=GMAIL_SEND_CAPABILITY_NAME,
        provider_id=GMAIL_CREDENTIAL_PROVIDER_ID,
        auth_scheme=GMAIL_CREDENTIAL_AUTH_SCHEME,
        required_scopes=(GMAIL_SEND_CREDENTIAL_SCOPE,),
        secret_ref=GMAIL_SEND_CREDENTIAL_SECRET_REF,
    )


def build_service(
    *,
    approval_store,
    execution_store,
    client,
    secret_source,
    enabled=True,
    sender=SENDER,
    permit=True,
):
    broker = CredentialAccessBroker(
        profile_catalog=CredentialProfileCatalog((send_profile(),)),
        secret_source=secret_source,
    )
    adapter = GmailSendModuleAdapter(
        credential_broker=broker,
        client=client,
    )
    registry = AdapterRegistry((adapter,))
    permissions = (
        (
            ExecutableCapabilityPermission(
                capability_id=GMAIL_SEND_CAPABILITY_ID,
                target_kind="module",
                adapter_id=GMAIL_SEND_ADAPTER_ID,
                operation=GMAIL_SEND_OPERATION,
                effect="external_side_effect",
                data_class="owner_data",
                owner_approval_required=True,
            ),
        )
        if permit
        else ()
    )
    policy = CapabilityPermissionPolicy(
        registry=registry,
        permissions=permissions,
    )
    return GmailSendExecutionService(
        approval_store=approval_store,
        execution_store=execution_store,
        guard=ExecutionGuard(
            registry=registry,
            permission_policy=policy,
        ),
        runtime=ModuleRuntime(registry=registry),
        sender=sender,
        enabled=enabled,
    )


def stores():
    return (
        GmailSendApprovalStore(clock=lambda: NOW),
        GmailSendExecutionClaimStore(clock=lambda: NOW),
    )


def test_success_claims_before_credential_and_returns_message_id() -> None:
    approval_store, execution_store = stores()
    approved = create_approved(approval_store)
    client = FakeClient()
    source = ClaimCheckingSecretSource(
        execution_store,
        approved.approval_id,
    )
    service = build_service(
        approval_store=approval_store,
        execution_store=execution_store,
        client=client,
        secret_source=source,
    )

    outcome = service.execute(
        approved.approval_id,
        approved.send_digest,
    )

    assert outcome.status == "succeeded"
    assert outcome.reason_code == "gmail_send_succeeded"
    assert outcome.provider_attempted is True
    assert outcome.message_id == "gmail-message-id-1"
    assert source.calls == 1
    assert client.calls == 1
    assert execution_store.state(approved.approval_id) == "succeeded"


def test_replay_and_concurrency_allow_at_most_one_provider_attempt() -> None:
    approval_store, execution_store = stores()
    approved = create_approved(approval_store)
    client = FakeClient()
    source = ClaimCheckingSecretSource(
        execution_store,
        approved.approval_id,
    )
    service = build_service(
        approval_store=approval_store,
        execution_store=execution_store,
        client=client,
        secret_source=source,
    )

    def attempt():
        try:
            return service.execute(
                approved.approval_id,
                approved.send_digest,
            ).status
        except GmailSendExecutionAlreadyClaimedError:
            return "blocked"

    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(lambda _: attempt(), range(16)))

    assert outcomes.count("succeeded") == 1
    assert outcomes.count("blocked") == 15
    assert client.calls == 1
    assert source.calls == 1


def test_wrong_digest_not_approved_and_authorization_fail_before_claim() -> None:
    approval_store, execution_store = stores()
    approved = create_approved(approval_store)
    client = FakeClient()
    source = ClaimCheckingSecretSource(
        execution_store,
        approved.approval_id,
    )
    service = build_service(
        approval_store=approval_store,
        execution_store=execution_store,
        client=client,
        secret_source=source,
    )
    wrong = "0" * 64
    if wrong == approved.send_digest:
        wrong = "f" * 64

    with pytest.raises(GmailSendExecutionDigestMismatchError):
        service.execute(approved.approval_id, wrong)

    pending_store, pending_execution_store = stores()
    approvals = GmailSendApprovalService(store=pending_store)
    pending = approvals.propose(
        GmailSendRequest(
            message=GmailSendDraft(
                recipient="pending@example.com",
                subject="Pending",
                body="Pending body",
            )
        )
    ).proposal
    pending_service = build_service(
        approval_store=pending_store,
        execution_store=pending_execution_store,
        client=FakeClient(),
        secret_source=EmptySecretSource(),
    )
    with pytest.raises(GmailSendExecutionNotApprovedError):
        pending_service.execute(
            pending.approval_id,
            pending.send_digest,
        )

    auth_store, auth_execution_store = stores()
    auth_approved = create_approved(auth_store)
    auth_client = FakeClient()
    auth_source = ClaimCheckingSecretSource(
        auth_execution_store,
        auth_approved.approval_id,
    )
    auth_service = build_service(
        approval_store=auth_store,
        execution_store=auth_execution_store,
        client=auth_client,
        secret_source=auth_source,
        permit=False,
    )
    with pytest.raises(GmailSendExecutionAuthorizationError):
        auth_service.execute(
            auth_approved.approval_id,
            auth_approved.send_digest,
        )

    assert execution_store.record_count == 0
    assert pending_execution_store.record_count == 0
    assert auth_execution_store.record_count == 0
    assert client.calls == 0
    assert auth_client.calls == 0
    assert auth_source.calls == 0


def test_credential_unavailable_consumes_claim_without_provider_attempt() -> None:
    approval_store, execution_store = stores()
    approved = create_approved(approval_store)
    client = FakeClient()
    service = build_service(
        approval_store=approval_store,
        execution_store=execution_store,
        client=client,
        secret_source=EmptySecretSource(),
    )

    outcome = service.execute(
        approved.approval_id,
        approved.send_digest,
    )

    assert outcome.status == "failed"
    assert outcome.reason_code == "gmail_send_credential_unavailable"
    assert outcome.provider_attempted is False
    assert client.calls == 0
    assert execution_store.state(approved.approval_id) == "failed"

    with pytest.raises(GmailSendExecutionAlreadyClaimedError):
        service.execute(approved.approval_id, approved.send_digest)


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (
            GmailSendConnectorError(
                GMAIL_SEND_ERROR_PROVIDER_REJECTED,
                provider_attempted=True,
                indeterminate=False,
            ),
            "failed",
        ),
        (
            GmailSendConnectorError(
                GMAIL_SEND_ERROR_INDETERMINATE,
                provider_attempted=True,
                indeterminate=True,
            ),
            "indeterminate",
        ),
    ],
)
def test_provider_failure_is_terminal_without_retry(
    error,
    expected_status,
) -> None:
    approval_store, execution_store = stores()
    approved = create_approved(approval_store)
    client = FakeClient(error=error)
    source = ClaimCheckingSecretSource(
        execution_store,
        approved.approval_id,
    )
    service = build_service(
        approval_store=approval_store,
        execution_store=execution_store,
        client=client,
        secret_source=source,
    )

    outcome = service.execute(
        approved.approval_id,
        approved.send_digest,
    )

    assert outcome.status == expected_status
    assert outcome.provider_attempted is True
    assert client.calls == 1

    with pytest.raises(GmailSendExecutionAlreadyClaimedError):
        service.execute(approved.approval_id, approved.send_digest)
    assert client.calls == 1


@pytest.mark.parametrize(
    ("enabled", "sender", "error_type"),
    [
        (False, SENDER, GmailSendExecutionDisabledError),
        (True, None, GmailSendExecutionSenderNotConfiguredError),
        (True, "owner@localhost", GmailSendExecutionSenderNotConfiguredError),
    ],
)
def test_deployment_gates_fail_before_claim_or_provider(
    enabled,
    sender,
    error_type,
) -> None:
    approval_store, execution_store = stores()
    approved = create_approved(approval_store)
    client = FakeClient()
    service = build_service(
        approval_store=approval_store,
        execution_store=execution_store,
        client=client,
        secret_source=EmptySecretSource(),
        enabled=enabled,
        sender=sender,
    )

    with pytest.raises(error_type):
        service.execute(
            approved.approval_id,
            approved.send_digest,
        )

    assert execution_store.record_count == 0
    assert client.calls == 0
