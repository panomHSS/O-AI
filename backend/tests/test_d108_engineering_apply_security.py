from __future__ import annotations

import ast
import inspect
import threading
from pathlib import Path

import pytest

from app.contracts.command import Result
from app.contracts.engineering_change_proposal import (
    EngineeringChangeBaseState,
    EngineeringChangeDraft,
    EngineeringChangeOperation,
    EngineeringChangeProposal,
)
from app.contracts.engineering_read import (
    EngineeringReadOperation,
)
from app.contracts.execution_authorization import OwnerApprovalEvidence
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.services.engineering_apply_approval import (
    EngineeringApplyAlreadyClaimedError,
    EngineeringApplyApprovalService,
    EngineeringApplyApprovalStore,
    EngineeringApplyDigestMismatchError,
    EngineeringApplyNotApprovedError,
    EngineeringApplyProposalInvalidError,
    EngineeringApplyWorkspaceMismatchError,
)
from app.services.engineering_apply_execution import (
    EngineeringApplyExecutionService,
    EngineeringApplyRootBindingError,
    build_engineering_apply_execution_plan,
)
from app.services.engineering_change_proposal import (
    EngineeringChangeProposalService,
)
from app.services.engineering_repository_reader import (
    EngineeringReadError,
    EngineeringRepositoryReader,
)
from app.services.execution_guard import execution_plan_digest


PERSONAL = WorkspaceScope(WorkspaceId.PERSONAL)
COMPANY = WorkspaceScope(WorkspaceId.COMPANY)


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "backend").mkdir()
    (root / "backend" / "app.py").write_bytes(b"value = 1\n")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_bytes(b"git internals")
    (root / "data").mkdir()
    (root / "data" / "oai.db").write_bytes(b"db")
    return root


def _proposal(
    root: Path,
    operation: EngineeringChangeOperation,
    path: str,
    content: str,
    *,
    workspace_scope: WorkspaceScope = PERSONAL,
):
    return EngineeringChangeProposalService(
        EngineeringRepositoryReader(root)
    ).propose(
        EngineeringChangeDraft(
            workspace_scope=workspace_scope,
            operation=operation,
            relative_path=path,
            proposed_content=content,
        )
    )


def _approved(
    root: Path,
    proposal,
    *,
    workspace_scope: WorkspaceScope = PERSONAL,
    approval_id: str = "approval-1",
):
    store = EngineeringApplyApprovalStore(
        approval_id_factory=lambda: approval_id,
    )
    approval_service = EngineeringApplyApprovalService(
        store=store,
        workspace_scope=workspace_scope,
    )
    pending = approval_service.propose(proposal).proposal
    decision = approval_service.approve(
        pending.approval_id,
        pending.proposal_digest,
    )
    assert decision.approved is not None
    execution = EngineeringApplyExecutionService(
        approval_store=store,
        workspace_scope=workspace_scope,
        repository_root=root,
    )
    return store, decision.approved, execution


def test_d108_apply_surface_accepts_no_path_content_root_or_plan_override() -> None:
    signature = inspect.signature(EngineeringApplyExecutionService.apply)
    assert tuple(signature.parameters) == (
        "self",
        "approval_id",
        "proposal_digest",
    )


