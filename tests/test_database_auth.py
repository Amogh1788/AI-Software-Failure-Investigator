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


def test_secret_key_takes_precedence_over_service_role_key():
    """Verify that backend prioritizes SUPABASE_SECRET_KEY over SUPABASE_SERVICE_ROLE_KEY."""
    database.reset_supabase_client()

    fake_url = "https://test-ref.supabase.co"
    fake_anon = "anon-key-12345"
    fake_service = "service-role-legacy-67890"
    fake_secret = "secret-key-primary-13579"

    with patch.dict(os.environ, {
        "SUPABASE_URL": fake_url,
        "SUPABASE_ANON_KEY": fake_anon,
        "SUPABASE_SERVICE_ROLE_KEY": fake_service,
        "SUPABASE_SECRET_KEY": fake_secret,
    }, clear=True), patch("app.core.database.create_client") as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        # get_supabase_client should use fake_secret
        c = database.get_supabase_client()
        assert c is not None
        mock_create.assert_called_once_with(fake_url, fake_secret)

    database.reset_supabase_client()
    with patch.dict(os.environ, {
        "SUPABASE_URL": fake_url,
        "SUPABASE_SERVICE_ROLE_KEY": fake_service,
        "SUPABASE_SECRET_KEY": fake_secret,
    }, clear=True), patch("app.core.database.create_client") as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        # get_service_role_client should also prioritize fake_secret
        sc = database.get_service_role_client()
        assert sc is not None
        mock_create.assert_called_once_with(fake_url, fake_secret)


def test_service_role_key_fallback_when_secret_key_absent():
    """Verify that backend uses SUPABASE_SERVICE_ROLE_KEY as temporary fallback when secret key is absent."""
    database.reset_supabase_client()

    fake_url = "https://test-ref.supabase.co"
    fake_anon = "anon-key-12345"
    fake_service = "service-role-legacy-67890"

    with patch.dict(os.environ, {
        "SUPABASE_URL": fake_url,
        "SUPABASE_ANON_KEY": fake_anon,
        "SUPABASE_SERVICE_ROLE_KEY": fake_service,
        "SUPABASE_SECRET_KEY": "",
    }, clear=True), patch("app.core.database.create_client") as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        c = database.get_supabase_client()
        assert c is not None
        mock_create.assert_called_once_with(fake_url, fake_service)

    database.reset_supabase_client()
    with patch.dict(os.environ, {
        "SUPABASE_URL": fake_url,
        "SUPABASE_SERVICE_ROLE_KEY": fake_service,
        "SUPABASE_SECRET_KEY": "",
    }, clear=True), patch("app.core.database.create_client") as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        sc = database.get_service_role_client()
        assert sc is not None
        mock_create.assert_called_once_with(fake_url, fake_service)


def test_production_works_with_only_secret_key():
    """Verify that production operates normally with ONLY SUPABASE_SECRET_KEY configured."""
    database.reset_supabase_client()

    fake_url = "https://prod-ref.supabase.co"
    fake_secret = "secret-key-prod-standalone"

    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "SUPABASE_URL": fake_url,
        "SUPABASE_SECRET_KEY": fake_secret,
        "SUPABASE_SERVICE_ROLE_KEY": "",
        "SUPABASE_ANON_KEY": "",
    }, clear=True), patch("app.core.database.create_client") as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        c = database.get_supabase_client()
        assert c is not None
        mock_create.assert_called_once_with(fake_url, fake_secret)

    database.reset_supabase_client()
    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "SUPABASE_URL": fake_url,
        "SUPABASE_SECRET_KEY": fake_secret,
        "SUPABASE_SERVICE_ROLE_KEY": "",
        "SUPABASE_ANON_KEY": "",
    }, clear=True), patch("app.core.database.create_client") as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        sc = database.get_service_role_client()
        assert sc is not None
        mock_create.assert_called_once_with(fake_url, fake_secret)


