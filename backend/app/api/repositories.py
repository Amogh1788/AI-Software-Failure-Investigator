from typing import List
from fastapi import APIRouter, status
from app.models.repository import (
    RepositoryAnalyzeRequest,
    RepositoryResponse,
    RepositoryFileResponse,
    RepositoryCommitResponse,
    RepositoryDetailResponse,
)
from app.services.repository_service import RepositoryService

router = APIRouter(prefix="/repositories", tags=["Repositories"])


@router.post(
    "/analyze",
    response_model=RepositoryDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest and analyze a public GitHub repository",
)
def analyze_repository(payload: RepositoryAnalyzeRequest) -> RepositoryDetailResponse:
    """
    Validate, safely shallow-clone, statically analyze, extract commit history,
    and persist repository metadata to Supabase.
    """
    return RepositoryService.analyze_repository(
        github_url=payload.github_url,
        project_id=payload.project_id,
    )


@router.get(
    "",
    response_model=List[RepositoryResponse],
    summary="List analyzed repositories",
)
def list_repositories() -> List[RepositoryResponse]:
    """Retrieve all previously analyzed GitHub repositories."""
    return RepositoryService.list_repositories()


@router.get(
    "/{repository_id}",
    response_model=RepositoryResponse,
    summary="Get repository summary",
)
def get_repository(repository_id: str) -> RepositoryResponse:
    """Retrieve repository summary by UUID."""
    return RepositoryService.get_repository(repository_id)


@router.get(
    "/{repository_id}/files",
    response_model=List[RepositoryFileResponse],
    summary="Get repository file metadata",
)
def get_repository_files(repository_id: str) -> List[RepositoryFileResponse]:
    """Retrieve file metadata for a specific repository."""
    return RepositoryService.get_repository_files(repository_id)


@router.get(
    "/{repository_id}/commits",
    response_model=List[RepositoryCommitResponse],
    summary="Get repository commit history",
)
def get_repository_commits(repository_id: str) -> List[RepositoryCommitResponse]:
    """Retrieve the recent Git commit metadata for a specific repository."""
    return RepositoryService.get_repository_commits(repository_id)
