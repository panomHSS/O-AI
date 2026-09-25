# D118 read-only Skill Catalog API security acceptance.

from __future__ import annotations

import inspect

from fastapi.routing import APIRoute

from app.api.dependencies import get_skill_catalog
from app.api.v1.engineering import list_engineering_skills, router
from app.schemas.skill_catalog import (
    SkillCatalogResponse,
    SkillDescriptorResponse,
)
from app.services.builtin_skills import (
    BUILTIN_SKILL_DESCRIPTORS,
    ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID,
)
from app.services.skill_catalog import SkillCatalog


_PUBLIC_DESCRIPTOR_FIELDS = {
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

_FORBIDDEN_AUTHORITY_FIELD_FRAGMENTS = {
    "handler",
    "callable",
    "service",
    "provider",
    "adapter",
    "model",
    "credential",
    "tool",
    "module",
    "connector",
    "runtime",
    "approval",
    "proposal",
    "apply",
    "invoke_url",
    "http_method",
    "execution_target",
    "workspace_id",
    "conversation_id",
}


def _skill_routes() -> list[APIRoute]:
    return [
        route
        for route in router.routes
        if isinstance(route, APIRoute)
        and route.path.startswith("/engineering/skills")
    ]


def test_d118_security_skill_route_surface_is_exact_and_bounded() -> None:
    surface = {
        (route.path, tuple(sorted(route.methods or set())))
        for route in _skill_routes()
    }

    assert surface == {
        ("/engineering/skills", ("GET",)),
        ("/engineering/skills/{skill_id}/invoke", ("POST",)),
    }


def test_d118_security_catalog_route_has_no_mutation_methods() -> None:
    catalog_routes = [
        route
        for route in _skill_routes()
        if route.path == "/engineering/skills"
    ]

    assert len(catalog_routes) == 1
    assert catalog_routes[0].methods == {"GET"}


def test_d118_security_public_descriptor_schema_is_exact() -> None:
    assert set(SkillDescriptorResponse.model_fields) == _PUBLIC_DESCRIPTOR_FIELDS
    assert set(SkillCatalogResponse.model_fields) == {"skills"}

    lowered_fields = {
        field_name.lower()
        for field_name in SkillDescriptorResponse.model_fields
    }
    assert all(
        fragment not in field_name
        for field_name in lowered_fields
        for fragment in _FORBIDDEN_AUTHORITY_FIELD_FRAGMENTS
    )


def test_d118_security_catalog_dependency_returns_metadata_only_catalog() -> None:
    catalog = get_skill_catalog()

    assert isinstance(catalog, SkillCatalog)
    assert catalog.list() == BUILTIN_SKILL_DESCRIPTORS
    assert tuple(
        descriptor.skill_id for descriptor in catalog.list()
    ) == (ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID,)


def test_d118_security_catalog_read_function_has_no_execution_call() -> None:
    source = inspect.getsource(list_engineering_skills)

    forbidden = (
        ".invoke(",
        ".investigate(",
        "SkillInvocationBridge",
        "EngineeringInvestigationWorkflowService",
        "provider",
        "adapter",
        "credential",
        "proposal",
        "approval",
        "apply",
    )

    assert all(token not in source for token in forbidden)
    assert "catalog.list()" in source


def test_d118_security_catalog_schema_exposes_no_invoke_locator() -> None:
    source = inspect.getsource(SkillDescriptorResponse)

    assert "invoke_url" not in source
    assert "http_method" not in source
    assert "handler" not in source
    assert "callable" not in source
    assert "execution_target" not in source
