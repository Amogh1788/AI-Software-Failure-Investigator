from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.models.repository import RepositoryResponse


class InvestigationStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"


class EvidenceType(str, Enum):
    BUG_REPORT = "bug_report"
    APPLICATION_LOG = "application_log"
    STACK_TRACE = "stack_trace"
    TEST_OUTPUT = "test_output"


class InvestigationCreateRequest(BaseModel):
    repository_id: str = Field(..., description="UUID of the analyzed repository")
    title: str = Field(..., min_length=1, max_length=200, description="Title of the investigation case")
    description: Optional[str] = Field(None, max_length=2000, description="Context or description of the failure")


class InvestigationUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Updated title")
    description: Optional[str] = Field(None, max_length=2000, description="Updated description")
    status: Optional[InvestigationStatus] = Field(None, description="Updated status ('draft' or 'ready')")


class EvidenceCreateRequest(BaseModel):
    evidence_type: EvidenceType = Field(..., description="Category of failure evidence")
    title: Optional[str] = Field(None, max_length=200, description="Title or label for this evidence item")
    content: str = Field(..., min_length=1, description="Raw evidence payload (logs, stack trace, etc.)")
    filename: Optional[str] = Field(None, max_length=255, description="Source filename or origin identifier")


class EvidenceResponse(BaseModel):
    id: str = Field(..., description="UUID primary key")
    investigation_id: str = Field(..., description="Associated investigation UUID")
    evidence_type: EvidenceType = Field(..., description="Evidence category")
    title: Optional[str] = Field(None, description="Evidence title/label")
    content: str = Field(..., description="Raw text content")
    filename: Optional[str] = Field(None, description="Optional filename")
    byte_size: int = Field(0, description="Byte size of the evidence content")
    created_at: str = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class InvestigationResponse(BaseModel):
    id: str = Field(..., description="UUID primary key")
    repository_id: str = Field(..., description="UUID of the associated repository")
    title: str = Field(..., description="Investigation title")
    description: Optional[str] = Field(None, description="Investigation description")
    status: InvestigationStatus = Field(InvestigationStatus.DRAFT, description="Current workflow status")
    evidence_count: int = Field(0, description="Total number of evidence items attached")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class InvestigationDetailResponse(BaseModel):
    investigation: InvestigationResponse
    repository: Optional[RepositoryResponse] = None
    evidence: List[EvidenceResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
