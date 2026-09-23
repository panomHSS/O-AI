# D118 owner-facing read-only Skill Catalog API tests.

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_engineering_investigation_workflow_service,
    get_skill_catalog,
    get_skill_invocation_bridge,
)
from app.api.v1.engineering import router
from app.contracts.ai_discovery import AI_CAPABILITY_TEXT_GENERATION
from app.contracts.skill import SkillDescriptor
from app.contracts.task_aware_ai_routing import AITaskKind
from app.services.builtin_skills import (
    ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL,
    build_builtin_skill_catalog,
)
from app.services.skill_catalog import SkillCatalog


_LOCAL_HEADERS = {"X-OAI-Local-Request": "1"}


def _unexpected_execution_dependency():
    raise AssertionError("catalog read requested an execution dependency")


def _client(catalog: SkillCatalog | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_skill_catalog] = (
        lambda: catalog or build_builtin_skill_catalog()
    )
    app.dependency_overrides[
        get_skill_invocation_bridge
    ] = _unexpected_execution_dependency
    app.dependency_overrides[
        get_engineering_investigation_workflow_service
    ] = _unexpected_execution_dependency
    return TestClient(app)


def _expected_public_descriptor(descriptor: SkillDescriptor) -> dict[str, object]:
    return {
        "skill_id": descriptor.skill_id,
        "version": descriptor.version,
        "display_name": descriptor.display_name,
        "description": descriptor.description,
        "task_kind": descriptor.task_kind.value,
        "required_ai_capability_ids": list(
            descriptor.required_ai_capability_ids
        ),
        "input_kind": descriptor.input_kind,
        "context_kind": descriptor.context_kind,
        "output_kind": descriptor.output_kind,
    }


def _descriptor(skill_id: str) -> SkillDescriptor:
    return SkillDescriptor(
        skill_id=skill_id,
        version="1",
        display_name=skill_id,
        description=f"Descriptor for {skill_id}.",
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
        required_ai_capability_ids=(AI_CAPABILITY_TEXT_GENERATION,),
        input_kind="engineering_investigation_request",
        context_kind="bounded_repository_evidence",
        output_kind="engineering_investigation_result",
    )


def test_d118_catalog_requires_existing_local_owner_marker() -> None:
    response = _client().get("/engineering/skills")

    assert response.status_code == 403


def test_d118_catalog_returns_exact_current_builtin_projection() -> None:
    response = _client().get(
        "/engineering/skills",
        headers=_LOCAL_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": {
            "skills": [
                _expected_public_descriptor(
                    ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL
                )
            ]
        },
    }


def test_d118_catalog_uses_deterministic_catalog_order() -> None:
    catalog = SkillCatalog(
        (
            _descriptor("zeta.skill"),
            _descriptor("alpha.skill"),
        )
    )

    response = _client(catalog).get(
        "/engineering/skills",
        headers=_LOCAL_HEADERS,
    )

    assert response.status_code == 200
    skills = response.json()["data"]["skills"]
    assert [item["skill_id"] for item in skills] == [
        "alpha.skill",
        "zeta.skill",
    ]


def test_d118_catalog_requires_no_body_workspace_or_conversation() -> None:
    response = _client().get(
        "/engineering/skills",
        headers=_LOCAL_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert "workspace_id" not in body["data"]
    assert "conversation_id" not in body["data"]
    assert set(body["data"]) == {"skills"}


def test_d118_public_projection_excludes_runtime_authority_fields() -> None:
    response = _client().get(
        "/engineering/skills",
        headers=_LOCAL_HEADERS,
    )

    assert response.status_code == 200
    item = response.json()["data"]["skills"][0]

    assert set(item) == {
        "skill_id",
        "version",
        "display_name",
        "description",
        "task_kind",
        "required_ai_capability_ids",
        "input_kind",
        "context_kind",
        "output_kind",
    }

    forbidden = {
        "handler",
        "callable",
        "service",
        "provider_id",
        "adapter_id",
        "model_id",
        "credential",
        "tool_id",
        "module_id",
        "connector_id",
        "invoke_url",
        "workspace_id",
        "conversation_id",
        "proposal",
        "approval",
        "apply",
    }
    assert forbidden.isdisjoint(item)


def test_d118_catalog_read_does_not_require_execution_dependencies() -> None:
    response = _client().get(
        "/engineering/skills",
        headers=_LOCAL_HEADERS,
    )

    assert response.status_code == 200
