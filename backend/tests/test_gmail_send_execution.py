from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.contracts.gmail_send import GmailSendDraft, GmailSendRequest
from app.contracts.gmail_send_approval import ApprovedGmailSendApproval
from app.contracts.gmail_send_execution import (
    GMAIL_SEND_ADAPTER_ID,
    GmailSendExecutionOutcome,
    gmail_send_execution_parameters,
    gmail_send_request_from_parameters,
)
from app.services.execution_guard import execution_plan_digest
from app.services.gmail_send_approval import (
    gmail_send_digest,
    gmail_send_preview,
)
from app.services.gmail_send_execution import (
    GmailSendExecutionAlreadyClaimedError,
    GmailSendExecutionClaimStore,
    GmailSendExecutionExpiredError,
    GmailSendExecutionIntegrityError,
    GmailSendExecutionStoreFullError,
    GmailSendExecutionTerminalError,
    build_gmail_send_execution_plan,
)


NOW = datetime(2026, 9, 18, 12, 0, tzinfo=timezone.utc)
SENDER = "owner@example.com"


def approved_request(
    *,
    approval_id: str = "approval-1",
    recipient: str = "recipient@example.com",
    subject: str = "D88 subject",
    body: str = "Line 1\n\tLine 2",
    expires_at: datetime | None = None,
) -> ApprovedGmailSendApproval:
    request = GmailSendRequest(
        message=GmailSendDraft(
            recipient=recipient,
            subject=subject,
            body=body,
        )
    )
    return ApprovedGmailSendApproval(
        approval_id=approval_id,
        request=request,
        send_digest=gmail_send_digest(request),
        preview=gmail_send_preview(request),
        approved_at=NOW,
        expires_at=expires_at or NOW + timedelta(minutes=10),
    )


def test_execution_projection_round_trips_exact_d86_request() -> None:
    approved = approved_request(
        subject="Café",
        body="A\n\tCafe\u0301\n",
    )
    parameters = gmail_send_execution_parameters(
        approved.request,
        approved.send_digest,
        sender=SENDER,
    )

    reconstructed, digest, sender = gmail_send_request_from_parameters(
        parameters
    )

    assert reconstructed == approved.request
    assert digest == approved.send_digest
    assert sender == SENDER
    assert parameters == {
        "contract_version": "1",
        "send_digest": approved.send_digest,
        "sender": SENDER,
        "recipient": "recipient@example.com",
        "subject": "Café",
        "body": "A\n\tCafe\u0301\n",
    }


@pytest.mark.parametrize(
    "extra",
    [
        {"cc": "cc@example.com"},
        {"bcc": "bcc@example.com"},
        {"html": "<b>x</b>"},
        {"attachment": "x"},
        {"retry": True},
        {"provider": "gmail"},
    ],
)
def test_execution_projection_rejects_extra_authority_fields(extra) -> None:
    approved = approved_request()
    parameters = gmail_send_execution_parameters(
        approved.request,
        approved.send_digest,
        sender=SENDER,
    )
    parameters.update(extra)

    with pytest.raises(
        ValueError,
        match="gmail_send_execution_parameters_invalid",
    ):
        gmail_send_request_from_parameters(parameters)


@pytest.mark.parametrize(
    "sender",
    [
        "",
        " owner@example.com",
        "owner@example.com ",
        ".owner@example.com",
        "owner..name@example.com",
        "owner@localhost",
        "owner\n@example.com",
    ],
)
def test_sender_requires_exact_single_mailbox(sender: str) -> None:
    approved = approved_request()
    with pytest.raises(ValueError):
        gmail_send_execution_parameters(
            approved.request,
            approved.send_digest,
            sender=sender,
        )


def test_build_plan_is_deterministic_and_domain_separated() -> None:
    approved = approved_request()

    command1, planning1, digest1 = build_gmail_send_execution_plan(
        approved,
        sender=SENDER,
    )
    command2, planning2, digest2 = build_gmail_send_execution_plan(
        approved,
        sender=SENDER,
    )

    assert command1 == command2
    assert planning1 == planning2
    assert digest1 == digest2
    assert digest1 != approved.send_digest
    assert planning1.plan is not None
    assert execution_plan_digest(planning1.plan) == digest1
    assert planning1.plan.adapter_id == GMAIL_SEND_ADAPTER_ID
    assert planning1.plan.owner_approval_required is True
    assert command1.command == "module.execute"


