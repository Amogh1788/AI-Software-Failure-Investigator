import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from app.core import database

client = TestClient(app)


def test_service_role_key_takes_precedence_over_anon_key():
    """Verify that backend prioritizes SUPABASE_SERVICE_ROLE_KEY when configured."""
    database.reset_supabase_client()

    fake_url = "https://test-ref.supabase.co"
    fake_anon = "anon-key-12345"
    fake_service = "service-role-secret-67890"

    with patch.dict(os.environ, {
        "SUPABASE_URL": fake_url,
        "SUPABASE_ANON_KEY": fake_anon,
        "SUPABASE_SERVICE_ROLE_KEY": fake_service,
    }, clear=True), patch("app.core.database.create_client") as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        c = database.get_supabase_client()
        assert c is not None
        mock_create.assert_called_once_with(fake_url, fake_service)


def test_anon_key_used_when_service_role_key_absent():
    """Verify that backend gracefully falls back to SUPABASE_ANON_KEY when service role key is absent."""
    database.reset_supabase_client()

    fake_url = "https://test-ref.supabase.co"
    fake_anon = "anon-key-12345"

    with patch.dict(os.environ, {
        "SUPABASE_URL": fake_url,
        "SUPABASE_ANON_KEY": fake_anon,
        "SUPABASE_SERVICE_ROLE_KEY": "",
    }, clear=True), patch("app.core.database.create_client") as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        c = database.get_supabase_client()
        assert c is not None
        mock_create.assert_called_once_with(fake_url, fake_anon)


def test_no_keys_exposed_in_api_responses():
    """Ensure no secret or anon keys are ever leaked in API response payloads."""
    secret = "secret-service-role-token-value-to-detect"
    with patch.dict(os.environ, {"SUPABASE_SERVICE_ROLE_KEY": secret}):
        resp_health = client.get("/api/health")
        assert resp_health.status_code == 200
        assert secret not in resp_health.text

        resp_health_db = client.get("/api/health/db")
        assert resp_health_db.status_code == 200
        assert secret not in resp_health_db.text

        resp_projects = client.get("/api/projects")
        assert secret not in resp_projects.text


def test_migration_sql_contains_required_rls_policies():
    """Inspect data/phase2_migration.sql to verify RLS is enabled and INSERT policies exist."""
    migration_path = Path(__file__).resolve().parent.parent / "data" / "phase2_migration.sql"
    assert migration_path.exists(), "phase2_migration.sql must exist"

    sql = migration_path.read_text(encoding="utf-8")

    # Verify RLS enabled on all three tables
    assert "ALTER TABLE public.repositories ENABLE ROW LEVEL SECURITY;" in sql
    assert "ALTER TABLE public.repository_files ENABLE ROW LEVEL SECURITY;" in sql
    assert "ALTER TABLE public.repository_commits ENABLE ROW LEVEL SECURITY;" in sql

    # Verify SELECT policies exist
    assert 'CREATE POLICY "Allow public read access to repositories"' in sql
    assert 'CREATE POLICY "Allow public read access to repository_files"' in sql
    assert 'CREATE POLICY "Allow public read access to repository_commits"' in sql

    # Verify INSERT policies exist (allowing backend with anon key to persist)
    assert 'CREATE POLICY "Allow public insert access to repositories"' in sql
    assert 'CREATE POLICY "Allow public insert access to repository_files"' in sql
    assert 'CREATE POLICY "Allow public insert access to repository_commits"' in sql
