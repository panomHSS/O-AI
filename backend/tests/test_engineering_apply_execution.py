from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.contracts.command import Result
from app.contracts.engineering_change_proposal import (
    EngineeringChangeDraft,
    EngineeringChangeOperation,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.services.engineering_apply_approval import (
    EngineeringApplyApprovalService,
    EngineeringApplyApprovalStore,
    EngineeringApplyNotApprovedError,
)
from app.services.engineering_apply_execution import (
    EngineeringApplyExecutionService,
    build_engineering_apply_execution_plan,
)
from app.services.engineering_change_proposal import (
    EngineeringChangeProposalService,
)
from app.services.engineering_repository_reader import (
    EngineeringRepositoryReader,
)


PERSONAL = WorkspaceScope(WorkspaceId.PERSONAL)


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "backend").mkdir()
    (root / "backend" / "app.py").write_bytes(b"value = 1\n")
    return root


def _proposal(
    root: Path,
    operation: EngineeringChangeOperation,
    path: str,
    content: str,
):
    return EngineeringChangeProposalService(
        EngineeringRepositoryReader(root)
    ).propose(
        EngineeringChangeDraft(
            workspace_scope=PERSONAL,
            operation=operation,
            relative_path=path,
            proposed_content=content,
        )
    )


def _approved(root: Path, proposal):
    store = EngineeringApplyApprovalStore(
        approval_id_factory=lambda: "approval-1"
    )
    approvals = EngineeringApplyApprovalService(
        store=store,
        workspace_scope=PERSONAL,
    )
    review = approvals.propose(proposal).proposal
    decision = approvals.approve(
        review.approval_id,
        review.proposal_digest,
    )
    assert decision.approved is not None
    execution = EngineeringApplyExecutionService(
        approval_store=store,
        workspace_scope=PERSONAL,
        repository_root=root,
    )
    return store, decision.approved, execution


def test_d108_create_plan_projection_is_exact(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    proposal = _proposal(
        root,
        EngineeringChangeOperation.CREATE_TEXT,
        "backend/new.py",
        "value = 2\n",
    )
    _, approved, _ = _approved(root, proposal)

    command, planning, plan_digest = build_engineering_apply_execution_plan(
        approved
    )

    assert command.request_id == approved.approval_id
    assert command.command == "tool.execute"
    assert command.arguments == {
        "adapter_id": "tool.filesystem.create_text",
        "operation": "create_text",
        "parameters": {
            "path": "backend/new.py",
            "content": "value = 2\n",
        },
    }
    assert planning.plan is not None
    assert planning.plan.owner_approval_required is True
    assert plan_digest != approved.proposal_digest


def test_d108_replace_plan_projection_uses_exact_base_sha(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    proposal = _proposal(
        root,
        EngineeringChangeOperation.REPLACE_TEXT,
        "backend/app.py",
        "value = 2\n",
    )
    _, approved, _ = _approved(root, proposal)

    command, planning, _ = build_engineering_apply_execution_plan(approved)

    assert planning.plan is not None
    assert command.arguments["parameters"] == {
        "path": "backend/app.py",
        "content": "value = 2\n",
        "expected_sha256": hashlib.sha256(b"value = 1\n").hexdigest(),
    }


def test_d108_create_applies_exact_bytes_once(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    target = root / "backend" / "new.py"
    proposal = _proposal(
        root,
        EngineeringChangeOperation.CREATE_TEXT,
        "backend/new.py",
        "value = 2\n",
    )
    store, approved, execution = _approved(root, proposal)

    outcome = execution.apply(
        approved.approval_id,
        approved.proposal_digest,
    )

    assert outcome.status == "applied"
    assert target.read_bytes() == b"value = 2\n"
    assert store.state(approved.approval_id) == "applied"

    with pytest.raises(EngineeringApplyNotApprovedError):
        execution.apply(
            approved.approval_id,
            approved.proposal_digest,
        )

    assert target.read_bytes() == b"value = 2\n"


def test_d108_replace_applies_exact_bytes_once(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    target = root / "backend" / "app.py"
    proposal = _proposal(
        root,
        EngineeringChangeOperation.REPLACE_TEXT,
        "backend/app.py",
        "value = 2\n",
    )
    store, approved, execution = _approved(root, proposal)

    outcome = execution.apply(
        approved.approval_id,
        approved.proposal_digest,
    )

    assert outcome.status == "applied"
    assert target.read_bytes() == b"value = 2\n"
    assert store.state(approved.approval_id) == "applied"


def test_d108_create_stale_state_never_overwrites(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    target = root / "backend" / "new.py"
    proposal = _proposal(
        root,
        EngineeringChangeOperation.CREATE_TEXT,
        "backend/new.py",
        "proposal = True\n",
    )
    store, approved, execution = _approved(root, proposal)

    target.write_bytes(b"external = True\n")

    outcome = execution.apply(
        approved.approval_id,
        approved.proposal_digest,
    )

    assert outcome.status == "stale"
    assert target.read_bytes() == b"external = True\n"
    assert store.state(approved.approval_id) == "stale"


def test_d108_replace_stale_state_never_overwrites(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    target = root / "backend" / "app.py"
    proposal = _proposal(
        root,
        EngineeringChangeOperation.REPLACE_TEXT,
        "backend/app.py",
        "value = 2\n",
    )
    store, approved, execution = _approved(root, proposal)

    target.write_bytes(b"value = 999\n")

    outcome = execution.apply(
        approved.approval_id,
        approved.proposal_digest,
    )

    assert outcome.status == "stale"
    assert target.read_bytes() == b"value = 999\n"
    assert store.state(approved.approval_id) == "stale"


def test_d108_malformed_post_claim_success_is_indeterminate(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    proposal = _proposal(
        root,
        EngineeringChangeOperation.CREATE_TEXT,
        "backend/new.py",
        "value = 2\n",
    )
    store, approved, execution = _approved(root, proposal)

    class FakeRuntime:
        def execute(self, request, authorization):
            return Result(
                request_id=request.request_id,
                status="succeeded",
                output={
                    "path": "backend/wrong.py",
                    "size_bytes": 1,
                    "sha256": "0" * 64,
                    "write_kind": "created",
                },
            )

    execution._runtime = FakeRuntime()  # type: ignore[attr-defined]

    outcome = execution.apply(
        approved.approval_id,
        approved.proposal_digest,
    )

    assert outcome.status == "indeterminate"
    assert store.state(approved.approval_id) == "indeterminate"
    assert not (root / "backend" / "new.py").exists()


def test_d108_runtime_exception_after_claim_is_indeterminate(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    proposal = _proposal(
        root,
        EngineeringChangeOperation.CREATE_TEXT,
        "backend/new.py",
        "value = 2\n",
    )
    store, approved, execution = _approved(root, proposal)

    class ExplodingRuntime:
        def execute(self, request, authorization):
            raise RuntimeError("boom")

    execution._runtime = ExplodingRuntime()  # type: ignore[attr-defined]

    outcome = execution.apply(
        approved.approval_id,
        approved.proposal_digest,
    )

    assert outcome.status == "indeterminate"
    assert store.state(approved.approval_id) == "indeterminate"
    assert not (root / "backend" / "new.py").exists()
