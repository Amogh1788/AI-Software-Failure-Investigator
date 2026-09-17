from typing import List
from fastapi import APIRouter
from app.models.project import ProjectResponse
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=List[ProjectResponse], summary="List all projects")
def get_projects() -> List[ProjectResponse]:
    """
    Retrieve project records from Supabase PostgreSQL database.
    """
    return ProjectService.get_all_projects()
