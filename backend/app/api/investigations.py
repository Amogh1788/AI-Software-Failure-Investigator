import logging
from typing import List
from fastapi import APIRouter, status, Response, HTTPException, Depends
from app.core.auth import get_current_user, AuthenticatedUser
from app.models.investigation import (
    InvestigationCreateRequest,
    InvestigationUpdateRequest,
    InvestigationResponse,
    InvestigationDetailResponse,
    EvidenceCreateRequest,
    EvidenceResponse,
)
from app.models.analysis import InvestigationAnalysisResponse
from app.services.investigation_service import InvestigationService
from app.services.evidence_service import EvidenceService
from app.services.analysis_service import AnalysisService

logger = logging.getLogger("ai_investigator.api.investigations")

router = APIRouter(prefix="/investigations", tags=["Investigations & Evidence"])


@router.post(
    "",
    response_model=InvestigationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an investigation case",
)
def create_investigation(
    request: InvestigationCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> InvestigationResponse:
    """
    Create a new investigation case linked to an analyzed repository.
    Initial status is set to 'draft'. Bound to authenticated owner.
    """
    return InvestigationService.create_investigation(request, user_id=current_user.id)


@router.get(
    "",
    response_model=List[InvestigationResponse],
    summary="List all investigation cases for authenticated user",
)
def list_investigations(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> List[InvestigationResponse]:
    """Retrieve all investigation cases belonging to the authenticated user."""
    return InvestigationService.list_investigations(user_id=current_user.id)


@router.get(
    "/{investigation_id}",
    response_model=InvestigationDetailResponse,
    summary="Get investigation case details",
)
def get_investigation(
    investigation_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> InvestigationDetailResponse:
    """Retrieve full details of an authorized investigation."""
    return InvestigationService.get_investigation(investigation_id, user_id=current_user.id)


@router.patch(
    "/{investigation_id}",
    response_model=InvestigationResponse,
    summary="Update investigation case",
)
def update_investigation(
    investigation_id: str,
    request: InvestigationUpdateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> InvestigationResponse:
    """
    Update title, description, or status ('draft' or 'ready').
    Transitioning to 'ready' strictly requires all 4 evidence types to be present.
    """
    return InvestigationService.update_investigation(investigation_id, request, user_id=current_user.id)


@router.delete(
    "/{investigation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an investigation case",
)
def delete_investigation(
    investigation_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete an investigation case and all its attached evidence."""
    InvestigationService.delete_investigation(investigation_id, user_id=current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{investigation_id}/evidence",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attach failure evidence to an investigation",
)
def add_evidence(
    investigation_id: str,
    request: EvidenceCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> EvidenceResponse:
    """
    Attach failure evidence (bug_report, application_log, stack_trace, test_output).
    Enforces strict size limits:
    - bug_report: 50 KB
    - application_log: 500 KB
    - stack_trace: 200 KB
    - test_output: 200 KB
    - aggregate evidence total per case: 2 MB
    Oversized inputs are rejected with HTTP 413.
    """
    return EvidenceService.add_evidence(investigation_id, request, user_id=current_user.id)


@router.get(
    "/{investigation_id}/evidence",
    response_model=List[EvidenceResponse],
    summary="List evidence attached to an investigation",
)
def get_investigation_evidence(
    investigation_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> List[EvidenceResponse]:
    """Retrieve all evidence items attached to an authorized investigation."""
    return EvidenceService.get_evidence_for_investigation(investigation_id, user_id=current_user.id)


@router.delete(
    "/{investigation_id}/evidence/{evidence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a single evidence item",
)
def delete_evidence(
    investigation_id: str,
    evidence_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete a single evidence item from an authorized investigation."""
    EvidenceService.delete_evidence(investigation_id, evidence_id, user_id=current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ====================================================================
# Phase 4 — Investigation Intelligence Engine Endpoints
# ====================================================================

@router.post(
    "/{investigation_id}/analyze",
    response_model=InvestigationAnalysisResponse,
    summary="Run Phase 4 investigation intelligence engine",
)
def analyze_investigation(
    investigation_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> InvestigationAnalysisResponse:
    """
    Executes deterministic evidence correlation and source ranking
    for an authorized investigation in 'ready' status.
    Transitions status to 'analyzing', runs the engine, and marks 'completed'.
    If analysis fails, reverts status to 'ready'.
    """
    return AnalysisService.analyze_investigation(investigation_id, user_id=current_user.id)


@router.get(
    "/{investigation_id}/analysis",
    response_model=InvestigationAnalysisResponse,
    summary="Get latest analysis results for an investigation",
)
def get_latest_analysis(
    investigation_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> InvestigationAnalysisResponse:
    """Retrieve the most recent analysis run results for an authorized investigation."""
    analysis = AnalysisService.get_latest_analysis(investigation_id, user_id=current_user.id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No analysis results found for investigation '{investigation_id}'.",
        )
    return analysis


@router.get(
    "/{investigation_id}/analysis/runs",
    response_model=List[InvestigationAnalysisResponse],
    summary="Get all historical analysis runs for an investigation",
)
def list_analysis_runs(
    investigation_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> List[InvestigationAnalysisResponse]:
    """Retrieve history of all analysis runs for an authorized investigation."""
    return AnalysisService.list_analysis_runs(investigation_id, user_id=current_user.id)
