import os
import stat
import shutil
import tempfile
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict
from fastapi import HTTPException, status
from app.core.database import get_supabase_client
from app.models.repository import (
    RepositoryResponse,
    RepositoryFileResponse,
    RepositoryCommitResponse,
    RepositoryDetailResponse,
)
from app.services.github_service import GitHubService
from app.services.repository_analyzer import RepositoryAnalyzer
from app.services.git_history_analyzer import GitHistoryAnalyzer

logger = logging.getLogger("ai_investigator.repository_service")


def _onerror_remove_readonly(func, path, exc_info):
    """Handle read-only files on Windows during directory deletion."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


class RepositoryService:
    """Orchestrates repository ingestion, static analysis, history extraction, and persistence."""

    @classmethod
    def analyze_repository(cls, github_url: str, project_id: Optional[str] = None) -> RepositoryDetailResponse:
        """
        Validate URL, clone to isolated temp directory, analyze codebase and Git history,
        persist metadata into Supabase, and clean up disk resources.
        """
        normalized_url, owner, repo_name = GitHubService.validate_and_parse_url(github_url)
        temp_dir = tempfile.mkdtemp(prefix="ai_repo_")
        repo = None

        try:
            # 1. Safe Shallow Clone with hard timeout
            repo = GitHubService.clone_repository_safely(normalized_url, temp_dir)

            # 2. Extract default branch
            default_branch = GitHistoryAnalyzer.get_default_branch(repo)

            # 3. Static Codebase Analysis (extensions, LOC, sizes)
            analysis_results = RepositoryAnalyzer.analyze(temp_dir)

            # 4. Recent Git History Analysis
            commits = GitHistoryAnalyzer.extract_recent_commits(repo)

            now_iso = datetime.now(timezone.utc).isoformat()

            # 5. Persist to Supabase
            repo_record = {
                "project_id": project_id,
                "github_url": normalized_url,
                "owner": owner,
                "name": repo_name,
                "default_branch": default_branch,
                "description": f"Public repository {owner}/{repo_name}",
                "primary_language": analysis_results["primary_language"],
                "total_files": analysis_results["total_files"],
                "source_files": analysis_results["source_files"],
                "analyzed_at": now_iso,
            }

            saved_repo = cls._save_to_supabase(
                repo_record,
                analysis_results["files"],
                commits,
            )

            files_response = [
                RepositoryFileResponse(
                    id=f.get("id", f"temp-{i}"),
                    repository_id=saved_repo.id,
                    path=f["path"],
                    extension=f.get("extension"),
                    language=f.get("language"),
                    file_size=f.get("file_size", 0),
                    lines_of_code=f.get("lines_of_code", 0),
                    is_source_file=f.get("is_source_file", True),
                    created_at=now_iso,
                )
                for i, f in enumerate(analysis_results["files"])
            ]

            commits_response = [
                RepositoryCommitResponse(
                    id=c.get("id", f"temp-c-{i}"),
                    repository_id=saved_repo.id,
                    commit_hash=c["commit_hash"],
                    author_name=c.get("author_name"),
                    author_email=c.get("author_email"),
                    commit_message=c.get("commit_message"),
                    committed_at=c.get("committed_at"),
                    files_changed=c.get("files_changed", 0),
                    created_at=now_iso,
                )
                for i, c in enumerate(commits)
            ]

            return RepositoryDetailResponse(
                repository=saved_repo,
                files=files_response,
                commits=commits_response,
                language_breakdown=analysis_results["language_breakdown"],
            )

        finally:
            # Guaranteed cleanup of temporary directory
            if repo:
                try:
                    repo.close()
                except Exception:
                    pass
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir, onerror=_onerror_remove_readonly)
                except Exception as exc:
                    logger.warning(f"Failed to fully delete temp dir {temp_dir}: {exc}")

    @classmethod
    def _save_to_supabase(cls, repo_data: Dict, files: List[Dict], commits: List[Dict]) -> RepositoryResponse:
        """Insert repository, files, and commits into Supabase PostgreSQL."""
        client = get_supabase_client()
        if not client:
            logger.warning("Supabase client not initialized; returning unpersisted analysis.")
            return RepositoryResponse(
                id="00000000-0000-0000-0000-000000000000",
                created_at=datetime.now(timezone.utc).isoformat(),
                **repo_data,
            )

        try:
            # 1. Insert repository record
            insert_res = client.table("repositories").insert(repo_data).execute()
            if not insert_res.data:
                raise Exception("Failed to insert repository record into Supabase.")

            repo_record = insert_res.data[0]
            repo_id = repo_record["id"]

            # 2. Bulk insert repository files in batches of 300
            file_records = [
                {
                    "repository_id": repo_id,
                    "path": f["path"],
                    "extension": f.get("extension"),
                    "language": f.get("language"),
                    "file_size": f.get("file_size", 0),
                    "lines_of_code": f.get("lines_of_code", 0),
                    "is_source_file": f.get("is_source_file", True),
                }
                for f in files
            ]

            for i in range(0, len(file_records), 300):
                chunk = file_records[i : i + 300]
                client.table("repository_files").insert(chunk).execute()

            # 3. Bulk insert commits
            commit_records = [
                {
                    "repository_id": repo_id,
                    "commit_hash": c["commit_hash"],
                    "author_name": c.get("author_name"),
                    "author_email": c.get("author_email"),
                    "commit_message": c.get("commit_message"),
                    "committed_at": c.get("committed_at"),
                    "files_changed": c.get("files_changed", 0),
                }
                for c in commits
            ]

            if commit_records:
                for i in range(0, len(commit_records), 300):
                    chunk = commit_records[i : i + 300]
                    client.table("repository_commits").insert(chunk).execute()

            return RepositoryResponse(**repo_record)

        except Exception as exc:
            logger.error(f"Error saving repository data to Supabase: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Database error while saving repository analysis: {str(exc)}",
            )

    @classmethod
    def list_repositories(cls) -> List[RepositoryResponse]:
        """Fetch all analyzed repositories ordered by analyzed_at descending."""
        client = get_supabase_client()
        if not client:
            return []

        try:
            res = client.table("repositories").select("*").order("analyzed_at", desc=True).execute()
            data = res.data or []
            return [RepositoryResponse(**r) for r in data]
        except Exception as exc:
            logger.error(f"Error listing repositories: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to query repositories: {str(exc)}",
            )

    @classmethod
    def get_repository(cls, repo_id: str) -> RepositoryResponse:
        """Fetch a single repository by UUID."""
        client = get_supabase_client()
        if not client:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unconfigured.")

        try:
            res = client.table("repositories").select("*").eq("id", repo_id).execute()
            data = res.data or []
            if not data:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository '{repo_id}' not found.")
            return RepositoryResponse(**data[0])
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to fetch repository: {str(exc)}",
            )

    @classmethod
    def get_repository_files(cls, repo_id: str) -> List[RepositoryFileResponse]:
        """Fetch all file metadata for a specific repository."""
        client = get_supabase_client()
        if not client:
            return []

        try:
            res = (
                client.table("repository_files")
                .select("*")
                .eq("repository_id", repo_id)
                .order("path", desc=False)
                .limit(2000)
                .execute()
            )
            data = res.data or []
            return [RepositoryFileResponse(**f) for f in data]
        except Exception as exc:
            logger.error(f"Error fetching repository files: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to fetch repository files: {str(exc)}",
            )

    @classmethod
    def get_repository_commits(cls, repo_id: str) -> List[RepositoryCommitResponse]:
        """Fetch all commit metadata for a specific repository."""
        client = get_supabase_client()
        if not client:
            return []

        try:
            res = (
                client.table("repository_commits")
                .select("*")
                .eq("repository_id", repo_id)
                .order("committed_at", desc=True)
                .limit(100)
                .execute()
            )
            data = res.data or []
            return [RepositoryCommitResponse(**c) for c in data]
        except Exception as exc:
            logger.error(f"Error fetching repository commits: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to fetch repository commits: {str(exc)}",
            )
