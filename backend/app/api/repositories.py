from typing import List
from fastapi import APIRouter, status, Depends, Response
from app.core.auth import get_current_user, AuthenticatedUser
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
    summary="Ingest and analyze a public GitHub repository (Authenticated)",
)
def analyze_repository(
    payload: RepositoryAnalyzeRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> RepositoryDetailResponse:
    """
    Validate, safely shallow-clone, statically analyze, extract commit history,
    and persist repository metadata to Supabase. Requires authentication.
    """
    return RepositoryService.analyze_repository(
        github_url=payload.github_url,
        project_id=payload.project_id,
        user_id=current_user.id,
    )


@router.get(
    "",
    response_model=List[RepositoryResponse],
    summary="List analyzed repositories for current user (Authenticated)",
)
def list_repositories(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> List[RepositoryResponse]:
    """Retrieve all previously analyzed GitHub repositories for the authenticated user."""
    return RepositoryService.list_repositories(user_id=current_user.id)


@router.delete(
    "/{repository_id}/history",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a repository from the user's history (Authenticated)",
)
@router.delete(
    "/{repository_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
def delete_repository_history(
    repository_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Remove a repository from the authenticated user's history.
    Does not delete the underlying repository or analysis data.
    """
    RepositoryService.delete_user_repository_history(
        repository_id=repository_id,
        user_id=current_user.id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{repository_id}",
    response_model=RepositoryResponse,
    summary="Get repository summary (Public Metadata)",
)
def get_repository(repository_id: str) -> RepositoryResponse:
    """Retrieve repository summary by UUID."""
    return RepositoryService.get_repository(repository_id)


@router.get(
    "/{repository_id}/files",
    response_model=List[RepositoryFileResponse],
    summary="Get repository file metadata (Public Metadata)",
)
def get_repository_files(repository_id: str) -> List[RepositoryFileResponse]:
    """Retrieve file metadata for a specific repository."""
    return RepositoryService.get_repository_files(repository_id)


@router.get(
    "/{repository_id}/commits",
    response_model=List[RepositoryCommitResponse],
    summary="Get repository commit history (Public Metadata)",
)
def get_repository_commits(repository_id: str) -> List[RepositoryCommitResponse]:
    """Retrieve the recent Git commit metadata for a specific repository."""
    return RepositoryService.get_repository_commits(repository_id)
