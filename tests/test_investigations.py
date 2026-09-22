import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from app.core import database
from app.core.config import settings
from app.models.investigation import EvidenceType, InvestigationStatus

client = TestClient(app)

MOCK_REPO_ID = "11111111-1111-1111-1111-111111111111"
MOCK_INV_ID = "22222222-2222-2222-2222-222222222222"
MOCK_EVID_ID = "33333333-3333-3333-3333-333333333333"


@pytest.fixture(autouse=True)
def ensure_service_role_configured():
    """Ensure service role key is mocked in test environment by default."""
    database.reset_supabase_client()
    with patch.dict(os.environ, {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-secret-key",
    }):
        yield
    database.reset_supabase_client()


# 1. Repository Association & Investigation Creation
def test_create_investigation_success():
    """Verify creating an investigation with valid repository."""
    mock_db = MagicMock()

    # Mock repository lookup
    mock_repo_query = MagicMock()
    mock_repo_query.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": MOCK_REPO_ID, "status": "analyzed"}
    ]

    # Mock investigation insert
    mock_inv_query = MagicMock()
    mock_inv_query.insert.return_value.execute.return_value.data = [
        {
            "id": MOCK_INV_ID,
            "repository_id": MOCK_REPO_ID,
            "title": "Payment Gateway 504 Timeout",
            "description": "Checkout failure under high load",
            "status": "draft",
            "created_at": "2026-09-19T14:00:00Z",
            "updated_at": "2026-09-19T14:00:00Z",
        }
    ]

    def table_side_effect(table_name):
        if table_name == "repositories":
            return mock_repo_query
        elif table_name == "investigations":
            return mock_inv_query
        return MagicMock()

    mock_db.table.side_effect = table_side_effect

    with patch("app.services.investigation_service.get_service_role_client", return_value=mock_db):
        resp = client.post(
            "/api/investigations",
            json={
                "repository_id": MOCK_REPO_ID,
                "title": "Payment Gateway 504 Timeout",
                "description": "Checkout failure under high load",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == MOCK_INV_ID
        assert data["repository_id"] == MOCK_REPO_ID
        assert data["title"] == "Payment Gateway 504 Timeout"
        assert data["status"] == "draft"
        assert data["evidence_count"] == 0


def test_create_investigation_missing_repository():
    """Verify 404 when attempting to create investigation for nonexistent repository."""
    mock_db = MagicMock()
    mock_repo_query = MagicMock()
    mock_repo_query.select.return_value.eq.return_value.execute.return_value.data = []
    mock_db.table.return_value = mock_repo_query

    with patch("app.services.investigation_service.get_service_role_client", return_value=mock_db):
        resp = client.post(
            "/api/investigations",
            json={
                "repository_id": "nonexistent-repo-id",
                "title": "Should Fail",
            },
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


def test_create_investigation_failed_repository():
    """Verify 409 when repository is in error/failed state."""
    mock_db = MagicMock()
    mock_repo_query = MagicMock()
    mock_repo_query.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": MOCK_REPO_ID, "status": "error"}
    ]
    mock_db.table.return_value = mock_repo_query

    with patch("app.services.investigation_service.get_service_role_client", return_value=mock_db):
        resp = client.post(
            "/api/investigations",
            json={
                "repository_id": MOCK_REPO_ID,
                "title": "Investigation on failed repo",
            },
        )
        assert resp.status_code == 409
        assert "failed state" in resp.json()["detail"].lower()


# 2. Evidence Type Validation & Limits
def test_add_evidence_valid_types():
    """Verify attaching each allowed evidence type."""
    mock_db = MagicMock()

    # Mock investigation exists
    mock_inv_query = MagicMock()
    mock_inv_query.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": MOCK_INV_ID, "owner_user_id": "00000000-0000-0000-0000-000000000001"}
    ]
    mock_inv_query.update.return_value.eq.return_value.execute.return_value.data = [{"id": MOCK_INV_ID}]

    valid_types = [
        ("bug_report", "Issue #402", "User cannot complete purchase."),
        ("application_log", "app.log", "2026-09-19 ERROR 504 Gateway Timeout"),
        ("stack_trace", "trace.txt", "Traceback (most recent call last):\n  File 'app.py', line 12"),
        ("test_output", "pytest.log", "FAILED tests/test_checkout.py::test_payment - TimeoutError"),
    ]

    for etype, title, content in valid_types:
        mock_evid_query = MagicMock()
        mock_evid_query.insert.return_value.execute.return_value.data = [
            {
                "id": MOCK_EVID_ID,
                "investigation_id": MOCK_INV_ID,
                "evidence_type": etype,
                "title": title,
                "content": content,
                "filename": f"{etype}.txt",
                "created_at": "2026-09-19T14:05:00Z",
            }
        ]

        def table_side_effect(table_name):
            if table_name == "investigations":
                return mock_inv_query
            elif table_name == "investigation_evidence":
                return mock_evid_query
            return MagicMock()

        mock_db.table.side_effect = table_side_effect

        with patch("app.services.evidence_service.get_service_role_client", return_value=mock_db):
            resp = client.post(
                f"/api/investigations/{MOCK_INV_ID}/evidence",
                json={
                    "evidence_type": etype,
                    "title": title,
                    "content": content,
                    "filename": f"{etype}.txt",
                },
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["evidence_type"] == etype
            assert data["content"] == content


def test_reject_invalid_evidence_type():
    """Verify rejection of unknown evidence types."""
    resp = client.post(
        f"/api/investigations/{MOCK_INV_ID}/evidence",
        json={
            "evidence_type": "unknown_ai_summary",
            "title": "Invalid Type",
            "content": "Some content",
        },
    )
    assert resp.status_code == 422


def test_reject_oversized_evidence_http_413():
    """Verify HTTP 413 Content Too Large when payload exceeds category limits."""
    mock_db = MagicMock()
    mock_inv_query = MagicMock()
    mock_inv_query.select.return_value.eq.return_value.execute.return_value.data = [{"id": MOCK_INV_ID}]
    mock_db.table.return_value = mock_inv_query

    test_cases = [
        ("bug_report", 51200 + 100),       # >50 KB
        ("application_log", 512000 + 100),  # >500 KB
        ("stack_trace", 204800 + 100),     # >200 KB
        ("test_output", 204800 + 100),     # >200 KB
    ]

    with patch("app.services.evidence_service.get_service_role_client", return_value=mock_db):
        for etype, byte_size in test_cases:
            oversized_content = "X" * byte_size
            resp = client.post(
                f"/api/investigations/{MOCK_INV_ID}/evidence",
                json={
                    "evidence_type": etype,
                    "title": f"Oversized {etype}",
                    "content": oversized_content,
                },
            )
            assert resp.status_code == 413, f"Expected 413 for {etype} with {byte_size} bytes"
            assert "exceeds size limit" in resp.json()["detail"]


# 3. Status Transition & Strict Ready Validation
def test_update_status_draft_always_allowed():
    """Verify that 'draft' status is always accepted."""
    mock_db = MagicMock()
    mock_inv_query = MagicMock()
    mock_inv_query.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": MOCK_INV_ID, "repository_id": MOCK_REPO_ID, "title": "Test", "owner_user_id": "00000000-0000-0000-0000-000000000001", "status": "draft", "created_at": "2026-09-19", "updated_at": "2026-09-19"}
    ]
    mock_inv_query.update.return_value.eq.return_value.execute.return_value.data = [
        {"id": MOCK_INV_ID, "repository_id": MOCK_REPO_ID, "title": "Updated Title", "owner_user_id": "00000000-0000-0000-0000-000000000001", "status": "draft", "created_at": "2026-09-19", "updated_at": "2026-09-19"}
    ]
    mock_db.table.return_value = mock_inv_query

    with patch("app.services.investigation_service.get_service_role_client", return_value=mock_db), \
         patch("app.services.evidence_service.EvidenceService.get_evidence_for_investigation", return_value=[]):
        resp = client.patch(
            f"/api/investigations/{MOCK_INV_ID}",
            json={"title": "Updated Title", "status": "draft"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"


def test_update_status_ready_fails_when_missing_evidence():
    """Verify HTTP 409 when transitioning to 'ready' with missing evidence categories."""
    mock_db = MagicMock()

    mock_inv_query = MagicMock()
    mock_inv_query.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": MOCK_INV_ID, "repository_id": MOCK_REPO_ID, "title": "Test", "owner_user_id": "00000000-0000-0000-0000-000000000001", "status": "draft"}
    ]

    # Only bug_report present; missing application_log, stack_trace, test_output
    mock_evid_query = MagicMock()
    mock_evid_query.select.return_value.eq.return_value.execute.return_value.data = [
        {"evidence_type": "bug_report"}
    ]

    def table_side_effect(table_name):
        if table_name == "investigations":
            return mock_inv_query
        elif table_name == "investigation_evidence":
            return mock_evid_query
        return MagicMock()

    mock_db.table.side_effect = table_side_effect

    with patch("app.services.investigation_service.get_service_role_client", return_value=mock_db):
        resp = client.patch(
            f"/api/investigations/{MOCK_INV_ID}",
            json={"status": "ready"},
        )
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert "cannot be marked ready" in detail.lower()
        assert "missing evidence" in detail.lower()


def test_update_status_ready_succeeds_when_all_four_categories_present():
    """Verify status transition to 'ready' succeeds when all 4 evidence types are attached."""
    mock_db = MagicMock()

    mock_inv_query = MagicMock()
    mock_inv_query.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": MOCK_INV_ID, "repository_id": MOCK_REPO_ID, "title": "Complete Case", "owner_user_id": "00000000-0000-0000-0000-000000000001", "status": "draft", "created_at": "2026-09-19", "updated_at": "2026-09-19"}
    ]
    mock_inv_query.update.return_value.eq.return_value.execute.return_value.data = [
        {"id": MOCK_INV_ID, "repository_id": MOCK_REPO_ID, "title": "Complete Case", "owner_user_id": "00000000-0000-0000-0000-000000000001", "status": "ready", "created_at": "2026-09-19", "updated_at": "2026-09-19"}
    ]

    # All 4 categories present
    mock_evid_query = MagicMock()
    mock_evid_query.select.return_value.eq.return_value.execute.return_value.data = [
        {"evidence_type": "bug_report"},
        {"evidence_type": "application_log"},
        {"evidence_type": "stack_trace"},
        {"evidence_type": "test_output"},
    ]

    def table_side_effect(table_name):
        if table_name == "investigations":
            return mock_inv_query
        elif table_name == "investigation_evidence":
            return mock_evid_query
        return MagicMock()

    mock_db.table.side_effect = table_side_effect

    with patch("app.services.investigation_service.get_service_role_client", return_value=mock_db), \
         patch("app.services.evidence_service.EvidenceService.get_evidence_for_investigation", return_value=[MagicMock(), MagicMock(), MagicMock(), MagicMock()]):
        resp = client.patch(
            f"/api/investigations/{MOCK_INV_ID}",
            json={"status": "ready"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"


# 4. Service-Role Key Security Enforcement
def test_investigation_operations_fail_when_service_role_key_missing():
    """Verify controlled HTTP 503 error when database server credentials are completely absent."""
    database.reset_supabase_client()
    with patch.dict(os.environ, {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SECRET_KEY": "",
        "SUPABASE_SERVICE_ROLE_KEY": "",
    }, clear=True), patch.object(settings, "SUPABASE_SECRET_KEY", ""), patch.object(settings, "SUPABASE_SERVICE_ROLE_KEY", ""):
        resp = client.get("/api/investigations")
        assert resp.status_code == 503
        assert "service role configuration missing" in resp.json()["detail"].lower()


def test_no_service_role_key_exposed_in_investigation_responses():
    """Verify service-role secret key is never leaked in investigation endpoints."""
    secret_key = "super-secret-service-role-key-999"
    mock_db = MagicMock()

    mock_inv_query = MagicMock()
    mock_inv_query.select.return_value.order.return_value.execute.return_value.data = [
        {"id": MOCK_INV_ID, "repository_id": MOCK_REPO_ID, "title": "Test", "owner_user_id": "00000000-0000-0000-0000-000000000001", "status": "draft", "created_at": "2026-09-19", "updated_at": "2026-09-19"}
    ]
    mock_db.table.return_value = mock_inv_query

    with patch.dict(os.environ, {"SUPABASE_SERVICE_ROLE_KEY": secret_key}), \
         patch("app.services.investigation_service.get_service_role_client", return_value=mock_db):
        resp = client.get("/api/investigations")
        assert resp.status_code == 200
        assert secret_key not in resp.text


# 5. Evidence Deletion
def test_delete_evidence_item():
    """Verify deleting a single evidence item."""
    mock_db = MagicMock()
    mock_evid_query = MagicMock()
    mock_evid_query.delete.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    mock_inv_query = MagicMock()
    mock_inv_query.update.return_value.eq.return_value.execute.return_value.data = []

    def table_side_effect(table_name):
        if table_name == "investigation_evidence":
            return mock_evid_query
        elif table_name == "investigations":
            return mock_inv_query
        return MagicMock()

    mock_db.table.side_effect = table_side_effect

    with patch("app.services.evidence_service.get_service_role_client", return_value=mock_db):
        resp = client.delete(f"/api/investigations/{MOCK_INV_ID}/evidence/{MOCK_EVID_ID}")
        assert resp.status_code == 204


# 6. Repository Status Schema Consistency & Fallback Tests
def test_create_investigation_with_status_column_missing_in_database_fallback():
    """
    Verify that if the database has not yet been migrated with phase3_repository_schema_fix.sql
    and throws PostgreSQL 42703 (column repositories.status does not exist), the backend
    gracefully catches it and falls back to verifying existence via id.
    """
    mock_db = MagicMock()

    # When select("id, status") is called, simulate PostgreSQL code 42703 error
    def select_side_effect(cols):
        query = MagicMock()
        if cols == "id, status":
            query.eq.return_value.execute.side_effect = Exception(
                "{'code': '42703', 'message': 'column repositories.status does not exist'}"
            )
        elif cols == "id":
            query.eq.return_value.execute.return_value.data = [{"id": MOCK_REPO_ID}]
        return query

    mock_repo_table = MagicMock()
    mock_repo_table.select.side_effect = select_side_effect

    mock_inv_query = MagicMock()
    mock_inv_query.insert.return_value.execute.return_value.data = [
        {
            "id": MOCK_INV_ID,
            "repository_id": MOCK_REPO_ID,
            "title": "Fallback Handled Case",
            "description": None,
            "status": "draft",
            "created_at": "2026-09-19T14:40:00Z",
            "updated_at": "2026-09-19T14:40:00Z",
        }
    ]

    def table_side_effect(table_name):
        if table_name == "repositories":
            return mock_repo_table
        elif table_name == "investigations":
            return mock_inv_query
        return MagicMock()

    mock_db.table.side_effect = table_side_effect

    with patch("app.services.investigation_service.get_service_role_client", return_value=mock_db):
        resp = client.post(
            "/api/investigations",
            json={
                "repository_id": MOCK_REPO_ID,
                "title": "Fallback Handled Case",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == MOCK_INV_ID
        assert data["status"] == "draft"


def test_schema_fix_migration_sql_validity():
    """Verify that data/phase3_repository_schema_fix.sql contains the required idempotent ALTER TABLE statements."""
    fix_path = Path(__file__).resolve().parent.parent / "data" / "phase3_repository_schema_fix.sql"
    assert fix_path.exists(), "phase3_repository_schema_fix.sql must exist"

    sql = fix_path.read_text(encoding="utf-8")
    assert "ALTER TABLE public.repositories" in sql
    assert "ADD COLUMN IF NOT EXISTS status TEXT" in sql
    assert "ADD COLUMN IF NOT EXISTS error_message TEXT" in sql
    assert "UPDATE public.repositories" in sql
    assert "SET status = 'analyzed'" in sql
    assert "repositories_status_check" in sql
    assert "CHECK (status IN ('analyzed', 'pending', 'failed', 'error'))" in sql
