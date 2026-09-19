import logging
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.core.database import get_service_role_client
from app.models.investigation import (
    InvestigationStatus,
    EvidenceType,
    InvestigationCreateRequest,
    InvestigationUpdateRequest,
    InvestigationResponse,
    InvestigationDetailResponse,
)
from app.models.repository import RepositoryResponse
from app.services.evidence_service import EvidenceService

logger = logging.getLogger("ai_investigator.investigation_service")

# The four mandatory failure evidence categories required to transition to 'ready'
REQUIRED_EVIDENCE_FOR_READY = {
    EvidenceType.BUG_REPORT,
    EvidenceType.APPLICATION_LOG,
    EvidenceType.STACK_TRACE,
    EvidenceType.TEST_OUTPUT,
}


class InvestigationService:
    """Service layer managing investigation lifecycle, validation, and repository relationships."""

    @classmethod
    def _require_db_client(cls):
        """Ensure the dedicated service-role Supabase client is available."""
        client = get_service_role_client()
        if not client:
            logger.error("SUPABASE_SERVICE_ROLE_KEY is not configured for private investigation operations.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service role configuration missing for private investigation operations. Set SUPABASE_SERVICE_ROLE_KEY in server environment.",
            )
        return client

    @classmethod
    def create_investigation(cls, request: InvestigationCreateRequest) -> InvestigationResponse:
        """
        Create a new investigation case linked to an analyzed repository.
        Validates repository existence and status.
        """
        client = cls._require_db_client()

        # 1. Validate repository association
        try:
            try:
                repo_res = (
                    client.table("repositories")
                    .select("id, status")
                    .eq("id", request.repository_id)
                    .execute()
                )
            except Exception as select_exc:
                err_str = str(select_exc)
                if "42703" in err_str or "status does not exist" in err_str:
                    logger.warning(
                        "Column 'repositories.status' does not yet exist in the database. "
                        "Falling back to 'id' lookup. Apply data/phase3_repository_schema_fix.sql."
                    )
                    repo_res = (
                        client.table("repositories")
                        .select("id")
                        .eq("id", request.repository_id)
                        .execute()
                    )
                else:
                    raise select_exc

            if not repo_res.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Repository with ID '{request.repository_id}' not found.",
                )

            repo_data = repo_res.data[0]
            # Check if repository has error or is incomplete
            if repo_data.get("status") in ["error", "failed"]:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Repository '{request.repository_id}' is in a failed state and cannot be investigated.",
                )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Error querying repository: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to verify repository: {str(exc)}",
            )

        # 2. Insert investigation record
        record = {
            "repository_id": request.repository_id,
            "title": request.title.strip(),
            "description": request.description.strip() if request.description else None,
            "status": InvestigationStatus.DRAFT.value,
        }

        try:
            insert_res = client.table("investigations").insert(record).execute()
            if not insert_res.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database failed to return created investigation record.",
                )

            data = insert_res.data[0]
            return InvestigationResponse(
                id=data["id"],
                repository_id=data["repository_id"],
                title=data["title"],
                description=data.get("description"),
                status=InvestigationStatus(data["status"]),
                evidence_count=0,
                created_at=data["created_at"],
                updated_at=data["updated_at"],
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Error creating investigation: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Database error creating investigation: {str(exc)}",
            )

    @classmethod
    def list_investigations(cls) -> List[InvestigationResponse]:
        """Fetch all investigation records ordered by created_at descending."""
        client = cls._require_db_client()

        try:
            # Retrieve investigations
            inv_res = (
                client.table("investigations")
                .select("id, repository_id, title, description, status, created_at, updated_at")
                .order("created_at", desc=True)
                .execute()
            )
            invs = inv_res.data or []
            if not invs:
                return []

            # Retrieve evidence count mapping
            evidence_res = (
                client.table("investigation_evidence")
                .select("investigation_id")
                .execute()
            )
            evidence_counts = {}
            for row in (evidence_res.data or []):
                inv_id = row.get("investigation_id")
                if inv_id:
                    evidence_counts[inv_id] = evidence_counts.get(inv_id, 0) + 1

            return [
                InvestigationResponse(
                    id=item["id"],
                    repository_id=item["repository_id"],
                    title=item["title"],
                    description=item.get("description"),
                    status=InvestigationStatus(item["status"]),
                    evidence_count=evidence_counts.get(item["id"], 0),
                    created_at=item["created_at"],
                    updated_at=item["updated_at"],
                )
                for item in invs
            ]
        except Exception as exc:
            logger.error(f"Error listing investigations: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to query investigations: {str(exc)}",
            )

    @classmethod
    def get_investigation(cls, investigation_id: str) -> InvestigationDetailResponse:
        """Fetch full details of an investigation, including repository and attached evidence."""
        client = cls._require_db_client()

        try:
            # 1. Fetch investigation record
            inv_res = (
                client.table("investigations")
                .select("*")
                .eq("id", investigation_id)
                .execute()
            )
            if not inv_res.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Investigation with ID '{investigation_id}' not found.",
                )

            inv_data = inv_res.data[0]

            # 2. Fetch associated repository
            repo_response = None
            repo_res = (
                client.table("repositories")
                .select("*")
                .eq("id", inv_data["repository_id"])
                .execute()
            )
            if repo_res.data:
                repo_response = RepositoryResponse(**repo_res.data[0])

            # 3. Fetch evidence list
            evidence_list = EvidenceService.get_evidence_for_investigation(investigation_id)

            inv_response = InvestigationResponse(
                id=inv_data["id"],
                repository_id=inv_data["repository_id"],
                title=inv_data["title"],
                description=inv_data.get("description"),
                status=InvestigationStatus(inv_data["status"]),
                evidence_count=len(evidence_list),
                created_at=inv_data["created_at"],
                updated_at=inv_data["updated_at"],
            )

            return InvestigationDetailResponse(
                investigation=inv_response,
                repository=repo_response,
                evidence=evidence_list,
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Error fetching investigation detail for '{investigation_id}': {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to retrieve investigation detail: {str(exc)}",
            )

    @classmethod
    def update_investigation(
        cls,
        investigation_id: str,
        request: InvestigationUpdateRequest,
    ) -> InvestigationResponse:
        """
        Update investigation metadata or status.
        ENFORCES STRICT REQUIREMENT:
        Cannot transition status to 'ready' unless all 4 evidence categories exist.
        """
        client = cls._require_db_client()

        # 1. Verify existence
        try:
            existing_res = (
                client.table("investigations")
                .select("*")
                .eq("id", investigation_id)
                .execute()
            )
            if not existing_res.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Investigation with ID '{investigation_id}' not found.",
                )
            existing = existing_res.data[0]
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Error fetching investigation before update: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Database error: {str(exc)}",
            )

        updates = {}
        if request.title is not None:
            updates["title"] = request.title.strip()
        if request.description is not None:
            updates["description"] = request.description.strip()

        # 2. Status Transition Validation
        if request.status is not None:
            if request.status == InvestigationStatus.READY:
                # Query all evidence attached to this investigation
                evidence_res = (
                    client.table("investigation_evidence")
                    .select("evidence_type")
                    .eq("investigation_id", investigation_id)
                    .execute()
                )
                present_types = {row["evidence_type"] for row in (evidence_res.data or [])}
                missing_types = [t.value for t in REQUIRED_EVIDENCE_FOR_READY if t.value not in present_types]

                if missing_types:
                    missing_str = ", ".join(missing_types)
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Investigation cannot be marked ready. Missing evidence: {missing_str}.",
                    )

            updates["status"] = request.status.value

        if not updates:
            # Nothing to update; return current state
            evidence_list = EvidenceService.get_evidence_for_investigation(investigation_id)
            return InvestigationResponse(
                id=existing["id"],
                repository_id=existing["repository_id"],
                title=existing["title"],
                description=existing.get("description"),
                status=InvestigationStatus(existing["status"]),
                evidence_count=len(evidence_list),
                created_at=existing["created_at"],
                updated_at=existing["updated_at"],
            )

        updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        try:
            upd_res = (
                client.table("investigations")
                .update(updates)
                .eq("id", investigation_id)
                .execute()
            )
            if not upd_res.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database failed to return updated investigation.",
                )

            data = upd_res.data[0]
            evidence_list = EvidenceService.get_evidence_for_investigation(investigation_id)
            return InvestigationResponse(
                id=data["id"],
                repository_id=data["repository_id"],
                title=data["title"],
                description=data.get("description"),
                status=InvestigationStatus(data["status"]),
                evidence_count=len(evidence_list),
                created_at=data["created_at"],
                updated_at=data["updated_at"],
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Error updating investigation '{investigation_id}': {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to update investigation: {str(exc)}",
            )

    @classmethod
    def delete_investigation(cls, investigation_id: str) -> None:
        """Delete an investigation record (cascading deletes to attached evidence)."""
        client = cls._require_db_client()

        try:
            client.table("investigations").delete().eq("id", investigation_id).execute()
        except Exception as exc:
            logger.error(f"Error deleting investigation '{investigation_id}': {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to delete investigation: {str(exc)}",
            )
