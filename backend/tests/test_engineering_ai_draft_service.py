import hashlib
from pathlib import Path
from uuid import uuid4

import pytest

from app.contracts.ai import AI_ADAPTER_CONTRACT_VERSION, AIRequest, AIResult
from app.contracts.ai_discovery import AI_CAPABILITY_TEXT_GENERATION
from app.contracts.ai_route import CHATGPT_DEFAULT_ADAPTER_ID, LOCAL_AI_ADAPTER_ID
from app.contracts.engineering_ai_draft import EngineeringAIDraftRequest
from app.contracts.engineering_read import ENGINEERING_TEXT_MAX_BYTES
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.contracts.workspace_ai_policy import WorkspaceAIRouteMode, WorkspaceAIRoutingPolicy
from app.services.adapter_registry import AdapterRegistry
from app.services.ai_provider_routing import AIProviderRoutingPolicy
from app.services.ai_router import AIRouter
from app.services.ai_runtime import AIRuntime
from app.services.capability_permission_policy import CapabilityPermissionPolicy
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.engineering_ai_draft import EngineeringAIDraftError, EngineeringAIDraftService
from app.services.engineering_repository_reader import EngineeringRepositoryReader
from app.services.execution_guard import ExecutionGuard
from app.services.execution_planner import ExecutionPlanner


PERSONAL = WorkspaceScope(WorkspaceId.PERSONAL)


class RecordingAI:
    contract_version = AI_ADAPTER_CONTRACT_VERSION

    def __init__(
        self,
        adapter_id: str,
        *,
        response: str = "drafted\n",
        fail_if_called: bool = False,
    ) -> None:
        self.adapter_id = adapter_id
        self.response = response
        self.fail_if_called = fail_if_called
        self.requests: list[AIRequest] = []

    def generate(self, request: AIRequest) -> AIResult:
        if self.fail_if_called:
            raise AssertionError(f"{self.adapter_id} must not be called")
        self.requests.append(request)
        return AIResult(content=self.response)


class Discovery:
    def discover(self, adapter_id: str):
        class Value:
            status = "available"
            capability_ids = (AI_CAPABILITY_TEXT_GENERATION,)
            configured_model_id = "configured-model"
        return Value()


def build_service(
    root: Path,
    *,
    local: RecordingAI | None = None,
    cloud: RecordingAI | None = None,
    mode: WorkspaceAIRouteMode = WorkspaceAIRouteMode.CLOUD_PREFERRED,
    include_local: bool = True,
):
    local_adapter = local or RecordingAI(LOCAL_AI_ADAPTER_ID)
    cloud_adapter = cloud or RecordingAI(
        CHATGPT_DEFAULT_ADAPTER_ID,
        fail_if_called=True,
    )
    adapters = [cloud_adapter]
    if include_local:
        adapters.append(local_adapter)

    registry = AdapterRegistry(tuple(adapters))
    router = AIRouter(
        registry=registry,
        policy=AIProviderRoutingPolicy(
            default_adapter_id=CHATGPT_DEFAULT_ADAPTER_ID,
            enabled_adapter_ids=frozenset(
                {CHATGPT_DEFAULT_ADAPTER_ID, LOCAL_AI_ADAPTER_ID}
            ),
        ),
        workspace_policy=WorkspaceAIRoutingPolicy(
            workspace_id=WorkspaceId.PERSONAL,
            mode=mode,
        ),
    )
    permissions = CapabilityPermissionPolicy(registry=registry, permissions=())
    planner = ExecutionPlanner(
        registry=registry,
        decision_engine=CommandDecisionEngine(),
        ai_router=router,
        ai_discovery=Discovery(),  # type: ignore[arg-type]
        permission_policy=permissions,
    )
    guard = ExecutionGuard(registry=registry, permission_policy=permissions)
    runtime = AIRuntime(registry=registry)

    return (
        EngineeringAIDraftService(
            repository_reader=EngineeringRepositoryReader(root),
            execution_planner=planner,
            execution_guard=guard,
            ai_runtime=runtime,
        ),
        local_adapter if include_local else None,
        cloud_adapter,
    )


def req(path: str, instruction: str = "make the requested change"):
    return EngineeringAIDraftRequest(
        conversation_id=uuid4(),
        relative_path=path,
        instruction=instruction,
    )