def test_production_fails_cleanly_when_neither_secret_nor_legacy_service_key_exists():
    """Verify production fails with a controlled RuntimeError when neither secret nor legacy service key exists."""
    database.reset_supabase_client()

    fake_url = "https://prod-ref.supabase.co"

    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "SUPABASE_URL": fake_url,
        "SUPABASE_SECRET_KEY": "",
        "SUPABASE_SERVICE_ROLE_KEY": "",
        "SUPABASE_ANON_KEY": "anon-key-should-not-be-used",
    }, clear=True):
        import pytest
        with pytest.raises(RuntimeError) as exc_info:
            database.get_supabase_client()

        assert "SUPABASE_SECRET_KEY is required" in str(exc_info.value)
        # Verify get_service_role_client cleanly returns None
        assert database.get_service_role_client() is None


def test_anon_key_never_used_as_privileged_production_fallback():
    """Strictly verify that SUPABASE_ANON_KEY is never used for privileged production database operations."""
    database.reset_supabase_client()

    fake_url = "https://prod-ref.supabase.co"
    fake_anon = "anon-key-publishable-only"

    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "SUPABASE_URL": fake_url,
        "SUPABASE_ANON_KEY": fake_anon,
        "SUPABASE_SECRET_KEY": "",
        "SUPABASE_SERVICE_ROLE_KEY": "",
    }, clear=True), patch("app.core.database.create_client") as mock_create:
        import pytest
        with pytest.raises(RuntimeError):
            database.get_supabase_client()

        # create_client must NOT have been called with anon key in production
        mock_create.assert_not_called()
        assert database.get_service_role_client() is None


def test_existing_development_behavior_remains_compatible():
    """Verify development environment falls back to SUPABASE_ANON_KEY when privileged keys are absent."""
    database.reset_supabase_client()

    fake_url = "https://dev-ref.supabase.co"
    fake_anon = "anon-key-dev-12345"

    with patch.dict(os.environ, {
        "ENVIRONMENT": "development",
        "SUPABASE_URL": fake_url,
        "SUPABASE_ANON_KEY": fake_anon,
        "SUPABASE_SECRET_KEY": "",
        "SUPABASE_SERVICE_ROLE_KEY": "",
    }, clear=True), patch("app.core.database.create_client") as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        # get_supabase_client falls back to anon key in development
        c = database.get_supabase_client()
        assert c is not None
        mock_create.assert_called_once_with(fake_url, fake_anon)

        # get_service_role_client strictly does NOT fall back to anon key
        assert database.get_service_role_client() is None


def test_secret_values_never_returned_in_api_responses_or_logs(caplog):
    """Ensure no secret values are ever leaked in API response payloads or logs."""
    import logging
    secret_key = "super-secret-key-token-never-expose-xyz987"
    service_key = "legacy-service-key-token-never-expose-abc123"

    with patch.dict(os.environ, {
        "SUPABASE_SECRET_KEY": secret_key,
        "SUPABASE_SERVICE_ROLE_KEY": service_key,
    }):
        resp_health = client.get("/api/health")
        assert resp_health.status_code == 200
        assert secret_key not in resp_health.text
        assert service_key not in resp_health.text

        resp_health_db = client.get("/api/health/db")
        assert resp_health_db.status_code == 200
        assert secret_key not in resp_health_db.text
        assert service_key not in resp_health_db.text

        resp_projects = client.get("/api/projects")
        assert secret_key not in resp_projects.text
        assert service_key not in resp_projects.text

    # Verify log output records the key name in production but never the key value
    database.reset_supabase_client()
    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SECRET_KEY": secret_key,
        "SUPABASE_SERVICE_ROLE_KEY": "",
    }, clear=True), patch("app.core.database.create_client") as mock_create:
        mock_create.return_value = MagicMock()
        with caplog.at_level(logging.INFO):
            database.get_supabase_client()

        # Log mentions SUPABASE_SECRET_KEY
        assert any("SUPABASE_SECRET_KEY" in rec.message for rec in caplog.records)
        # Log NEVER contains the secret value
        for rec in caplog.records:
            assert secret_key not in rec.message
            assert service_key not in rec.message


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
