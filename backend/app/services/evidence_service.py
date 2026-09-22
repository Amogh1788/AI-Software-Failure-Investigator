import logging
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.core.config import settings
from app.core.database import get_service_role_client
from app.models.investigation import (
    EvidenceType,
    EvidenceCreateRequest,
    EvidenceResponse,
)

logger = logging.getLogger("ai_investigator.evidence_service")


class EvidenceService:
    """Service layer managing failure evidence validation, limits, ownership, and persistence."""

    # Size limits mapping by evidence type (in bytes)
    LIMITS_BY_TYPE = {
        EvidenceType.BUG_REPORT: settings.MAX_EVIDENCE_BUG_REPORT_BYTES,
        EvidenceType.APPLICATION_LOG: settings.MAX_EVIDENCE_APP_LOGS_BYTES,
        EvidenceType.STACK_TRACE: settings.MAX_EVIDENCE_STACK_TRACE_BYTES,
        EvidenceType.TEST_OUTPUT: settings.MAX_EVIDENCE_TEST_OUTPUT_BYTES,
    }

    @classmethod
    def _require_db_client(cls):
        """Ensure the dedicated service-role Supabase client is available."""
        client = get_service_role_client()
        if not client:
            logger.error("SUPABASE_SECRET_KEY is not configured for private investigation operations.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service role configuration missing for private investigation operations. Set SUPABASE_SECRET_KEY in server environment.",
            )
        return client

    @classmethod
    def validate_size_limit(cls, evidence_type: EvidenceType, content: str) -> int:
        """
        Calculate byte size of content and enforce strict size limits.
        Rejects oversized input with HTTP 413.
        """
        content_bytes = len(content.encode("utf-8"))
        max_limit = cls.LIMITS_BY_TYPE.get(evidence_type, settings.MAX_EVIDENCE_BUG_REPORT_BYTES)

        if content_bytes > max_limit:
            limit_kb = max_limit // 1024
            actual_kb = round(content_bytes / 1024, 1)
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=(
                    f"Evidence payload exceeds size limit for '{evidence_type.value}'. "
                    f"Maximum allowed: {limit_kb} KB ({max_limit} bytes), received: {actual_kb} KB ({content_bytes} bytes)."
                ),
            )
        return content_bytes

    @classmethod
    def add_evidence(
        cls,
        investigation_id: str,
        request: EvidenceCreateRequest,
        user_id: Optional[str] = None,
    ) -> EvidenceResponse:
        """Validate, store, and return new evidence for an authorized investigation."""
        # 1. Enforce individual byte size limit
        content_bytes = cls.validate_size_limit(request.evidence_type, request.content)

        client = cls._require_db_client()

        from app.services.investigation_service import InvestigationService
        InvestigationService.check_investigation_ownership(investigation_id, user_id, client=client)

        # 2. Enforce aggregate evidence size limit per case
        try:
            existing_ev_res = (
                client.table("investigation_evidence")
                .select("content")
                .eq("investigation_id", investigation_id)
                .execute()
            )
            existing_bytes = sum(
                len(row.get("content", "").encode("utf-8"))
                for row in (existing_ev_res.data or [])
            )
            if existing_bytes + content_bytes > settings.MAX_EVIDENCE_SIZE_TOTAL_PER_CASE_BYTES:
                limit_kb = settings.MAX_EVIDENCE_SIZE_TOTAL_PER_CASE_BYTES // 1024
                actual_kb = round((existing_bytes + content_bytes) / 1024, 1)
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail=(
                        f"Aggregate evidence limit exceeded for this investigation case. "
                        f"Maximum allowed total: {limit_kb} KB, current + new payload: {actual_kb} KB."
                    ),
                )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Error checking aggregate evidence size: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Database error checking evidence limits: {str(exc)}",
            )

        # 3. Insert record into investigation_evidence
        record = {
            "investigation_id": investigation_id,
            "evidence_type": request.evidence_type.value,
            "title": request.title or f"{request.evidence_type.value.replace('_', ' ').title()}",
            "content": request.content,
            "filename": request.filename,
        }

        try:
            insert_res = client.table("investigation_evidence").insert(record).execute()
            if not insert_res.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database failed to return inserted evidence record.",
                )

            data = insert_res.data[0]
            # Update investigation updated_at timestamp
            now_iso = datetime.now(timezone.utc).isoformat()
            client.table("investigations").update({"updated_at": now_iso}).eq("id", investigation_id).execute()

            return EvidenceResponse(
                id=data["id"],
                investigation_id=data["investigation_id"],
                evidence_type=EvidenceType(data["evidence_type"]),
                title=data.get("title"),
                content=data["content"],
                filename=data.get("filename"),
                byte_size=content_bytes,
                created_at=data["created_at"],
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Error inserting evidence for investigation '{investigation_id}': {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to persist evidence: {str(exc)}",
            )

    @classmethod
    def get_evidence_for_investigation(
        cls,
        investigation_id: str,
        user_id: Optional[str] = None,
    ) -> List[EvidenceResponse]:
        """Retrieve all evidence items for an authorized investigation."""
        client = cls._require_db_client()
        from app.services.investigation_service import InvestigationService
        InvestigationService.check_investigation_ownership(investigation_id, user_id, client=client)

        try:
            evidence_res = (
                client.table("investigation_evidence")
                .select("*")
                .eq("investigation_id", investigation_id)
                .order("created_at", desc=False)
                .execute()
            )
            rows = evidence_res.data or []

            return [
                EvidenceResponse(
                    id=row["id"],
                    investigation_id=row["investigation_id"],
                    evidence_type=EvidenceType(row["evidence_type"]),
                    title=row.get("title"),
                    content=row["content"],
                    filename=row.get("filename"),
                    byte_size=len(row["content"].encode("utf-8")),
                    created_at=row["created_at"],
                )
                for row in rows
            ]
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Error querying evidence for investigation '{investigation_id}': {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to query evidence: {str(exc)}",
            )

    @classmethod
    def delete_evidence(
        cls,
        investigation_id: str,
        evidence_id: str,
        user_id: Optional[str] = None,
    ) -> None:
        """Delete an evidence item from an authorized investigation."""
        client = cls._require_db_client()
        from app.services.investigation_service import InvestigationService
        InvestigationService.check_investigation_ownership(investigation_id, user_id, client=client)

        try:
            # Delete evidence item scoped to the specific investigation
            del_res = (
                client.table("investigation_evidence")
                .delete()
                .eq("id", evidence_id)
                .eq("investigation_id", investigation_id)
                .execute()
            )
            # Touch parent investigation updated_at
            now_iso = datetime.now(timezone.utc).isoformat()
            client.table("investigations").update({"updated_at": now_iso}).eq("id", investigation_id).execute()
        except Exception as exc:
            logger.error(f"Error deleting evidence '{evidence_id}': {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to delete evidence item: {str(exc)}",
            )