def test_d110_existing_text_uses_d106_and_local_ai(tmp_path: Path) -> None:
    target = tmp_path / "app.py"
    target.write_bytes(b"value = 1\n")
    local = RecordingAI(LOCAL_AI_ADAPTER_ID, response="value = 2\n")
    svc, _, cloud = build_service(tmp_path, local=local)

    result = svc.draft(
        workspace_scope=PERSONAL,
        request=req("app.py", "change value to two"),
    )

    assert result.draft_operation == "replace_text"
    assert result.source_state == "present"
    assert result.source_sha256 == hashlib.sha256(b"value = 1\n").hexdigest()
    assert result.source_size_bytes == len(b"value = 1\n")
    assert result.draft_content == "value = 2\n"
    assert result.ai_adapter_id == LOCAL_AI_ADAPTER_ID
    assert len(local.requests) == 1
    assert cloud.requests == []
    prompt = local.requests[0].content
    assert "OWNER-SELECTED TARGET: app.py" in prompt
    assert "SERVER-DERIVED DRAFT OPERATION: replace_text" in prompt
    assert "change value to two" in prompt
    assert "value = 1" in prompt


def test_d110_absent_target_yields_create_hint_without_mutation(tmp_path: Path) -> None:
    local = RecordingAI(LOCAL_AI_ADAPTER_ID, response="new file\n")
    svc, _, _ = build_service(tmp_path, local=local)
    result = svc.draft(workspace_scope=PERSONAL, request=req("new.txt"))
    assert result.draft_operation == "create_text"
    assert result.source_state == "absent"
    assert result.source_sha256 is None
    assert result.source_size_bytes is None
    assert not (tmp_path / "new.txt").exists()


def test_d110_sensitive_path_fails_before_ai(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("SECRET=1\n", encoding="utf-8")
    local = RecordingAI(LOCAL_AI_ADAPTER_ID)
    svc, _, _ = build_service(tmp_path, local=local)
    with pytest.raises(
        EngineeringAIDraftError,
        match="engineering_ai_draft_path_not_allowed",
    ):
        svc.draft(workspace_scope=PERSONAL, request=req(".env"))
    assert local.requests == []


def test_d110_unsupported_and_oversized_sources_fail_before_ai(tmp_path: Path) -> None:
    (tmp_path / "folder").mkdir()
    (tmp_path / "binary.bin").write_bytes(b"abc\x00def")
    (tmp_path / "large.txt").write_bytes(
        b"x" * (ENGINEERING_TEXT_MAX_BYTES + 1)
    )
    local = RecordingAI(LOCAL_AI_ADAPTER_ID)
    svc, _, _ = build_service(tmp_path, local=local)

    for path in ("folder", "binary.bin"):
        with pytest.raises(
            EngineeringAIDraftError,
            match="engineering_ai_draft_target_unsupported",
        ):
            svc.draft(workspace_scope=PERSONAL, request=req(path))

    with pytest.raises(
        EngineeringAIDraftError,
        match="engineering_ai_draft_source_too_large",
    ):
        svc.draft(workspace_scope=PERSONAL, request=req("large.txt"))

    assert local.requests == []


def test_d110_oversized_output_fails_without_truncation(tmp_path: Path) -> None:
    local = RecordingAI(
        LOCAL_AI_ADAPTER_ID,
        response="x" * (ENGINEERING_TEXT_MAX_BYTES + 1),
    )
    svc, _, _ = build_service(tmp_path, local=local)
    with pytest.raises(
        EngineeringAIDraftError,
        match="engineering_ai_draft_too_large",
    ):
        svc.draft(workspace_scope=PERSONAL, request=req("new.txt"))
    assert len(local.requests) == 1
    assert not (tmp_path / "new.txt").exists()


def test_d110_local_unavailable_never_falls_back_to_cloud(tmp_path: Path) -> None:
    cloud = RecordingAI(
        CHATGPT_DEFAULT_ADAPTER_ID,
        response="must not be used",
        fail_if_called=True,
    )
    svc, local, cloud = build_service(
        tmp_path,
        cloud=cloud,
        include_local=False,
    )
    with pytest.raises(
        EngineeringAIDraftError,
        match="engineering_ai_draft_unavailable",
    ):
        svc.draft(workspace_scope=PERSONAL, request=req("new.txt"))
    assert local is None
    assert cloud.requests == []


def test_d110_workspace_policy_cannot_expand_local_authority(tmp_path: Path) -> None:
    local = RecordingAI(LOCAL_AI_ADAPTER_ID)
    svc, _, cloud = build_service(
        tmp_path,
        local=local,
        mode=WorkspaceAIRouteMode.CLOUD_ONLY,
    )
    with pytest.raises(
        EngineeringAIDraftError,
        match="engineering_ai_draft_unavailable",
    ):
        svc.draft(workspace_scope=PERSONAL, request=req("new.txt"))
    assert local.requests == []
    assert cloud.requests == []
