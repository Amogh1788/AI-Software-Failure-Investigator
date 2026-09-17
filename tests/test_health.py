import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app

client = TestClient(app)


def test_api_health_endpoint():
    """Verify that GET /api/health returns the expected response schema and status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "ai-software-failure-investigator"


def test_root_endpoint():
    """Verify that root / returns service info and discovery endpoints."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "ai-software-failure-investigator"
    assert "/api/health" in data["endpoints"]["health"]


def test_database_health_endpoint():
    """Verify that GET /api/health/db returns a valid database health status structure."""
    response = client.get("/api/health/db")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["connected", "disconnected"]
    assert data["database"] == "supabase-postgresql"
    assert "message" in data