def test_d108_cross_workspace_apply_fails_closed(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    proposal = _proposal(
        root,
        EngineeringChangeOperation.CREATE_TEXT,
        "backend/new.py",
        "value = 2\n",
        workspace_scope=PERSONAL,
    )
    store, approved, _ = _approved(root, proposal)

    wrong_workspace_execution = EngineeringApplyExecutionService(
        approval_store=store,
        workspace_scope=COMPANY,
        repository_root=root,
    )

    with pytest.raises(EngineeringApplyWorkspaceMismatchError):
        wrong_workspace_execution.apply(
            approved.approval_id,
            approved.proposal_digest,
        )

    assert not (root / "backend" / "new.py").exists()


def test_d108_digest_substitution_fails_closed_without_mutation(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    proposal = _proposal(
        root,
        EngineeringChangeOperation.CREATE_TEXT,
        "backend/new.py",
        "value = 2\n",
    )
    _, approved, execution = _approved(root, proposal)

    with pytest.raises(EngineeringApplyDigestMismatchError):
        execution.apply(
            approved.approval_id,
            "0" * 64,
        )

    assert not (root / "backend" / "new.py").exists()


def test_d108_tampered_server_snapshot_fails_closed(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    proposal = _proposal(
        root,
        EngineeringChangeOperation.CREATE_TEXT,
        "backend/new.py",
        "value = 2\n",
    )
    _, approved, execution = _approved(root, proposal)

    object.__setattr__(
        approved.proposal,
        "proposed_content",
        "tampered = True\n",
    )

    with pytest.raises(EngineeringApplyProposalInvalidError):
        execution.apply(
            approved.approval_id,
            approved.proposal_digest,
        )

    assert not (root / "backend" / "new.py").exists()


def test_d108_generic_plan_parameter_substitution_is_rejected_by_d36(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    proposal = _proposal(
        root,
        EngineeringChangeOperation.CREATE_TEXT,
        "backend/new.py",
        "value = 2\n",
    )
    _, approved, execution = _approved(root, proposal)

    command, planning, original_digest = (
        build_engineering_apply_execution_plan(approved)
    )
    assert planning.plan is not None

    planning.plan.steps[0].parameters["content"] = "evil = True\n"

    evidence = OwnerApprovalEvidence(
        request_id=approved.approval_id,
        plan_digest=original_digest,
        decision="approved",
    )
    authorization = execution._guard.authorize(  # type: ignore[attr-defined]
        command,
        planning,
        evidence,
    )

    assert authorization.status == "rejected"
    assert authorization.reason_code == "approval_plan_mismatch"
    assert authorization.source_plan_digest != original_digest
    assert not (root / "backend" / "new.py").exists()


def test_d108_plan_digest_domain_is_distinct_from_proposal_digest(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    proposal = _proposal(
        root,
        EngineeringChangeOperation.CREATE_TEXT,
        "backend/new.py",
        "value = 2\n",
    )
    _, approved, _ = _approved(root, proposal)

    _, planning, plan_digest = build_engineering_apply_execution_plan(approved)

    assert planning.plan is not None
    assert execution_plan_digest(planning.plan) == plan_digest
    assert plan_digest != approved.proposal_digest


def test_d108_sensitive_path_manual_proposal_is_blocked_before_claim(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    proposal = EngineeringChangeProposal(
        workspace_scope=PERSONAL,
        operation=EngineeringChangeOperation.CREATE_TEXT,
        relative_path=".git/new.txt",
        base_state=EngineeringChangeBaseState.ABSENT,
        base_content=None,
        base_sha256=None,
        base_size_bytes=None,
        proposed_content="must not write\n",
    )
    store, approved, execution = _approved(root, proposal)

    outcome = execution.apply(
        approved.approval_id,
        approved.proposal_digest,
    )

    assert outcome.status == "stale"
    assert store.state(approved.approval_id) == "stale"
    assert not (root / ".git" / "new.txt").exists()


def test_d108_invalid_repository_root_fails_closed(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    proposal = _proposal(
        root,
        EngineeringChangeOperation.CREATE_TEXT,
        "backend/new.py",
        "value = 2\n",
    )
    store, _, _ = _approved(root, proposal)

    with pytest.raises(EngineeringApplyRootBindingError):
        EngineeringApplyExecutionService(
            approval_store=store,
            workspace_scope=PERSONAL,
            repository_root=tmp_path / "missing-repository",
        )


def test_d108_create_race_after_d106_revalidation_becomes_stale(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    target = root / "backend" / "new.py"
    proposal = _proposal(
        root,
        EngineeringChangeOperation.CREATE_TEXT,
        "backend/new.py",
        "proposal = True\n",
    )
    store, approved, execution = _approved(root, proposal)

    base_reader = EngineeringRepositoryReader(root)

    class CreateRaceReader:
        triggered = False

        def read(self, request):
            try:
                return base_reader.read(request)
            except EngineeringReadError as exc:
                if (
                    not self.triggered
                    and request.operation is EngineeringReadOperation.STAT_PATH
                    and request.relative_path == "backend/new.py"
                    and exc.code == "engineering_path_not_found"
                ):
                    target.write_bytes(b"external = True\n")
                    self.triggered = True
                raise

    execution._reader = CreateRaceReader()  # type: ignore[attr-defined]

    outcome = execution.apply(
        approved.approval_id,
        approved.proposal_digest,
    )

    assert outcome.status == "stale"
    assert store.state(approved.approval_id) == "stale"
    assert target.read_bytes() == b"external = True\n"


def test_d108_replace_race_after_d106_revalidation_becomes_stale(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    target = root / "backend" / "app.py"
    proposal = _proposal(
        root,
        EngineeringChangeOperation.REPLACE_TEXT,
        "backend/app.py",
        "value = 2\n",
    )
    store, approved, execution = _approved(root, proposal)

    base_reader = EngineeringRepositoryReader(root)

    class ReplaceRaceReader:
        triggered = False

        def read(self, request):
            observed = base_reader.read(request)
            if (
                not self.triggered
                and request.operation is EngineeringReadOperation.READ_TEXT
                and request.relative_path == "backend/app.py"
            ):
                target.write_bytes(b"value = external\n")
                self.triggered = True
            return observed

    execution._reader = ReplaceRaceReader()  # type: ignore[attr-defined]

    outcome = execution.apply(
        approved.approval_id,
        approved.proposal_digest,
    )

    assert outcome.status == "stale"
    assert store.state(approved.approval_id) == "stale"
    assert target.read_bytes() == b"value = external\n"


def test_d108_concurrent_double_apply_has_one_claim_winner(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    target = root / "backend" / "new.py"
    proposal = _proposal(
        root,
        EngineeringChangeOperation.CREATE_TEXT,
        "backend/new.py",
        "value = 2\n",
    )
    store, approved, execution = _approved(root, proposal)

    original_runtime = execution._runtime  # type: ignore[attr-defined]
    entered = threading.Event()
    release = threading.Event()
    calls = []

    class BlockingRuntime:
        def execute(self, request, authorization):
            calls.append(request.request_id)
            entered.set()
            assert release.wait(timeout=5)
            return original_runtime.execute(request, authorization)

    execution._runtime = BlockingRuntime()  # type: ignore[attr-defined]

    first = {}

    def run_first() -> None:
        try:
            first["outcome"] = execution.apply(
                approved.approval_id,
                approved.proposal_digest,
            )
        except Exception as exc:  # pragma: no cover - diagnostic capture
            first["error"] = exc

    thread = threading.Thread(target=run_first)
    thread.start()
    assert entered.wait(timeout=5)

    # The losing concurrent caller may be rejected either at the approved-state
    # lookup (the winner has already changed state to claimed) or at the atomic
    # claim itself. Both are fail-closed and must result in zero second dispatch.
    with pytest.raises(
        (
            EngineeringApplyAlreadyClaimedError,
            EngineeringApplyNotApprovedError,
        )
    ):
        execution.apply(
            approved.approval_id,
            approved.proposal_digest,
        )

    release.set()
    thread.join(timeout=5)
    assert not thread.is_alive()

    assert "error" not in first
    assert first["outcome"].status == "applied"
    assert calls == [approved.approval_id]
    assert target.read_bytes() == b"value = 2\n"
    assert store.state(approved.approval_id) == "applied"


def test_d108_replay_after_applied_never_dispatches_again(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    target = root / "backend" / "new.py"
    proposal = _proposal(
        root,
        EngineeringChangeOperation.CREATE_TEXT,
        "backend/new.py",
        "value = 2\n",
    )
    _, approved, execution = _approved(root, proposal)

    first = execution.apply(
        approved.approval_id,
        approved.proposal_digest,
    )
    assert first.status == "applied"

    with pytest.raises(EngineeringApplyNotApprovedError):
        execution.apply(
            approved.approval_id,
            approved.proposal_digest,
        )

    assert target.read_bytes() == b"value = 2\n"


def test_d108_indeterminate_is_terminal_and_has_no_retry(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    target = root / "backend" / "new.py"
    proposal = _proposal(
        root,
        EngineeringChangeOperation.CREATE_TEXT,
        "backend/new.py",
        "value = 2\n",
    )
    store, approved, execution = _approved(root, proposal)
    original_runtime = execution._runtime  # type: ignore[attr-defined]

    class ExplodingRuntime:
        def execute(self, request, authorization):
            raise RuntimeError("simulated uncertain runtime failure")

    execution._runtime = ExplodingRuntime()  # type: ignore[attr-defined]

    outcome = execution.apply(
        approved.approval_id,
        approved.proposal_digest,
    )

    assert outcome.status == "indeterminate"
    assert store.state(approved.approval_id) == "indeterminate"
    assert not target.exists()

    execution._runtime = original_runtime  # type: ignore[attr-defined]

    with pytest.raises(EngineeringApplyNotApprovedError):
        execution.apply(
            approved.approval_id,
            approved.proposal_digest,
        )

    assert not target.exists()


def test_d108_malformed_success_metadata_is_indeterminate_and_terminal(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    target = root / "backend" / "new.py"
    proposal = _proposal(
        root,
        EngineeringChangeOperation.CREATE_TEXT,
        "backend/new.py",
        "value = 2\n",
    )
    store, approved, execution = _approved(root, proposal)

    class MalformedRuntime:
        def execute(self, request, authorization):
            return Result(
                request_id=request.request_id,
                status="succeeded",
                output={
                    "path": "backend/not-approved.py",
                    "size_bytes": 1,
                    "sha256": "0" * 64,
                    "write_kind": "created",
                },
            )

    execution._runtime = MalformedRuntime()  # type: ignore[attr-defined]

    outcome = execution.apply(
        approved.approval_id,
        approved.proposal_digest,
    )

    assert outcome.status == "indeterminate"
    assert store.state(approved.approval_id) == "indeterminate"
    assert not target.exists()


def test_d108_production_does_not_import_generic_d45_or_planner_coordinator() -> None:
    import app.services.engineering_apply_execution as module

    source_path = Path(module.__file__).resolve()
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    forbidden = (
        "app.services.execution_approval_service",
        "app.services.execution_approval",
        "app.services.execution_planner",
        "app.services.command_execution_coordinator",
    )

    assert not any(
        item == prefix or item.startswith(prefix + ".")
        for item in imported
        for prefix in forbidden
    )


def test_d108_has_no_shell_git_network_credential_or_ai_provider_imports() -> None:
    import app.services.engineering_apply_execution as execution
    import app.services.engineering_apply_approval as approval

    imported: set[str] = set()
    for module in (execution, approval):
        tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)

    forbidden_prefixes = (
        "subprocess",
        "socket",
        "urllib",
        "requests",
        "httpx",
        "git",
        "app.services.credential",
        "app.services.gmail",
        "app.services.calendar",
        "app.services.ai_router",
        "app.services.ai_provider",
    )

    assert not any(
        item == prefix or item.startswith(prefix + ".")
        for item in imported
        for prefix in forbidden_prefixes
    )


def test_d108_has_no_public_api_or_frontend_integration() -> None:
    import app.services.engineering_apply_execution as module

    backend_root = Path(module.__file__).resolve().parents[2]
    api_root = backend_root / "api"

    api_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in api_root.rglob("*.py")
    )
    assert "EngineeringApplyExecutionService" not in api_text
    assert "engineering_apply_execution" not in api_text
