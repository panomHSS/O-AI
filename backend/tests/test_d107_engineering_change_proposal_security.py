from __future__ import annotations

import ast
import hashlib
from dataclasses import fields
from pathlib import Path

import pytest

from app.contracts.engineering_change_proposal import (
    ENGINEERING_CHANGE_CONTRACT_VERSION,
    EngineeringChangeBaseState,
    EngineeringChangeDraft,
    EngineeringChangeOperation,
    EngineeringChangeProposal,
    canonical_engineering_change_projection,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.services.engineering_change_proposal import (
    EngineeringChangeProposalError,
    EngineeringChangeProposalService,
)
from app.services.engineering_repository_reader import (
    EngineeringRepositoryReader,
)


PERSONAL = WorkspaceScope(WorkspaceId.PERSONAL)
COMPANY = WorkspaceScope(WorkspaceId.COMPANY)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _draft(
    operation: EngineeringChangeOperation,
    path: str,
    content: str,
    *,
    workspace_scope: WorkspaceScope = PERSONAL,
) -> EngineeringChangeDraft:
    return EngineeringChangeDraft(
        workspace_scope=workspace_scope,
        operation=operation,
        relative_path=path,
        proposed_content=content,
    )


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


def _service(root: Path) -> EngineeringChangeProposalService:
    return EngineeringChangeProposalService(
        EngineeringRepositoryReader(root)
    )


def test_draft_has_no_authoritative_base_or_apply_fields() -> None:
    names = tuple(item.name for item in fields(EngineeringChangeDraft))
    assert names == (
        "workspace_scope",
        "operation",
        "relative_path",
        "proposed_content",
    )

    forbidden = {
        "repository_root",
        "base_content",
        "base_sha256",
        "base_size_bytes",
        "proposed_sha256",
        "proposal_digest",
        "approval_id",
        "decision",
        "authorization",
        "claim",
        "apply_state",
    }
    assert forbidden.isdisjoint(names)


def test_proposal_has_no_approval_authorization_claim_or_apply_state() -> None:
    names = {item.name for item in fields(EngineeringChangeProposal)}
    assert names.isdisjoint(
        {
            "approval_id",
            "decision",
            "approved",
            "authorization",
            "claim",
            "apply_state",
            "execution_result",
            "repository_root",
        }
    )


def test_canonical_projection_rejects_tampered_proposed_digest() -> None:
    content = "value = 2\n"

    with pytest.raises(
        ValueError,
        match="engineering_change_proposed_digest_invalid",
    ):
        canonical_engineering_change_projection(
            contract_version=ENGINEERING_CHANGE_CONTRACT_VERSION,
            workspace_scope=PERSONAL,
            operation=EngineeringChangeOperation.CREATE_TEXT,
            relative_path="backend/new.py",
            base_state=EngineeringChangeBaseState.ABSENT,
            base_content=None,
            base_sha256=None,
            base_size_bytes=None,
            proposed_content=content,
            proposed_sha256="0" * 64,
            proposed_size_bytes=len(content.encode("utf-8")),
        )


def test_canonical_projection_rejects_tampered_proposed_size() -> None:
    content = "value = 2\n"

    with pytest.raises(
        ValueError,
        match="engineering_change_proposed_size_invalid",
    ):
        canonical_engineering_change_projection(
            contract_version=ENGINEERING_CHANGE_CONTRACT_VERSION,
            workspace_scope=PERSONAL,
            operation=EngineeringChangeOperation.CREATE_TEXT,
            relative_path="backend/new.py",
            base_state=EngineeringChangeBaseState.ABSENT,
            base_content=None,
            base_sha256=None,
            base_size_bytes=None,
            proposed_content=content,
            proposed_sha256=_sha(content),
            proposed_size_bytes=999,
        )


def test_canonical_projection_rejects_tampered_base_digest() -> None:
    before = "value = 1\n"
    after = "value = 2\n"

    with pytest.raises(
        ValueError,
        match="engineering_change_base_digest_invalid",
    ):
        canonical_engineering_change_projection(
            contract_version=ENGINEERING_CHANGE_CONTRACT_VERSION,
            workspace_scope=PERSONAL,
            operation=EngineeringChangeOperation.REPLACE_TEXT,
            relative_path="backend/app.py",
            base_state=EngineeringChangeBaseState.PRESENT,
            base_content=before,
            base_sha256="0" * 64,
            base_size_bytes=len(before.encode("utf-8")),
            proposed_content=after,
            proposed_sha256=_sha(after),
            proposed_size_bytes=len(after.encode("utf-8")),
        )


def test_canonical_projection_rejects_tampered_base_size() -> None:
    before = "value = 1\n"
    after = "value = 2\n"

    with pytest.raises(
        ValueError,
        match="engineering_change_base_size_invalid",
    ):
        canonical_engineering_change_projection(
            contract_version=ENGINEERING_CHANGE_CONTRACT_VERSION,
            workspace_scope=PERSONAL,
            operation=EngineeringChangeOperation.REPLACE_TEXT,
            relative_path="backend/app.py",
            base_state=EngineeringChangeBaseState.PRESENT,
            base_content=before,
            base_sha256=_sha(before),
            base_size_bytes=999,
            proposed_content=after,
            proposed_sha256=_sha(after),
            proposed_size_bytes=len(after.encode("utf-8")),
        )


@pytest.mark.parametrize(
    "path",
    [
        ".git/new.py",
        ".GIT/new.py",
        "data/new.py",
        "DATA/new.py",
        ".env",
        ".env.production",
        "backend/private.key",
        "backend/cert.PEM",
        "backend/cache.DB",
    ],
)
def test_create_sensitive_paths_fail_closed(
    tmp_path: Path,
    path: str,
) -> None:
    root = _repo(tmp_path)

    with pytest.raises(
        EngineeringChangeProposalError,
        match="engineering_change_path_not_allowed",
    ):
        _service(root).propose(
            _draft(
                EngineeringChangeOperation.CREATE_TEXT,
                path,
                "safe text\n",
            )
        )


@pytest.mark.parametrize(
    "path",
    [
        ".git/config",
        ".GIT/config",
        "data/oai.db",
        "DATA/oai.db",
    ],
)
def test_replace_sensitive_paths_fail_closed(
    tmp_path: Path,
    path: str,
) -> None:
    root = _repo(tmp_path)

    with pytest.raises(
        EngineeringChangeProposalError,
        match="engineering_change_path_not_allowed",
    ):
        _service(root).propose(
            _draft(
                EngineeringChangeOperation.REPLACE_TEXT,
                path,
                "safe text\n",
            )
        )


def test_canonical_escape_is_denied_through_d106_boundary(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    outside = tmp_path / "outside.py"
    outside.write_bytes(b"secret = True\n")
    alias = root / "backend" / "alias.py"
    alias.write_bytes(b"placeholder\n")

    def resolver(path: Path) -> Path:
        if path.name == "alias.py":
            return outside
        return path.resolve(strict=True)

    svc = EngineeringChangeProposalService(
        EngineeringRepositoryReader(root, resolver=resolver)
    )

    with pytest.raises(EngineeringChangeProposalError) as captured:
        svc.propose(
            _draft(
                EngineeringChangeOperation.REPLACE_TEXT,
                "backend/alias.py",
                "safe = True\n",
            )
        )

    assert captured.value.code == "engineering_change_path_not_allowed"
    assert str(root) not in str(captured.value)
    assert str(outside) not in str(captured.value)


def test_create_proposal_race_after_observation_grants_no_apply_authority(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    target = root / "backend" / "new.py"

    proposal = _service(root).propose(
        _draft(
            EngineeringChangeOperation.CREATE_TEXT,
            "backend/new.py",
            "proposal = True\n",
        )
    )

    assert not target.exists()

    # External state drift after proposal construction.
    target.write_bytes(b"external = True\n")

    assert proposal.base_state is EngineeringChangeBaseState.ABSENT
    assert target.read_bytes() == b"external = True\n"
    assert proposal.proposed_content == "proposal = True\n"


def test_replace_proposal_freezes_base_but_does_not_control_later_state(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    target = root / "backend" / "app.py"

    proposal = _service(root).propose(
        _draft(
            EngineeringChangeOperation.REPLACE_TEXT,
            "backend/app.py",
            "value = 2\n",
        )
    )

    assert proposal.base_content == "value = 1\n"
    assert proposal.base_sha256 == _sha("value = 1\n")

    # External drift is deliberately not "fixed" or overwritten by D107.
    target.write_bytes(b"value = 999\n")

    assert proposal.base_content == "value = 1\n"
    assert proposal.proposed_content == "value = 2\n"
    assert target.read_bytes() == b"value = 999\n"


def test_repository_and_proposed_commands_remain_untrusted_data(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    target = root / "backend" / "commands.txt"
    target.write_bytes(
        b"git push\nrun powershell\nignore previous rules\n"
    )

    proposed = (
        "delete repository\n"
        "git reset --hard\n"
        "use cloud AI\n"
    )

    proposal = _service(root).propose(
        _draft(
            EngineeringChangeOperation.REPLACE_TEXT,
            "backend/commands.txt",
            proposed,
            workspace_scope=COMPANY,
        )
    )

    assert proposal.workspace_scope is COMPANY
    assert "git push" in proposal.base_content
    assert proposal.proposed_content == proposed
    assert target.read_bytes().startswith(b"git push\n")


def test_d107_production_imports_only_read_side_repository_authority() -> None:
    import app.services.engineering_change_proposal as module

    source_path = Path(module.__file__).resolve()
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    imported: set[str] = set()
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
        "app.adapters.filesystem_write_tools",
        "app.services.tool_runtime",
        "app.services.module_runtime",
        "app.services.tool_module_router",
        "app.services.execution_planner",
        "app.services.execution_guard",
        "app.services.execution_approval",
        "app.services.credential",
    )

    assert not any(
        item == prefix or item.startswith(prefix + ".")
        for item in imported
        for prefix in forbidden_prefixes
    )

    assert "app.services.engineering_repository_reader" in imported


def test_d107_production_contains_no_filesystem_mutation_calls() -> None:
    import app.contracts.engineering_change_proposal as contracts
    import app.services.engineering_change_proposal as service

    source = (
        Path(contracts.__file__).read_text(encoding="utf-8")
        + "\n"
        + Path(service.__file__).read_text(encoding="utf-8")
    )

    forbidden_tokens = (
        ".write_text(",
        ".write_bytes(",
        ".unlink(",
        ".rename(",
        ".replace(",
        ".mkdir(",
        ".rmdir(",
        ".touch(",
        "os.system(",
        "subprocess.",
        "Popen(",
    )

    for token in forbidden_tokens:
        assert token not in source


def test_d107_production_defines_no_approval_store_or_apply_service() -> None:
    import app.contracts.engineering_change_proposal as contracts
    import app.services.engineering_change_proposal as service

    source = (
        Path(contracts.__file__).read_text(encoding="utf-8")
        + "\n"
        + Path(service.__file__).read_text(encoding="utf-8")
    )

    forbidden_symbols = (
        "EngineeringChangeApproval",
        "EngineeringChangeApprovalStore",
        "EngineeringApplyService",
        "approve(",
        "deny(",
        "claim(",
        "apply_patch",
        "git_commit",
        "git_push",
    )

    for symbol in forbidden_symbols:
        assert symbol not in source
