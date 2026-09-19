from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict


class RepositoryAnalyzeRequest(BaseModel):
    github_url: str = Field(..., description="Public GitHub HTTPS repository URL (e.g. https://github.com/owner/repo)")
    project_id: Optional[str] = Field(None, description="Optional associated project UUID")


class RepositoryResponse(BaseModel):
    id: str = Field(..., description="UUID primary key")
    project_id: Optional[str] = Field(None, description="Associated project UUID")
    github_url: str = Field(..., description="Normalized GitHub HTTPS URL")
    owner: str = Field(..., description="Repository owner or organization")
    name: str = Field(..., description="Repository name")
    default_branch: Optional[str] = Field(None, description="Default branch name (e.g. main, master)")
    description: Optional[str] = Field(None, description="Repository description")
    primary_language: Optional[str] = Field(None, description="Detected primary programming language")
    total_files: int = Field(0, description="Total number of analyzed files")
    source_files: int = Field(0, description="Total number of identified source code files")
    analyzed_at: str = Field(..., description="Timestamp when analysis was conducted")
    created_at: str = Field(..., description="Timestamp of record creation")

    model_config = ConfigDict(from_attributes=True)


class RepositoryFileResponse(BaseModel):
    id: str = Field(..., description="UUID primary key")
    repository_id: str = Field(..., description="Parent repository UUID")
    path: str = Field(..., description="Relative file path from repository root")
    extension: Optional[str] = Field(None, description="File extension (e.g. .py, .ts)")
    language: Optional[str] = Field(None, description="Detected language or file type")
    file_size: int = Field(0, description="File size in bytes")
    lines_of_code: int = Field(0, description="Lines of code count")
    is_source_file: bool = Field(True, description="True if classified as a source code file")
    created_at: str = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class RepositoryCommitResponse(BaseModel):
    id: str = Field(..., description="UUID primary key")
    repository_id: str = Field(..., description="Parent repository UUID")
    commit_hash: str = Field(..., description="Commit SHA-1 hash")
    author_name: Optional[str] = Field(None, description="Commit author name")
    author_email: Optional[str] = Field(None, description="Commit author email")
    commit_message: Optional[str] = Field(None, description="Commit message headline/body")
    committed_at: Optional[str] = Field(None, description="ISO 8601 commit timestamp")
    files_changed: int = Field(0, description="Number of files touched in this commit")
    created_at: Optional[str] = Field(None, description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class RepositoryDetailResponse(BaseModel):
    repository: RepositoryResponse
    files: List[RepositoryFileResponse] = Field(default_factory=list)
    commits: List[RepositoryCommitResponse] = Field(default_factory=list)
    language_breakdown: Dict[str, int] = Field(default_factory=dict, description="File count per language")

    model_config = ConfigDict(from_attributes=True)
