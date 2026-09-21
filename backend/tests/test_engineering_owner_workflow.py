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
    EngineeringOwnerActiveWorkflowError,
    EngineeringOwnerBindingStore,
)
from app.services.engineering_owner_workflow import (
    EngineeringOwnerConversationNotFoundError,
    EngineeringOwnerUpstreamError,
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


def _service(root: Path, conversation_id):
    reader = EngineeringRepositoryReader(root)
    counter = itertools.count(1)
    store = EngineeringApplyApprovalStore(
        approval_id_factory=lambda: f"approval-{next(counter)}"
    )
    return (
        EngineeringOwnerWorkflowService(
            workspace_scope=PERSONAL,
            conversation_repository=FakeConversationRepository(
                conversation_id
            ),
            repository_reader=reader,
            proposal_service=EngineeringChangeProposalService(reader),
            approval_service=EngineeringApplyApprovalService(
                store=store,
                workspace_scope=PERSONAL,
            ),
            execution_service=EngineeringApplyExecutionService(
                approval_store=store,
                workspace_scope=PERSONAL,
                repository_root=root,
            ),
            binding_store=EngineeringOwnerBindingStore(),
        ),
        store,
    )


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "backend").mkdir()
    (root / "backend" / "app.py").write_bytes(b"value = 1\n")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("secret", encoding="utf-8")
    return root


def test_d109_read_uses_exact_d106_boundary(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    conversation_id = uuid4()
    service, _ = _service(root, conversation_id)

    observed = service.read(
        conversation_id=conversation_id,
        operation="read_text",
        relative_path="backend/app.py",
    )

    assert observed.relative_path == "backend/app.py"
    assert observed.content == "value = 1\n"


def test_d109_sensitive_read_is_still_denied(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    conversation_id = uuid4()
    service, _ = _service(root, conversation_id)

    with pytest.raises(EngineeringOwnerUpstreamError) as error:
        service.read(
            conversation_id=conversation_id,
            operation="read_text",
            relative_path=".git/config",
        )

    assert error.value.reason_code == "engineering_path_not_allowed"


def test_d109_create_proposal_registers_pending_without_mutation(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    conversation_id = uuid4()
    target = root / "backend" / "new.py"
    service, d108_store = _service(root, conversation_id)

    binding = service.propose(
        conversation_id=conversation_id,
        operation="create_text",
        relative_path="backend/new.py",
        proposed_content="value = 2\n",
    )

    assert binding.presentation_state == "pending"
    assert binding.review.base_state == "absent"
    assert binding.review.before_content is None
    assert binding.review.after_content == "value = 2\n"
    assert d108_store.state(binding.approval_id) == "pending"
    assert not target.exists()


def test_d109_replace_review_is_exact_d107_snapshot(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    conversation_id = uuid4()
    service, _ = _service(root, conversation_id)

    binding = service.propose(
        conversation_id=conversation_id,
        operation="replace_text",
        relative_path="backend/app.py",
        proposed_content="value = 2\n",
    )

    assert binding.review.base_state == "present"
    assert binding.review.before_content == "value = 1\n"
    assert binding.review.after_content == "value = 2\n"
    assert (root / "backend" / "app.py").read_bytes() == b"value = 1\n"


def test_d109_second_active_proposal_is_rejected(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    conversation_id = uuid4()
    service, _ = _service(root, conversation_id)

    service.propose(
        conversation_id=conversation_id,
        operation="create_text",
        relative_path="backend/new.py",
        proposed_content="value = 2\n",
    )

    with pytest.raises(EngineeringOwnerActiveWorkflowError):
        service.propose(
            conversation_id=conversation_id,
            operation="create_text",
            relative_path="backend/other.py",
            proposed_content="value = 3\n",
        )

    assert not (root / "backend" / "new.py").exists()
    assert not (root / "backend" / "other.py").exists()


def test_d109_unknown_conversation_fails_before_repository_read(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    known = uuid4()
    unknown = uuid4()
    service, _ = _service(root, known)

    with pytest.raises(EngineeringOwnerConversationNotFoundError):
        service.read(
            conversation_id=unknown,
            operation="read_text",
            relative_path="backend/app.py",
        )
