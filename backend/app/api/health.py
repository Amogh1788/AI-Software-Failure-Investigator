from fastapi import APIRouter
from app.models.project import HealthResponse, DatabaseHealthResponse
from app.services.project_service import ProjectService

router = APIRouter(prefix="/health", tags=["Health Checks"])


@router.get("", response_model=HealthResponse, summary="Backend health probe")
def get_health() -> HealthResponse:
    """
    Probe the FastAPI backend health status.
    Expected response:
    {
        "status": "ok",
        "service": "ai-software-failure-investigator"
    }
    """
    return HealthResponse(status="ok", service="ai-software-failure-investigator")


@router.get("/db", response_model=DatabaseHealthResponse, summary="Database connection probe")
def get_database_health() -> DatabaseHealthResponse:
    """
    Probe real connectivity to Supabase PostgreSQL via the backend service.
    """
    return ProjectService.get_database_health()
