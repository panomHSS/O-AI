from __future__ import annotations

import itertools
from pathlib import Path
from uuid import uuid4

import pytest

from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.services.engineering_apply_approval import (
    EngineeringApplyApprovalService,
    EngineeringApplyApprovalStore,
)
from app.services.engineering_apply_execution import (
    EngineeringApplyExecutionService,
)
from app.services.engineering_change_proposal import (
    EngineeringChangeProposalService,
)
from app.services.engineering_owner_binding import (
    EngineeringOwnerBindingCollisionError,
    EngineeringOwnerBindingStateError,
    EngineeringOwnerBindingStore,
)
from app.services.engineering_owner_workflow import (
    EngineeringOwnerWorkflowService,
)
from app.services.engineering_repository_reader import (
    EngineeringRepositoryReader,
)


PERSONAL = WorkspaceScope(WorkspaceId.PERSONAL)


class FakeConversationRepository:
    def __init__(self, *conversation_ids):
        self._ids = {str(item) for item in conversation_ids}

    def get(self, conversation_id: str):
        return object() if conversation_id in self._ids else None


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "backend").mkdir()
    (root / "backend" / "app.py").write_bytes(b"value = 1\n")
    return root


def _service(root: Path, *conversation_ids):
    counter = itertools.count(1)
    approval_store = EngineeringApplyApprovalStore(
        approval_id_factory=lambda: f"approval-{next(counter)}"
    )
    reader = EngineeringRepositoryReader(root)
    workflow = EngineeringOwnerWorkflowService(
        workspace_scope=PERSONAL,
        conversation_repository=FakeConversationRepository(
            *conversation_ids
        ),
        repository_reader=reader,
        proposal_service=EngineeringChangeProposalService(reader),
        approval_service=EngineeringApplyApprovalService(
            store=approval_store,
            workspace_scope=PERSONAL,
        ),
        execution_service=EngineeringApplyExecutionService(
            approval_store=approval_store,
            workspace_scope=PERSONAL,
            repository_root=root,
        ),
        binding_store=EngineeringOwnerBindingStore(),
    )
    return workflow, approval_store


def _pending_create(workflow, conversation_id):
    return workflow.propose(
        conversation_id=conversation_id,
        operation="create_text",
        relative_path="backend/new.py",
        proposed_content="value = 2\n",
    )


def test_d109_approve_is_separate_from_apply(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    conversation_id = uuid4()
    workflow, store = _service(root, conversation_id)
    pending = _pending_create(workflow, conversation_id)

    approved = workflow.approve(
        conversation_id=conversation_id,
        approval_id=pending.approval_id,
        proposal_digest=pending.proposal_digest,
    )

    assert approved.presentation_state == "approved"
    assert store.state(pending.approval_id) == "approved"
    assert not (root / "backend" / "new.py").exists()


def test_d109_explicit_apply_mutates_once(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    conversation_id = uuid4()
    workflow, _ = _service(root, conversation_id)
    pending = _pending_create(workflow, conversation_id)
    approved = workflow.approve(
        conversation_id=conversation_id,
        approval_id=pending.approval_id,
        proposal_digest=pending.proposal_digest,
    )

    applied = workflow.apply(
        conversation_id=conversation_id,
        approval_id=approved.approval_id,
        proposal_digest=approved.proposal_digest,
    )

    assert applied.presentation_state == "applied"
    assert (root / "backend" / "new.py").read_bytes() == b"value = 2\n"

    with pytest.raises(EngineeringOwnerBindingStateError):
        workflow.apply(
            conversation_id=conversation_id,
            approval_id=approved.approval_id,
            proposal_digest=approved.proposal_digest,
        )


def test_d109_deny_is_terminal_and_never_mutates(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    conversation_id = uuid4()
    workflow, store = _service(root, conversation_id)
    pending = _pending_create(workflow, conversation_id)

    denied = workflow.deny(
        conversation_id=conversation_id,
        approval_id=pending.approval_id,
        proposal_digest=pending.proposal_digest,
    )

    assert denied.presentation_state == "denied"
    assert store.state(pending.approval_id) == "denied"
    assert not (root / "backend" / "new.py").exists()

    with pytest.raises(EngineeringOwnerBindingStateError):
        workflow.apply(
            conversation_id=conversation_id,
            approval_id=pending.approval_id,
            proposal_digest=pending.proposal_digest,
        )


def test_d109_cross_conversation_approval_fails_closed(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    conversation_a = uuid4()
    conversation_b = uuid4()
    workflow, _ = _service(root, conversation_a, conversation_b)
    pending = _pending_create(workflow, conversation_a)

    with pytest.raises(EngineeringOwnerBindingCollisionError):
        workflow.approve(
            conversation_id=conversation_b,
            approval_id=pending.approval_id,
            proposal_digest=pending.proposal_digest,
        )

    assert not (root / "backend" / "new.py").exists()


def test_d109_tampered_digest_fails_before_owner_decision(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    conversation_id = uuid4()
    workflow, store = _service(root, conversation_id)
    pending = _pending_create(workflow, conversation_id)

    with pytest.raises(EngineeringOwnerBindingCollisionError):
        workflow.approve(
            conversation_id=conversation_id,
            approval_id=pending.approval_id,
            proposal_digest="0" * 64,
        )

    assert store.state(pending.approval_id) == "pending"


def test_d109_terminal_workflow_requires_fresh_proposal(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    conversation_id = uuid4()
    workflow, _ = _service(root, conversation_id)
    first = _pending_create(workflow, conversation_id)

    workflow.deny(
        conversation_id=conversation_id,
        approval_id=first.approval_id,
        proposal_digest=first.proposal_digest,
    )

    second = workflow.propose(
        conversation_id=conversation_id,
        operation="create_text",
        relative_path="backend/other.py",
        proposed_content="value = 3\n",
    )

    assert second.approval_id != first.approval_id
    assert second.presentation_state == "pending"
    assert second.review.relative_path == "backend/other.py"
