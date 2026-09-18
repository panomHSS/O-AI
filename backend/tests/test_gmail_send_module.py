from __future__ import annotations

from dataclasses import replace

from pydantic import SecretStr

from app.adapters.gmail_send_module import (
    GMAIL_SEND_ERROR_CREDENTIAL_UNAVAILABLE,
    GmailSendModuleAdapter,
)
from app.connectors.gmail_send import (
    GMAIL_SEND_ERROR_INDETERMINATE,
    GMAIL_SEND_ERROR_PROVIDER_REJECTED,
    GmailSendConnectorError,
    GmailSendProviderResult,
)
from app.contracts.command import ExecutionPlan
from app.contracts.credential import CredentialProfile
from app.contracts.gmail import (
    GMAIL_CREDENTIAL_AUTH_SCHEME,
    GMAIL_CREDENTIAL_PROVIDER_ID,
    GMAIL_PLUGIN_ID,
    GMAIL_PLUGIN_VERSION,
)
from app.contracts.gmail_send import GmailSendDraft, GmailSendRequest
from app.contracts.gmail_send_approval import ApprovedGmailSendApproval
from app.contracts.gmail_send_execution import (
    GMAIL_SEND_ADAPTER_ID,
    GMAIL_SEND_CAPABILITY_NAME,
    GMAIL_SEND_CREDENTIAL_PROFILE_ID,
    GMAIL_SEND_CREDENTIAL_SCOPE,
    GMAIL_SEND_CREDENTIAL_SECRET_REF,
)
from app.services.credential_access_broker import (
    CredentialAccessBroker,
    StaticCredentialSecretSource,
)
from app.services.credential_profile_catalog import CredentialProfileCatalog
from app.services.gmail_send_approval import (
    gmail_send_digest,
    gmail_send_preview,
)
from app.services.gmail_send_execution import build_gmail_send_execution_plan


class FakeClient:
    def __init__(self, result=None, error=None):
        self.result = result or GmailSendProviderResult(
            message_id="gmail-message-id-1"
        )
        self.error = error
        self.calls = []

    def send_message(self, access_token, *, sender, request):
        self.calls.append((access_token, sender, request))
        if self.error is not None:
            raise self.error
        return self.result


def approved() -> ApprovedGmailSendApproval:
    from datetime import datetime, timedelta, timezone

    now = datetime(2026, 9, 18, 12, 0, tzinfo=timezone.utc)
    request = GmailSendRequest(
        message=GmailSendDraft(
            recipient="recipient@example.com",
            subject="D88 module",
            body="Exact body\n",
        )
    )
    return ApprovedGmailSendApproval(
        approval_id="approval-1",
        request=request,
        send_digest=gmail_send_digest(request),
        preview=gmail_send_preview(request),
        approved_at=now,
        expires_at=now + timedelta(minutes=10),
    )


def broker(
    *,
    profile: CredentialProfile | None = None,
    include_secret: bool = True,
) -> CredentialAccessBroker:
    profile = profile or CredentialProfile(
        profile_id=GMAIL_SEND_CREDENTIAL_PROFILE_ID,
        plugin_id=GMAIL_PLUGIN_ID,
        plugin_version=GMAIL_PLUGIN_VERSION,
        capability_name=GMAIL_SEND_CAPABILITY_NAME,
        provider_id=GMAIL_CREDENTIAL_PROVIDER_ID,
        auth_scheme=GMAIL_CREDENTIAL_AUTH_SCHEME,
        required_scopes=(GMAIL_SEND_CREDENTIAL_SCOPE,),
        secret_ref=GMAIL_SEND_CREDENTIAL_SECRET_REF,
    )
    secrets = (
        {profile.secret_ref: SecretStr("send-access-token")}
        if include_secret
        else {}
    )
    return CredentialAccessBroker(
        profile_catalog=CredentialProfileCatalog((profile,)),
        secret_source=StaticCredentialSecretSource(secrets),
    )


def authorized_command_and_plan():
    snapshot = approved()
    command, planning, _ = build_gmail_send_execution_plan(
        snapshot,
        sender="owner@example.com",
    )
    assert planning.plan is not None
    plan = ExecutionPlan(
        request_id=planning.plan.request_id,
        adapter_id=planning.plan.adapter_id,
        steps=planning.plan.steps,
        owner_approval_required=False,
    )
    return snapshot, command, plan


