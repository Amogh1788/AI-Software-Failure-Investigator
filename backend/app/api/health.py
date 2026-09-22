import shutil
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.models.project import HealthResponse, DatabaseHealthResponse
from app.services.project_service import ProjectService

router = APIRouter(prefix="/health", tags=["Health Checks"])


@router.get("", response_model=HealthResponse, summary="Backend health probe (liveness)")
def get_health() -> HealthResponse:
    """
    Probe the FastAPI backend process liveness.
    Returns HTTP 200 with service metadata.
    """
    return HealthResponse(status="ok", service=settings.SERVICE_NAME)


@router.get("/live", summary="Kubernetes / Orchestrator liveness probe")
def get_liveness():
    """
    Confirms only that the FastAPI process is alive and accepting connections.
    Does not evaluate downstream dependencies.
    """
    return {
        "status": "ok",
        "service": settings.SERVICE_NAME,
        "probe": "liveness",
    }


@router.get("/ready", summary="Deep dependency readiness probe")
def get_readiness():
    """
    Deep readiness check for cloud orchestrators.
    Verifies:
      1. Git executable is installed and available in system PATH.
      2. Supabase PostgreSQL database is reachable.
    Returns HTTP 200 if all dependencies are healthy; HTTP 503 if any dependency fails.
    """
    # 1. Check Git availability
    git_path = shutil.which("git")
    git_status = "available" if git_path else "missing"

    # 2. Check Database connectivity
    db_health = ProjectService.get_database_health()
    db_status = "connected" if db_health.status == "connected" else "disconnected"

    is_ready = (git_status == "available") and (db_status == "connected")

    payload = {
        "status": "ready" if is_ready else "unavailable",
        "service": settings.SERVICE_NAME,
        "probe": "readiness",
        "dependencies": {
            "database": db_status,
            "git": git_status,
        },
    }

    if not is_ready:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload)

    return payload


@router.get("/db", response_model=DatabaseHealthResponse, summary="Database connection probe (backward-compatible)")
def get_database_health() -> DatabaseHealthResponse:
    """
    Probe real connectivity to Supabase PostgreSQL via the backend service.
    Maintained for backward compatibility.
    """
    return ProjectService.get_database_health()
