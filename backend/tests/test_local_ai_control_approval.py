from __future__ import annotations

import inspect
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone

from app.contracts.local_ai_control import LocalAIControlPreview
from app.services import local_ai_control_approval as approval_module
from app.services.local_ai_control_approval import (
    DEFAULT_LOCAL_AI_CONTROL_APPROVAL_TTL,
    DEFAULT_MAX_LOCAL_AI_CONTROL_APPROVAL_RECORDS,
    LocalAIControlApprovalAlreadyClaimedError,
    LocalAIControlApprovalDigestMismatchError,
    LocalAIControlApprovalExpiredError,
    LocalAIControlApprovalNotApprovedError,
    LocalAIControlApprovalNotPendingError,
    LocalAIControlApprovalProposalInvalidError,
    LocalAIControlApprovalService,
    LocalAIControlApprovalStore,
    LocalAIControlApprovalStoreFullError,
    local_ai_control_digest,
    local_ai_control_preview,
    local_ai_control_projection,
)


class LocalAIControlApprovalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = [datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)]
        self.next_id = 0

        def new_id() -> str:
            self.next_id += 1
            return f"control-{self.next_id}"

        self.store = LocalAIControlApprovalStore(clock=lambda: self.now[0], approval_id_factory=new_id)
        self.service = LocalAIControlApprovalService(store=self.store)

    def load(self) -> LocalAIControlPreview:
        return local_ai_control_preview(
            operation="load_configured_model",
            backend_id="ollama",
            configured_model_id="qwen3.5:9b",
            expected_loaded_state=False,
        )

    def unload(self) -> LocalAIControlPreview:
        return local_ai_control_preview(
            operation="unload_configured_model",
            backend_id="ollama",
            configured_model_id="qwen3.5:9b",
            expected_loaded_state=True,
        )

    def test_exact_two_operations_and_state_transitions(self) -> None:
        self.assertEqual((self.load().expected_loaded_state, self.load().desired_loaded_state), (False, True))
        self.assertEqual((self.unload().expected_loaded_state, self.unload().desired_loaded_state), (True, False))
        with self.assertRaises(LocalAIControlApprovalProposalInvalidError):
            local_ai_control_preview(
                operation="switch_model",  # type: ignore[arg-type]
                backend_id="ollama",
                configured_model_id="qwen3.5:9b",
                expected_loaded_state=False,
            )

    def test_contract_is_immutable(self) -> None:
        preview = self.load()
        with self.assertRaises(FrozenInstanceError):
            preview.backend_id = "other"  # type: ignore[misc]

    def test_projection_and_digest_are_deterministic_and_bound(self) -> None:
        preview = self.load()
        expected = {
            "contract_version": "1",
            "operation": "load_configured_model",
            "backend_id": "ollama",
            "configured_model_id": "qwen3.5:9b",
            "expected_loaded_state": False,
            "desired_loaded_state": True,
        }
        self.assertEqual(local_ai_control_projection(preview), expected)
        digest = local_ai_control_digest(preview)
        self.assertEqual(digest, local_ai_control_digest(preview))
        self.assertNotEqual(digest, local_ai_control_digest(replace(preview, configured_model_id="other")))
        self.assertNotEqual(digest, local_ai_control_digest(self.unload()))

    def test_proposal_and_approve_have_no_execution_result(self) -> None:
        preview = self.load()
        proposal = self.service.propose(preview).proposal
        self.assertFalse(hasattr(proposal, "execution"))
        outcome = self.service.approve(proposal.approval_id, proposal.control_digest)
        self.assertEqual(outcome.decision, "approved")
        self.assertIs(outcome.approved.preview, preview)  # type: ignore[union-attr]
        self.assertFalse(hasattr(outcome, "execution"))

    def test_deny_is_terminal(self) -> None:
        proposal = self.service.propose(self.load()).proposal
        self.service.deny(proposal.approval_id, proposal.control_digest)
        with self.assertRaises(LocalAIControlApprovalNotPendingError):
            self.service.approve(proposal.approval_id, proposal.control_digest)
        with self.assertRaises(LocalAIControlApprovalNotApprovedError):
            self.store.claim_approved(proposal.approval_id, proposal.control_digest)

    def test_wrong_digest_consumes_pending_ticket(self) -> None:
        proposal = self.service.propose(self.load()).proposal
        with self.assertRaises(LocalAIControlApprovalDigestMismatchError):
            self.service.approve(proposal.approval_id, "0" * 64)
        with self.assertRaises(LocalAIControlApprovalNotPendingError):
            self.service.approve(proposal.approval_id, proposal.control_digest)

    def test_exact_ttl_and_expiry(self) -> None:
        self.assertEqual(DEFAULT_LOCAL_AI_CONTROL_APPROVAL_TTL, timedelta(minutes=10))
        proposal = self.service.propose(self.load()).proposal
        self.now[0] += timedelta(minutes=10)
        with self.assertRaises(LocalAIControlApprovalExpiredError):
            self.service.approve(proposal.approval_id, proposal.control_digest)

    def test_store_bound_is_128(self) -> None:
        self.assertEqual(DEFAULT_MAX_LOCAL_AI_CONTROL_APPROVAL_RECORDS, 128)
        store = LocalAIControlApprovalStore(max_records=1, clock=lambda: self.now[0], approval_id_factory=lambda: "one")
        service = LocalAIControlApprovalService(store=store)
        service.propose(self.load())
        with self.assertRaises(LocalAIControlApprovalStoreFullError):
            service.propose(self.unload())

    def test_claim_is_single_use(self) -> None:
        proposal = self.service.propose(self.load()).proposal
        self.service.approve(proposal.approval_id, proposal.control_digest)
        self.store.claim_approved(proposal.approval_id, proposal.control_digest)
        with self.assertRaises(LocalAIControlApprovalAlreadyClaimedError):
            self.store.claim_approved(proposal.approval_id, proposal.control_digest)

    def test_concurrent_claim_has_one_winner(self) -> None:
        proposal = self.service.propose(self.load()).proposal
        self.service.approve(proposal.approval_id, proposal.control_digest)

        def attempt() -> str:
            try:
                self.store.claim_approved(proposal.approval_id, proposal.control_digest)
                return "claimed"
            except LocalAIControlApprovalAlreadyClaimedError:
                return "already"

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = sorted(pool.map(lambda _: attempt(), range(2)))
        self.assertEqual(results, ["already", "claimed"])

    def test_batch01_has_no_runtime_generation_routing_or_persistence_authority(self) -> None:
        self.assertEqual(tuple(inspect.signature(LocalAIControlApprovalService).parameters), ("store",))
        source = inspect.getsource(approval_module)
        for marker in (
            "LocalAIRuntimeClient", "OllamaRuntimeClient", "LocalAIAdapter",
            "AIRuntime", "AIRouter", "ConversationService", "ChatService",
            "Session", "Repository", ".generate(", ".execute(",
            "load_model(", "unload_model(",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