def test_adapter_resolves_exact_send_credential_then_calls_client_once() -> None:
    snapshot, command, plan = authorized_command_and_plan()
    client = FakeClient()
    adapter = GmailSendModuleAdapter(
        credential_broker=broker(),
        client=client,
    )

    result = adapter.execute(command, plan)

    assert result.status == "succeeded"
    assert result.error is None
    assert result.output == {
        "message_id": "gmail-message-id-1",
        "provider_attempted": True,
    }
    assert len(client.calls) == 1
    token, sender, send_request = client.calls[0]
    assert token.get_secret_value() == "send-access-token"
    assert sender == "owner@example.com"
    assert send_request == snapshot.request


def test_adapter_rejects_plan_that_still_requires_owner_approval() -> None:
    _, command, plan = authorized_command_and_plan()
    client = FakeClient()
    adapter = GmailSendModuleAdapter(
        credential_broker=broker(),
        client=client,
    )
    blocked = replace(plan, owner_approval_required=True)

    result = adapter.execute(command, blocked)

    assert result.status == "failed"
    assert result.error == "owner_approval_required"
    assert result.output == {"provider_attempted": False}
    assert client.calls == []


def test_read_only_credential_cannot_satisfy_send_subject() -> None:
    _, command, plan = authorized_command_and_plan()
    read_profile = CredentialProfile(
        profile_id="gmail.messages.readonly",
        plugin_id="gmail",
        plugin_version="1.0.0",
        capability_name="read_messages",
        provider_id="google",
        auth_scheme="oauth2_bearer",
        required_scopes=(
            "https://www.googleapis.com/auth/gmail.readonly",
        ),
        secret_ref="gmail.access_token",
    )
    client = FakeClient()
    adapter = GmailSendModuleAdapter(
        credential_broker=broker(profile=read_profile),
        client=client,
    )

    result = adapter.execute(command, plan)

    assert result.status == "failed"
    assert result.error == GMAIL_SEND_ERROR_CREDENTIAL_UNAVAILABLE
    assert result.output == {"provider_attempted": False}
    assert client.calls == []


def test_wrong_send_profile_identity_is_rejected_before_provider() -> None:
    _, command, plan = authorized_command_and_plan()
    wrong = CredentialProfile(
        profile_id="gmail.messages.send.wrong",
        plugin_id=GMAIL_PLUGIN_ID,
        plugin_version=GMAIL_PLUGIN_VERSION,
        capability_name=GMAIL_SEND_CAPABILITY_NAME,
        provider_id=GMAIL_CREDENTIAL_PROVIDER_ID,
        auth_scheme=GMAIL_CREDENTIAL_AUTH_SCHEME,
        required_scopes=(GMAIL_SEND_CREDENTIAL_SCOPE,),
        secret_ref="gmail.send.wrong.access_token",
    )
    client = FakeClient()
    adapter = GmailSendModuleAdapter(
        credential_broker=broker(profile=wrong),
        client=client,
    )

    result = adapter.execute(command, plan)

    assert result.status == "failed"
    assert result.error == GMAIL_SEND_ERROR_CREDENTIAL_UNAVAILABLE
    assert result.output == {"provider_attempted": False}
    assert client.calls == []


def test_provider_failure_truth_is_preserved_without_retry() -> None:
    _, command, plan = authorized_command_and_plan()

    for error in (
        GmailSendConnectorError(
            GMAIL_SEND_ERROR_PROVIDER_REJECTED,
            provider_attempted=True,
            indeterminate=False,
        ),
        GmailSendConnectorError(
            GMAIL_SEND_ERROR_INDETERMINATE,
            provider_attempted=True,
            indeterminate=True,
        ),
    ):
        client = FakeClient(error=error)
        adapter = GmailSendModuleAdapter(
            credential_broker=broker(),
            client=client,
        )

        result = adapter.execute(command, plan)

        assert result.status == "failed"
        assert result.error == error.code
        assert result.output == {"provider_attempted": True}
        assert len(client.calls) == 1


def test_private_adapter_identity_is_exact() -> None:
    adapter = GmailSendModuleAdapter(
        credential_broker=broker(),
        client=FakeClient(),
    )
    assert adapter.adapter_id == GMAIL_SEND_ADAPTER_ID
    assert adapter.module_name == "Gmail Send Message"
