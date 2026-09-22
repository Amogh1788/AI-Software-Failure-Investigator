import os
import shutil
import stat
import time
import logging
import tempfile
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import HTTPException, status
import git

from app.core.database import get_service_role_client
from app.models.investigation import InvestigationStatus
from app.models.analysis import (
    InvestigationAnalysisResponse,
    EvidenceSignalsSummary,
    FailureCandidate,
    FailureChainStep,
    RelevantCommit,
)
from app.services.github_service import GitHubService
from app.services.evidence_service import EvidenceService
from app.services.intelligence_engine import IntelligenceEngine

logger = logging.getLogger("ai_investigator.analysis_service")


def _onerror_remove_readonly(func, path, exc_info):
    """Windows-safe handler to force-remove read-only git index files."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception as e:
        logger.warning(f"Could not remove path {path}: {e}")


class AnalysisService:
    """Orchestrates investigation analysis runs, status lifecycle, and persistence."""

    ENGINE_VERSION = "1.0.0"

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
    def analyze_investigation(
        cls,
        investigation_id: str,
        user_id: Optional[str] = None,
    ) -> InvestigationAnalysisResponse:
        """
        Execute investigation intelligence analysis.
        Strictly enforces:
          - Only authorized owner can analyze the investigation case.
          - Only investigations with status = 'ready' or 'completed' (for re-analysis) may be analyzed.
          - If still 'draft': returns HTTP 409 Conflict.
          - Transitions: ready -> analyzing -> completed.
          - On failure: reverts to 'ready' to prevent getting stuck in 'analyzing'.
          - Creates a new analysis run record in investigation_runs.
        """
        client = cls._require_db_client()
        from app.services.investigation_service import InvestigationService
        inv_data = InvestigationService.check_investigation_ownership(investigation_id, user_id, client=client)

        start_time = time.time()

        current_status = inv_data.get("status")
        if current_status == InvestigationStatus.DRAFT.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Investigation must be marked ready before analysis.",
            )

        # 2. Fetch repository info
        try:
            repo_res = client.table("repositories").select("*").eq("id", inv_data["repository_id"]).execute()
            if not repo_res.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Repository '{inv_data['repository_id']}' not found.",
                )
            repo_data = repo_res.data[0]
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to query repository: {str(exc)}",
            )

        # 3. Transition status to 'analyzing'
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            client.table("investigations").update({
                "status": InvestigationStatus.ANALYZING.value,
                "updated_at": now_iso,
            }).eq("id", investigation_id).execute()
        except Exception as exc:
            logger.warning(f"Failed to set status to analyzing: {exc}")

        temp_dir = tempfile.mkdtemp(prefix="investigation_repo_")
        git_repo: Optional[git.Repo] = None

        try:
            # 4. Fetch evidence artifacts
            evidence_items = EvidenceService.get_evidence_for_investigation(investigation_id, user_id=user_id)
            evidence_dicts = [e.model_dump() for e in evidence_items]

            # 5. Acquire repository code
            github_url = repo_data.get("github_url", "")
            if os.path.exists(github_url) and os.path.isdir(github_url):
                # Local test fixture repository (e.g. checkout-testbed)
                scan_dir = github_url
                try:
                    git_repo = git.Repo(scan_dir)
                except Exception:
                    git_repo = None
            else:
                # Clone safely using Phase 2 service
                git_repo = GitHubService.clone_repository_safely(github_url, temp_dir)
                scan_dir = temp_dir

            # 6. Run Investigation Intelligence Engine v1
            candidates, chain, commits, signals_summary, summary = IntelligenceEngine.analyze(
                repo_dir=scan_dir,
                git_repo=git_repo,
                evidence_items=evidence_dicts,
            )

            duration_ms = int((time.time() - start_time) * 1000)

            # 7. Persist analysis run into investigation_runs
            run_record = {
                "investigation_id": investigation_id,
                "engine_version": cls.ENGINE_VERSION,
                "status": "completed",
                "summary": summary,
                "failure_chain": [step.model_dump() for step in chain],
                "ranked_candidates": [c.model_dump() for c in candidates],
                "relevant_commits": [rc.model_dump() for rc in commits],
                "evidence_signals": signals_summary.model_dump(),
                "run_duration_ms": duration_ms,
            }

            insert_res = client.table("investigation_runs").insert(run_record).execute()
            if not insert_res.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database failed to record analysis run.",
                )

            saved_run = insert_res.data[0]

            # 8. Transition investigation status to 'completed'
            client.table("investigations").update({
                "status": InvestigationStatus.COMPLETED.value,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", investigation_id).execute()

            return InvestigationAnalysisResponse(
                id=saved_run["id"],
                investigation_id=saved_run["investigation_id"],
                engine_version=saved_run.get("engine_version", cls.ENGINE_VERSION),
                status=saved_run.get("status", "completed"),
                summary=saved_run["summary"],
                failure_chain=[FailureChainStep(**s) for s in saved_run.get("failure_chain", [])],
                ranked_candidates=[FailureCandidate(**c) for c in saved_run.get("ranked_candidates", [])],
                relevant_commits=[RelevantCommit(**rc) for rc in saved_run.get("relevant_commits", [])],
                evidence_signals=EvidenceSignalsSummary(**saved_run.get("evidence_signals", {})),
                run_duration_ms=saved_run.get("run_duration_ms", duration_ms),
                created_at=saved_run["created_at"],
            )

        except HTTPException:
            # On failure: revert status back to 'ready' so investigation is not permanently stuck
            try:
                client.table("investigations").update({
                    "status": InvestigationStatus.READY.value,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", investigation_id).execute()
            except Exception:
                pass
            raise

        except Exception as exc:
            # On unexpected failure: revert status back to 'ready'
            try:
                client.table("investigations").update({
                    "status": InvestigationStatus.READY.value,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", investigation_id).execute()
            except Exception:
                pass

            logger.error(f"Analysis engine execution failed: {exc}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Analysis engine failed: {str(exc)}",
            )

        finally:
            # Guaranteed cleanup of temporary clone directory
            if git_repo:
                try:
                    git_repo.close()
                except Exception:
                    pass
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir, onerror=_onerror_remove_readonly)
                except Exception as exc:
                    logger.warning(f"Failed to delete analysis temp directory {temp_dir}: {exc}")

    @classmethod
    def get_latest_analysis(
        cls,
        investigation_id: str,
        user_id: Optional[str] = None,
    ) -> Optional[InvestigationAnalysisResponse]:
        """Fetch the most recent completed analysis run for an authorized investigation."""
        client = cls._require_db_client()
        from app.services.investigation_service import InvestigationService
        InvestigationService.check_investigation_ownership(investigation_id, user_id, client=client)

        try:
            res = (
                client.table("investigation_runs")
                .select("*")
                .eq("investigation_id", investigation_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            data = res.data or []
            if not data:
                return None

            run = data[0]
            return InvestigationAnalysisResponse(
                id=run["id"],
                investigation_id=run["investigation_id"],
                engine_version=run.get("engine_version", cls.ENGINE_VERSION),
                status=run.get("status", "completed"),
                summary=run["summary"],
                failure_chain=[FailureChainStep(**s) for s in run.get("failure_chain", [])],
                ranked_candidates=[FailureCandidate(**c) for c in run.get("ranked_candidates", [])],
                relevant_commits=[RelevantCommit(**rc) for rc in run.get("relevant_commits", [])],
                evidence_signals=EvidenceSignalsSummary(**run.get("evidence_signals", {})),
                run_duration_ms=run.get("run_duration_ms", 0),
                created_at=run["created_at"],
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Error fetching analysis for '{investigation_id}': {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to retrieve analysis report: {str(exc)}",
            )

    @classmethod
    def list_analysis_runs(
        cls,
        investigation_id: str,
        user_id: Optional[str] = None,
    ) -> List[InvestigationAnalysisResponse]:
        """Fetch all historical analysis runs for an authorized investigation."""
        client = cls._require_db_client()
        from app.services.investigation_service import InvestigationService
        InvestigationService.check_investigation_ownership(investigation_id, user_id, client=client)

        try:
            res = (
                client.table("investigation_runs")
                .select("*")
                .eq("investigation_id", investigation_id)
                .order("created_at", desc=True)
                .execute()
            )
            runs = res.data or []
            return [
                InvestigationAnalysisResponse(
                    id=run["id"],
                    investigation_id=run["investigation_id"],
                    engine_version=run.get("engine_version", cls.ENGINE_VERSION),
                    status=run.get("status", "completed"),
                    summary=run["summary"],
                    failure_chain=[FailureChainStep(**s) for s in run.get("failure_chain", [])],
                    ranked_candidates=[FailureCandidate(**c) for c in run.get("ranked_candidates", [])],
                    relevant_commits=[RelevantCommit(**rc) for rc in run.get("relevant_commits", [])],
                    evidence_signals=EvidenceSignalsSummary(**run.get("evidence_signals", {})),
                    run_duration_ms=run.get("run_duration_ms", 0),
                    created_at=run["created_at"],
                )
                for run in runs
            ]
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Error listing analysis runs: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to query analysis runs: {str(exc)}",
            )