def test_plan_digest_binds_sender() -> None:
    approved = approved_request()

    _, _, digest1 = build_gmail_send_execution_plan(
        approved,
        sender="owner@example.com",
    )
    _, _, digest2 = build_gmail_send_execution_plan(
        approved,
        sender="alternate@example.com",
    )

    assert digest1 != digest2


def test_plan_rejects_tampered_approved_digest() -> None:
    approved = approved_request()
    tampered = replace(approved, send_digest="0" * 64)

    with pytest.raises(GmailSendExecutionIntegrityError):
        build_gmail_send_execution_plan(
            tampered,
            sender=SENDER,
        )


def test_plan_rejects_tampered_approved_preview() -> None:
    approved = approved_request()
    other = approved_request(subject="other")
    tampered = replace(approved, preview=other.preview)

    with pytest.raises(GmailSendExecutionIntegrityError):
        build_gmail_send_execution_plan(
            tampered,
            sender=SENDER,
        )


def test_claim_is_exact_one_shot() -> None:
    approved = approved_request()
    _, _, plan_digest = build_gmail_send_execution_plan(
        approved,
        sender=SENDER,
    )
    store = GmailSendExecutionClaimStore(clock=lambda: NOW)

    claim = store.claim(
        approved,
        sender=SENDER,
        plan_digest=plan_digest,
    )

    assert claim.approval_id == approved.approval_id
    assert claim.send_digest == approved.send_digest
    assert claim.plan_digest == plan_digest
    assert claim.sender == SENDER
    assert store.state(approved.approval_id) == "claimed"

    with pytest.raises(GmailSendExecutionAlreadyClaimedError):
        store.claim(
            approved,
            sender=SENDER,
            plan_digest=plan_digest,
        )


def test_claim_rejects_wrong_plan_digest_before_consuming() -> None:
    approved = approved_request()
    _, _, plan_digest = build_gmail_send_execution_plan(
        approved,
        sender=SENDER,
    )
    wrong = "0" * 64
    if wrong == plan_digest:
        wrong = "f" * 64

    store = GmailSendExecutionClaimStore(clock=lambda: NOW)
    with pytest.raises(GmailSendExecutionIntegrityError):
        store.claim(
            approved,
            sender=SENDER,
            plan_digest=wrong,
        )

    assert store.record_count == 0


def test_claim_rejects_expired_approval() -> None:
    approved = approved_request(
        expires_at=NOW + timedelta(minutes=1),
    )
    _, _, plan_digest = build_gmail_send_execution_plan(
        approved,
        sender=SENDER,
    )
    store = GmailSendExecutionClaimStore(
        clock=lambda: NOW + timedelta(minutes=1)
    )

    with pytest.raises(GmailSendExecutionExpiredError):
        store.claim(
            approved,
            sender=SENDER,
            plan_digest=plan_digest,
        )

    assert store.record_count == 0


def test_claim_store_is_bounded() -> None:
    store = GmailSendExecutionClaimStore(
        max_records=1,
        clock=lambda: NOW,
    )
    first = approved_request(approval_id="approval-1")
    second = approved_request(approval_id="approval-2")
    _, _, first_digest = build_gmail_send_execution_plan(
        first,
        sender=SENDER,
    )
    _, _, second_digest = build_gmail_send_execution_plan(
        second,
        sender=SENDER,
    )

    store.claim(first, sender=SENDER, plan_digest=first_digest)

    with pytest.raises(GmailSendExecutionStoreFullError):
        store.claim(second, sender=SENDER, plan_digest=second_digest)


def test_concurrent_claim_allows_exactly_one_winner() -> None:
    approved = approved_request()
    _, _, plan_digest = build_gmail_send_execution_plan(
        approved,
        sender=SENDER,
    )
    store = GmailSendExecutionClaimStore(clock=lambda: NOW)

    def attempt() -> str:
        try:
            store.claim(
                approved,
                sender=SENDER,
                plan_digest=plan_digest,
            )
            return "claimed"
        except GmailSendExecutionAlreadyClaimedError:
            return "blocked"

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: attempt(), range(32)))

    assert results.count("claimed") == 1
    assert results.count("blocked") == 31
    assert store.record_count == 1


