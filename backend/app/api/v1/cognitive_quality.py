"""D156 exact-workspace read-only cognitive quality API."""
from __future__ import annotations
from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.api.dependencies import get_cognitive_quality_diagnostic_service, get_cognitive_quality_investigation_evidence_service, get_cognitive_quality_investigation_planning_service, get_cognitive_quality_summary_service
from app.api.dependencies import get_cognitive_quality_investigation_hypothesis_review_service
from app.schemas.api import ApiSuccess
from app.schemas.cognitive_quality import CognitiveQualitySummaryResponse, CognitiveQualityComparisonResponse
from app.schemas.cognitive_quality_diagnostic import CognitiveQualityDiagnosticResponse
from app.schemas.cognitive_quality_investigation import CognitiveQualityInvestigationPlanResponse
from app.schemas.cognitive_quality_investigation_evidence import CognitiveQualityInvestigationEvidencePacketResponse
from app.schemas.cognitive_quality_investigation_hypothesis_review import CognitiveQualityInvestigationHypothesisReviewResponse
from app.services.cognitive_quality_summary import CognitiveQualitySummaryService
from app.services.cognitive_quality_diagnostic_advisory import CognitiveQualityDiagnosticService
from app.services.cognitive_quality_investigation_planning import CognitiveQualityInvestigationPlanningService
from app.services.cognitive_quality_investigation_evidence import CognitiveQualityInvestigationEvidenceService
from app.services.cognitive_quality_investigation_hypothesis_review import CognitiveQualityInvestigationHypothesisReviewService

router=APIRouter(prefix="/cognitive-quality",tags=["cognitive-quality"])

@router.get("/summary",response_model=ApiSuccess[CognitiveQualitySummaryResponse],status_code=status.HTTP_200_OK)
def cognitive_quality_summary(service:Annotated[CognitiveQualitySummaryService,Depends(get_cognitive_quality_summary_service)],since:Annotated[datetime|None,Query()]=None,until:Annotated[datetime|None,Query()]=None):
    try: s=service.summarize(since=since,until=until)
    except ValueError: raise HTTPException(status_code=400,detail="Invalid cognitive quality summary filters.") from None
    return ApiSuccess(data=CognitiveQualitySummaryResponse.from_contract(s))

@router.get("/compare",response_model=ApiSuccess[CognitiveQualityComparisonResponse],status_code=status.HTTP_200_OK)
def cognitive_quality_compare(service:Annotated[CognitiveQualitySummaryService,Depends(get_cognitive_quality_summary_service)],reference_since:Annotated[datetime,Query()],reference_until:Annotated[datetime,Query()],candidate_since:Annotated[datetime,Query()],candidate_until:Annotated[datetime,Query()]):
    try: c=service.compare(reference_since=reference_since,reference_until=reference_until,candidate_since=candidate_since,candidate_until=candidate_until)
    except ValueError: raise HTTPException(status_code=400,detail="Invalid cognitive quality comparison filters.") from None
    return ApiSuccess(data=CognitiveQualityComparisonResponse.from_contract(c))

@router.get("/diagnostic",response_model=ApiSuccess[CognitiveQualityDiagnosticResponse],status_code=status.HTTP_200_OK)
def cognitive_quality_diagnostic(service:Annotated[CognitiveQualityDiagnosticService,Depends(get_cognitive_quality_diagnostic_service)],reference_since:Annotated[datetime,Query()],reference_until:Annotated[datetime,Query()],candidate_since:Annotated[datetime,Query()],candidate_until:Annotated[datetime,Query()]):
    advisory=service.diagnose(reference_since=reference_since,reference_until=reference_until,candidate_since=candidate_since,candidate_until=candidate_until)
    return ApiSuccess(data=CognitiveQualityDiagnosticResponse.from_contract(advisory))

@router.get("/investigation-plan",response_model=ApiSuccess[CognitiveQualityInvestigationPlanResponse],status_code=status.HTTP_200_OK)
def cognitive_quality_investigation_plan(service:Annotated[CognitiveQualityInvestigationPlanningService,Depends(get_cognitive_quality_investigation_planning_service)],reference_since:Annotated[datetime,Query()],reference_until:Annotated[datetime,Query()],candidate_since:Annotated[datetime,Query()],candidate_until:Annotated[datetime,Query()]):
    plan=service.plan(reference_since=reference_since,reference_until=reference_until,candidate_since=candidate_since,candidate_until=candidate_until)
    return ApiSuccess(data=CognitiveQualityInvestigationPlanResponse.from_contract(plan))

@router.get("/investigation-evidence",response_model=ApiSuccess[CognitiveQualityInvestigationEvidencePacketResponse],status_code=status.HTTP_200_OK)
def cognitive_quality_investigation_evidence(service:Annotated[CognitiveQualityInvestigationEvidenceService,Depends(get_cognitive_quality_investigation_evidence_service)],reference_since:Annotated[datetime,Query()],reference_until:Annotated[datetime,Query()],candidate_since:Annotated[datetime,Query()],candidate_until:Annotated[datetime,Query()]):
    packet=service.assemble(reference_since=reference_since,reference_until=reference_until,candidate_since=candidate_since,candidate_until=candidate_until)
    return ApiSuccess(data=CognitiveQualityInvestigationEvidencePacketResponse.from_contract(packet))

@router.get(
    "/investigation-hypothesis-review",
    response_model=ApiSuccess[CognitiveQualityInvestigationHypothesisReviewResponse],
    status_code=status.HTTP_200_OK,
)
def cognitive_quality_investigation_hypothesis_review(
    service: Annotated[
        CognitiveQualityInvestigationHypothesisReviewService,
        Depends(get_cognitive_quality_investigation_hypothesis_review_service),
    ],
    reference_since: Annotated[datetime, Query()],
    reference_until: Annotated[datetime, Query()],
    candidate_since: Annotated[datetime, Query()],
    candidate_until: Annotated[datetime, Query()],
):
    review = service.review(
        reference_since=reference_since,
        reference_until=reference_until,
        candidate_since=candidate_since,
        candidate_until=candidate_until,
    )
    return ApiSuccess(data=CognitiveQualityInvestigationHypothesisReviewResponse.from_contract(review))
