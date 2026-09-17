import sys
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from app.models.project import ProjectResponse

client = TestClient(app)


def test_get_projects_mocked():
    """Verify that /api/projects serializes and returns project records properly."""
    mock_projects = [
        ProjectResponse(
            id="11111111-2222-3333-4444-555555555555",
            name="mock-incident-pipeline",
            description="Mock pipeline crash test",
            created_at="2026-09-17T00:00:00Z",
        )
    ]

    with patch("app.services.project_service.ProjectService.get_all_projects", return_value=mock_projects):
        response = client.get("/api/projects")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "mock-incident-pipeline"
        assert data[0]["id"] == "11111111-2222-3333-4444-555555555555"


def test_get_projects_graceful_handling_without_credentials():
    """Verify that /api/projects fails gracefully (e.g. 503/502) if Supabase is unconfigured."""
    # Ensure client returns None when unconfigured
    with patch("app.services.project_service.get_supabase_client", return_value=None):
        response = client.get("/api/projects")
        assert response.status_code in [502, 503]
        data = response.json()
        assert "detail" in data
