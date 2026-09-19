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
    """Service layer managing failure evidence validation, limits, and persistence."""

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
            logger.error("SUPABASE_SERVICE_ROLE_KEY is not configured for private investigation operations.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service role configuration missing for private investigation operations. Set SUPABASE_SERVICE_ROLE_KEY in server environment.",
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
    ) -> EvidenceResponse:
        """Validate, store, and return new evidence for an investigation."""
        client = cls._require_db_client()

        # 1. Verify that investigation exists
        try:
            inv_res = (
                client.table("investigations")
                .select("id")
                .eq("id", investigation_id)
                .execute()
            )
            if not inv_res.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Investigation with ID '{investigation_id}' not found.",
                )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Error checking investigation existence: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to query investigation: {str(exc)}",
            )

        # 2. Enforce byte size limit
        content_bytes = cls.validate_size_limit(request.evidence_type, request.content)

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
            logger.error(f"Error persisting evidence: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Database error while saving evidence: {str(exc)}",
            )

    @classmethod
    def get_evidence_for_investigation(cls, investigation_id: str) -> List[EvidenceResponse]:
        """Fetch all evidence items attached to an investigation."""
        client = cls._require_db_client()

        try:
            res = (
                client.table("investigation_evidence")
                .select("*")
                .eq("investigation_id", investigation_id)
                .order("created_at", desc=False)
                .execute()
            )
            items = res.data or []
            return [
                EvidenceResponse(
                    id=item["id"],
                    investigation_id=item["investigation_id"],
                    evidence_type=EvidenceType(item["evidence_type"]),
                    title=item.get("title"),
                    content=item["content"],
                    filename=item.get("filename"),
                    byte_size=len(item["content"].encode("utf-8")),
                    created_at=item["created_at"],
                )
                for item in items
            ]
        except Exception as exc:
            logger.error(f"Error fetching evidence for investigation '{investigation_id}': {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to query evidence: {str(exc)}",
            )

    @classmethod
    def delete_evidence(cls, investigation_id: str, evidence_id: str) -> None:
        """Delete an individual evidence item."""
        client = cls._require_db_client()

        try:
            del_res = (
                client.table("investigation_evidence")
                .delete()
                .eq("id", evidence_id)
                .eq("investigation_id", investigation_id)
                .execute()
            )
            # Update investigation updated_at
            now_iso = datetime.now(timezone.utc).isoformat()
            client.table("investigations").update({"updated_at": now_iso}).eq("id", investigation_id).execute()
        except Exception as exc:
            logger.error(f"Error deleting evidence '{evidence_id}': {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to delete evidence: {str(exc)}",
            )