@pytest.mark.parametrize(
    ("status", "provider_attempted", "message_id"),
    [
        ("succeeded", True, "gmail-message-id-1"),
        ("failed", False, None),
        ("failed", True, None),
        ("indeterminate", True, None),
    ],
)
def test_terminal_outcome_contract(
    status: str,
    provider_attempted: bool,
    message_id: str | None,
) -> None:
    approved = approved_request()
    outcome = GmailSendExecutionOutcome(
        approval_id=approved.approval_id,
        send_digest=approved.send_digest,
        status=status,  # type: ignore[arg-type]
        reason_code=f"gmail_send_{status}",
        provider_attempted=provider_attempted,
        message_id=message_id,
    )
    assert outcome.status == status


@pytest.mark.parametrize(
    ("status", "provider_attempted", "message_id"),
    [
        ("succeeded", False, "gmail-message-id-1"),
        ("succeeded", True, None),
        ("indeterminate", False, None),
        ("indeterminate", True, "gmail-message-id-1"),
        ("failed", False, "gmail-message-id-1"),
    ],
)
def test_terminal_outcome_rejects_false_truth(
    status: str,
    provider_attempted: bool,
    message_id: str | None,
) -> None:
    approved = approved_request()
    with pytest.raises(ValueError):
        GmailSendExecutionOutcome(
            approval_id=approved.approval_id,
            send_digest=approved.send_digest,
            status=status,  # type: ignore[arg-type]
            reason_code="gmail_send_test",
            provider_attempted=provider_attempted,
            message_id=message_id,
        )


@pytest.mark.parametrize(
    ("status", "provider_attempted", "message_id"),
    [
        ("failed", False, None),
        ("indeterminate", True, None),
        ("succeeded", True, "gmail-message-id-1"),
    ],
)
def test_terminal_state_never_releases_claim(
    status: str,
    provider_attempted: bool,
    message_id: str | None,
) -> None:
    approved = approved_request()
    _, _, plan_digest = build_gmail_send_execution_plan(
        approved,
        sender=SENDER,
    )
    store = GmailSendExecutionClaimStore(clock=lambda: NOW)
    claim = store.claim(
        approved,
        sender=SENDER,
        plan_digest=plan_digest,
    )
    outcome = GmailSendExecutionOutcome(
        approval_id=approved.approval_id,
        send_digest=approved.send_digest,
        status=status,  # type: ignore[arg-type]
        reason_code=f"gmail_send_{status}",
        provider_attempted=provider_attempted,
        message_id=message_id,
    )

    assert store.complete(claim, outcome) == outcome
    assert store.state(approved.approval_id) == status

    with pytest.raises(GmailSendExecutionTerminalError):
        store.complete(claim, outcome)

    with pytest.raises(GmailSendExecutionAlreadyClaimedError):
        store.claim(
            approved,
            sender=SENDER,
            plan_digest=plan_digest,
        )


def test_batch01_surface_has_no_retry_release_reset_or_execute_method() -> None:
    forbidden = {
        "retry",
        "resend",
        "release",
        "reset",
        "execute",
        "send",
        "clear",
    }
    public = {
        name
        for name in dir(GmailSendExecutionClaimStore)
        if not name.startswith("_")
    }
    assert not (public & forbidden)


def test_batch01_service_still_has_no_credential_network_or_provider_dependency() -> None:
    contract_source = (
        Path(__file__).parents[1]
        / "app/contracts/gmail_send_execution.py"
    ).read_text(encoding="utf-8")
    service_source = (
        Path(__file__).parents[1]
        / "app/services/gmail_send_execution.py"
    ).read_text(encoding="utf-8")

    # D88 Batch 02 deliberately adds the exact gmail.send credential identity
    # to the execution contract, but Batch 01's planning/claim service must
    # still have zero credential, OAuth, runtime, network, or provider access.
    assert (
        "https://www.googleapis.com/auth/gmail.send"
        in contract_source
    )
    assert (
        "https://www.googleapis.com/auth/gmail.send"
        not in service_source
    )

    for marker in (
        "CredentialAccessBroker",
        "GoogleOAuthTokenManager",
        "gmail.googleapis.com",
        "urllib.request",
        "requests.",
        "httpx.",
        "GmailClient",
        "GmailSendClient",
        "ModuleRuntime",
        ".execute(",
    ):
        assert marker not in service_source
