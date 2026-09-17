from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class ProjectBase(BaseModel):
    name: str = Field(..., description="Project name or identifier", min_length=1)
    description: Optional[str] = Field(None, description="Detailed project description")


class ProjectCreate(ProjectBase):
    pass


class ProjectResponse(ProjectBase):
    id: str = Field(..., description="UUID primary key")
    created_at: str = Field(..., description="ISO 8601 timestamp with timezone")

    model_config = ConfigDict(from_attributes=True)


class ProjectListResponse(BaseModel):
    status: str = "ok"
    count: int
    data: List[ProjectResponse]


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "ai-software-failure-investigator"


class DatabaseHealthResponse(BaseModel):
    status: str  # "connected" or "disconnected"
    database: str = "supabase-postgresql"
    message: str
