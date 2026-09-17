import logging
from typing import List, Optional
from fastapi import HTTPException, status
from app.core.database import get_supabase_client, check_database_connection
from app.models.project import ProjectResponse, DatabaseHealthResponse

logger = logging.getLogger("ai_investigator.project_service")


class ProjectService:
    """Service layer encapsulating project operations and Supabase queries."""

    @staticmethod
    def get_database_health() -> DatabaseHealthResponse:
        """Probe the database connection and return typed status."""
        is_connected, message = check_database_connection()
        return DatabaseHealthResponse(
            status="connected" if is_connected else "disconnected",
            database="supabase-postgresql",
            message=message,
        )

    @staticmethod
    def get_all_projects() -> List[ProjectResponse]:
        """
        Fetch all project records from the Supabase projects table.
        Ordered by created_at descending.
        """
        client = get_supabase_client()
        if not client:
            logger.error("Supabase client unavailable when attempting to fetch projects.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Database connection is not configured or unavailable. "
                    "Ensure SUPABASE_URL and SUPABASE_ANON_KEY are set in your environment."
                ),
            )

        try:
            response = (
                client.table("projects")
                .select("id, name, description, created_at")
                .order("created_at", desc=True)
                .execute()
            )

            data = response.data or []
            return [ProjectResponse(**item) for item in data]
        except Exception as exc:
            logger.error(f"Error querying projects table: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to query projects from Supabase: {str(exc)}",
            )

    @staticmethod
    def get_project_by_id(project_id: str) -> Optional[ProjectResponse]:
        """Fetch a specific project by UUID."""
        client = get_supabase_client()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection is not configured.",
            )

        try:
            response = (
                client.table("projects")
                .select("id, name, description, created_at")
                .eq("id", project_id)
                .execute()
            )
            data = response.data or []
            if not data:
                return None
            return ProjectResponse(**data[0])
        except Exception as exc:
            logger.error(f"Error querying project by id '{project_id}': {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to query project from Supabase: {str(exc)}",
            )
