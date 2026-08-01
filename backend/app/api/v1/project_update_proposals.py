from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_project_update_proposal_service
from app.schemas.api import ApiSuccess
from app.schemas.project_update_proposals import (
    CreateProjectUpdateProposalRequest,
    ProjectUpdateProposalListResponse,
    ProjectUpdateProposalResponse,
    ProposalStatus,
)
from app.services.project_update_proposals import ProjectUpdateProposalService


router = APIRouter(
    prefix="/project-update-proposals",
    tags=["project-update-proposals"],
)


@router.post(
    "",
    response_model=ApiSuccess[ProjectUpdateProposalResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_project_update_proposal(
    payload: CreateProjectUpdateProposalRequest,
    service: Annotated[
        ProjectUpdateProposalService,
        Depends(get_project_update_proposal_service),
    ],
) -> ApiSuccess[ProjectUpdateProposalResponse]:
    return ApiSuccess(data=service.create(payload))


@router.get(
    "/project/{project_id}",
    response_model=ApiSuccess[ProjectUpdateProposalListResponse],
)
def list_project_update_proposals(
    project_id: UUID,
    service: Annotated[
        ProjectUpdateProposalService,
        Depends(get_project_update_proposal_service),
    ],
    status_filter: Annotated[
        ProposalStatus | None,
        Query(alias="status"),
    ] = None,
) -> ApiSuccess[ProjectUpdateProposalListResponse]:
    return ApiSuccess(
        data=service.list_for_project(
            project_id,
            status_filter,
        )
    )


@router.get(
    "/{proposal_id}",
    response_model=ApiSuccess[ProjectUpdateProposalResponse],
)
def get_project_update_proposal(
    proposal_id: UUID,
    service: Annotated[
        ProjectUpdateProposalService,
        Depends(get_project_update_proposal_service),
    ],
) -> ApiSuccess[ProjectUpdateProposalResponse]:
    return ApiSuccess(data=service.get(proposal_id))


@router.post(
    "/{proposal_id}/approve",
    response_model=ApiSuccess[ProjectUpdateProposalResponse],
)
def approve_project_update_proposal(
    proposal_id: UUID,
    service: Annotated[
        ProjectUpdateProposalService,
        Depends(get_project_update_proposal_service),
    ],
) -> ApiSuccess[ProjectUpdateProposalResponse]:
    return ApiSuccess(data=service.approve(proposal_id))


@router.post(
    "/{proposal_id}/reject",
    response_model=ApiSuccess[ProjectUpdateProposalResponse],
)
def reject_project_update_proposal(
    proposal_id: UUID,
    service: Annotated[
        ProjectUpdateProposalService,
        Depends(get_project_update_proposal_service),
    ],
) -> ApiSuccess[ProjectUpdateProposalResponse]:
    return ApiSuccess(data=service.reject(proposal_id))