from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_project_service
from app.schemas.api import ApiSuccess
from app.schemas.projects import (
    ChangeNextActionRequest, ChangeProjectStatusRequest, CreateProjectRequest,
    ProjectHistoryResponse, ProjectListResponse, ProjectResponse, ProjectStatus,
    RecordProjectProgressRequest, UpdateProjectDetailsRequest,
)
from app.services.projects import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ApiSuccess[ProjectResponse], status_code=status.HTTP_201_CREATED)
def create_project(payload: CreateProjectRequest, service: Annotated[ProjectService, Depends(get_project_service)]) -> ApiSuccess[ProjectResponse]:
    return ApiSuccess(data=service.create(payload))


@router.get("", response_model=ApiSuccess[ProjectListResponse])
def list_projects(service: Annotated[ProjectService, Depends(get_project_service)], page: Annotated[int, Query(ge=1)] = 1, page_size: Annotated[int, Query(ge=1, le=100)] = 25, status_filter: ProjectStatus | None = Query(default=None, alias="status")) -> ApiSuccess[ProjectListResponse]:
    return ApiSuccess(data=service.list(page, page_size, status_filter))


@router.get("/{project_id}", response_model=ApiSuccess[ProjectResponse])
def get_project(project_id: UUID, service: Annotated[ProjectService, Depends(get_project_service)]) -> ApiSuccess[ProjectResponse]:
    return ApiSuccess(data=service.get(project_id))


@router.patch("/{project_id}/details", response_model=ApiSuccess[ProjectResponse])
def update_details(project_id: UUID, payload: UpdateProjectDetailsRequest, service: Annotated[ProjectService, Depends(get_project_service)]) -> ApiSuccess[ProjectResponse]:
    return ApiSuccess(data=service.update_details(project_id, payload))


@router.post("/{project_id}/progress", response_model=ApiSuccess[ProjectResponse])
def record_progress(project_id: UUID, payload: RecordProjectProgressRequest, service: Annotated[ProjectService, Depends(get_project_service)]) -> ApiSuccess[ProjectResponse]:
    return ApiSuccess(data=service.record_progress(project_id, payload))


@router.put("/{project_id}/next-action", response_model=ApiSuccess[ProjectResponse])
def change_next_action(project_id: UUID, payload: ChangeNextActionRequest, service: Annotated[ProjectService, Depends(get_project_service)]) -> ApiSuccess[ProjectResponse]:
    return ApiSuccess(data=service.change_next_action(project_id, payload))


@router.post("/{project_id}/status", response_model=ApiSuccess[ProjectResponse])
def change_status(project_id: UUID, payload: ChangeProjectStatusRequest, service: Annotated[ProjectService, Depends(get_project_service)]) -> ApiSuccess[ProjectResponse]:
    return ApiSuccess(data=service.change_status(project_id, payload))


@router.get("/{project_id}/history", response_model=ApiSuccess[ProjectHistoryResponse])
def history(project_id: UUID, service: Annotated[ProjectService, Depends(get_project_service)]) -> ApiSuccess[ProjectHistoryResponse]:
    return ApiSuccess(data=service.history(project_id))
