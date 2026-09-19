import logging
from typing import List
from fastapi import APIRouter, status, Response, HTTPException
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
def create_investigation(request: InvestigationCreateRequest) -> InvestigationResponse:
    """
    Create a new investigation case linked to an analyzed repository.
    Initial status is set to 'draft'.
    """
    return InvestigationService.create_investigation(request)


@router.get(
    "",
    response_model=List[InvestigationResponse],
    summary="List all investigation cases",
)
def list_investigations() -> List[InvestigationResponse]:
    """Retrieve all previously created investigation cases with evidence counts."""
    return InvestigationService.list_investigations()


@router.get(
    "/{investigation_id}",
    response_model=InvestigationDetailResponse,
    summary="Get investigation case details",
)
def get_investigation(investigation_id: str) -> InvestigationDetailResponse:
    """Retrieve full details of an investigation, including repository info and attached evidence."""
    return InvestigationService.get_investigation(investigation_id)


@router.patch(
    "/{investigation_id}",
    response_model=InvestigationResponse,
    summary="Update investigation case",
)
def update_investigation(
    investigation_id: str,
    request: InvestigationUpdateRequest,
) -> InvestigationResponse:
    """
    Update title, description, or status ('draft' or 'ready').
    Transitioning to 'ready' strictly requires all 4 evidence types to be present.
    """
    return InvestigationService.update_investigation(investigation_id, request)


@router.delete(
    "/{investigation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an investigation case",
)
def delete_investigation(investigation_id: str):
    """Delete an investigation case and all its attached evidence."""
    InvestigationService.delete_investigation(investigation_id)
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
) -> EvidenceResponse:
    """
    Attach failure evidence (bug_report, application_log, stack_trace, test_output).
    Enforces strict size limits:
    - bug_report: 50 KB
    - application_log: 500 KB
    - stack_trace: 200 KB
    - test_output: 200 KB
    Oversized inputs are rejected with HTTP 413.
    """
    return EvidenceService.add_evidence(investigation_id, request)


@router.get(
    "/{investigation_id}/evidence",
    response_model=List[EvidenceResponse],
    summary="List evidence attached to an investigation",
)
def get_investigation_evidence(investigation_id: str) -> List[EvidenceResponse]:
    """Retrieve all evidence items attached to an investigation."""
    return EvidenceService.get_evidence_for_investigation(investigation_id)


@router.delete(
    "/{investigation_id}/evidence/{evidence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a single evidence item",
)
def delete_evidence(investigation_id: str, evidence_id: str):
    """Delete a single evidence item from an investigation."""
    EvidenceService.delete_evidence(investigation_id, evidence_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ====================================================================
# Phase 4 — Investigation Intelligence Engine Endpoints
# ====================================================================

@router.post(
    "/{investigation_id}/analyze",
    response_model=InvestigationAnalysisResponse,
    summary="Run Phase 4 investigation intelligence engine",
)
def analyze_investigation(investigation_id: str) -> InvestigationAnalysisResponse:
    """
    Executes deterministic evidence correlation and source ranking
    for an investigation in 'ready' status.
    Transitions status to 'analyzing', runs the engine, and marks 'completed'.
    If analysis fails, reverts status to 'ready'.
    """
    return AnalysisService.analyze_investigation(investigation_id)


@router.get(
    "/{investigation_id}/analysis",
    response_model=InvestigationAnalysisResponse,
    summary="Get latest analysis results for an investigation",
)
def get_latest_analysis(investigation_id: str) -> InvestigationAnalysisResponse:
    """Retrieve the most recent analysis run results for this investigation."""
    analysis = AnalysisService.get_latest_analysis(investigation_id)
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
def list_analysis_runs(investigation_id: str) -> List[InvestigationAnalysisResponse]:
    """Retrieve history of all analysis runs for this investigation."""
    return AnalysisService.list_analysis_runs(investigation_id)

