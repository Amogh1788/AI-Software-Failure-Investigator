import os
import time
import jwt
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.auth import get_current_user, AuthenticatedUser
from app.core import database
from app.middleware.rate_limit import reset_rate_limiter, rate_limiter

client = TestClient(app)
TEST_JWT_SECRET = "phase5-super-secret-jwt-signing-key-12345678901234567890"


# ==============================================================================
# 1. AUTHENTICATION TESTS
# ==============================================================================

def test_auth_missing_token_returns_401():
    """Verify missing Authorization header returns HTTP 401."""
    app.dependency_overrides.clear()
    resp = client.get("/api/investigations")
    assert resp.status_code == 401
    assert "credentials were not provided" in resp.json()["detail"].lower()


def test_auth_malformed_token_returns_401():
    """Verify malformed Authorization header returns HTTP 401."""
    app.dependency_overrides.clear()
    resp = client.get("/api/investigations", headers={"Authorization": "Basic 12345"})
    assert resp.status_code == 401
    assert "invalid authorization header format" in resp.json()["detail"].lower()


def test_auth_invalid_signature_returns_401():
    """Verify token signed with wrong key returns HTTP 401."""
    app.dependency_overrides.clear()
    token = jwt.encode(
        {"sub": "user-attacker", "exp": int(time.time()) + 3600},
        "wrong-secret-key-that-is-at-least-32-bytes-long",
        algorithm="HS256",
    )
    with patch.object(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET):
        resp = client.get("/api/investigations", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert "invalid authentication token" in resp.json()["detail"].lower()


def test_auth_expired_token_returns_401():
    """Verify expired token returns HTTP 401."""
    app.dependency_overrides.clear()
    expired_token = jwt.encode(
        {"sub": "user-expired", "exp": int(time.time()) - 3600},
        TEST_JWT_SECRET,
        algorithm="HS256",
    )
    with patch.object(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET):
        resp = client.get("/api/investigations", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401
    assert "token has expired" in resp.json()["detail"].lower()


def test_auth_valid_token_derives_user_identity():
    """Verify valid cryptographic JWT extracts user identity and allows access."""
    app.dependency_overrides.clear()
    token = jwt.encode(
        {"sub": "verified-user-123", "email": "user@example.com", "exp": int(time.time()) + 3600},
        TEST_JWT_SECRET,
        algorithm="HS256",
    )

    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.or_.return_value.order.return_value.execute.return_value.data = []
    mock_db.table.return_value.select.return_value.execute.return_value.data = []

    with patch.object(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET), \
         patch("app.services.investigation_service.get_service_role_client", return_value=mock_db):
        resp = client.get("/api/investigations", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    assert resp.json() == []


# ==============================================================================
# 2. AUTHORIZATION & OWNERSHIP TESTS
# ==============================================================================

def test_user_a_can_access_own_investigation():
    """Verify user A can successfully access their own investigation (HTTP 200)."""
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id="user-A-uuid",
        email="userA@test.com",
    )

    mock_db = MagicMock()
    mock_inv_query = MagicMock()
    mock_inv_query.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": "inv-owned-by-user-a",
            "repository_id": "repo-123",
            "title": "User A Investigation",
            "owner_user_id": "user-A-uuid",
            "status": "draft",
            "created_at": "2026-09-21T00:00:00Z",
            "updated_at": "2026-09-21T00:00:00Z",
        }
    ]
    mock_repo_query = MagicMock()
    mock_repo_query.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": "repo-123",
            "github_url": "https://github.com/example/repo",
            "owner": "example",
            "name": "repo",
            "analyzed_at": "2026-09-21T00:00:00Z",
            "created_at": "2026-09-21T00:00:00Z",
        }
    ]
    mock_evid_query = MagicMock()
    mock_evid_query.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []

    mock_db.table.side_effect = lambda table: {
        "investigations": mock_inv_query,
        "repositories": mock_repo_query,
        "investigation_evidence": mock_evid_query,
    }.get(table, MagicMock())

    with patch("app.services.investigation_service.get_service_role_client", return_value=mock_db), \
         patch("app.services.evidence_service.get_service_role_client", return_value=mock_db):
        resp = client.get("/api/investigations/inv-owned-by-user-a")

    assert resp.status_code == 200
    assert resp.json()["investigation"]["id"] == "inv-owned-by-user-a"
    assert resp.json()["investigation"]["owner_user_id"] == "user-A-uuid"


def test_user_b_cannot_access_user_a_investigation():
    """Verify user B is rejected with HTTP 403 when requesting user A's investigation."""
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id="user-B-uuid",
        email="userB@test.com",
    )

    mock_db = MagicMock()
    mock_inv_query = MagicMock()
    mock_inv_query.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": "inv-owned-by-user-a",
            "repository_id": "repo-123",
            "title": "User A Investigation",
            "owner_user_id": "user-A-uuid",
            "status": "draft",
        }
    ]
    mock_db.table.return_value = mock_inv_query

    with patch("app.services.investigation_service.get_service_role_client", return_value=mock_db):
        resp = client.get("/api/investigations/inv-owned-by-user-a")

    assert resp.status_code == 403
    assert "forbidden" in resp.json()["detail"].lower()


def test_user_b_cannot_read_evidence_of_user_a():
    """Verify user B cannot read evidence attached to user A's investigation (HTTP 403)."""
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id="user-B-uuid",
        email="userB@test.com",
    )

    mock_db = MagicMock()
    mock_inv_query = MagicMock()
    mock_inv_query.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": "inv-owned-by-user-a",
            "owner_user_id": "user-A-uuid",
            "status": "draft",
        }
    ]
    mock_db.table.return_value = mock_inv_query

    with patch("app.services.evidence_service.get_service_role_client", return_value=mock_db), \
         patch("app.services.investigation_service.get_service_role_client", return_value=mock_db):
        resp = client.get("/api/investigations/inv-owned-by-user-a/evidence")

    assert resp.status_code == 403
    assert "forbidden" in resp.json()["detail"].lower()


def test_user_b_cannot_modify_user_a_evidence():
    """Verify user B cannot add evidence to user A's investigation (HTTP 403)."""
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id="user-B-uuid",
        email="userB@test.com",
    )

    mock_db = MagicMock()
    mock_inv_query = MagicMock()
    mock_inv_query.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": "inv-owned-by-user-a",
            "owner_user_id": "user-A-uuid",
            "status": "draft",
        }
    ]
    mock_db.table.return_value = mock_inv_query

    with patch("app.services.evidence_service.get_service_role_client", return_value=mock_db), \
         patch("app.services.investigation_service.get_service_role_client", return_value=mock_db):
        resp = client.post(
            "/api/investigations/inv-owned-by-user-a/evidence",
            json={
                "evidence_type": "bug_report",
                "title": "Malicious Injection",
                "content": "Attacker payload",
            },
        )

    assert resp.status_code == 403
    assert "forbidden" in resp.json()["detail"].lower()


def test_user_b_cannot_delete_evidence_of_user_a():
    """Verify user B cannot delete an evidence item from user A's investigation (HTTP 403)."""
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id="user-B-uuid",
        email="userB@test.com",
    )

    mock_db = MagicMock()
    mock_inv_query = MagicMock()
    mock_inv_query.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": "inv-owned-by-user-a",
            "owner_user_id": "user-A-uuid",
            "status": "draft",
        }
    ]
    mock_db.table.return_value = mock_inv_query

    with patch("app.services.evidence_service.get_service_role_client", return_value=mock_db), \
         patch("app.services.investigation_service.get_service_role_client", return_value=mock_db):
        resp = client.delete("/api/investigations/inv-owned-by-user-a/evidence/ev-123")

    assert resp.status_code == 403
    assert "forbidden" in resp.json()["detail"].lower()


def test_user_b_cannot_analyze_user_a_investigation():
    """Verify user B cannot trigger analysis on user A's investigation (HTTP 403)."""
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id="user-B-uuid",
        email="userB@test.com",
    )

    mock_db = MagicMock()
    mock_inv_query = MagicMock()
    mock_inv_query.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": "inv-owned-by-user-a",
            "owner_user_id": "user-A-uuid",
            "status": "ready",
        }
    ]
    mock_db.table.return_value = mock_inv_query

    with patch("app.services.analysis_service.get_service_role_client", return_value=mock_db), \
         patch("app.services.investigation_service.get_service_role_client", return_value=mock_db):
        resp = client.post("/api/investigations/inv-owned-by-user-a/analyze")

    assert resp.status_code == 403
    assert "forbidden" in resp.json()["detail"].lower()


def test_no_universal_bootstrap_owner_bypass():
    """Verify that BOOTSTRAP_OWNER_USER_ID is NOT accessible to arbitrary users (bypass removed)."""
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id="user-arbitrary-uuid",
        email="arbitrary@test.com",
    )

    mock_db = MagicMock()
    mock_inv_query = MagicMock()
    mock_inv_query.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": "inv-bootstrap-owned",
            "owner_user_id": "00000000-0000-0000-0000-000000000001",
            "status": "draft",
        }
    ]
    mock_db.table.return_value = mock_inv_query

    with patch("app.services.investigation_service.get_service_role_client", return_value=mock_db):
        resp = client.get("/api/investigations/inv-bootstrap-owned")

    assert resp.status_code == 403
    assert "forbidden" in resp.json()["detail"].lower()


def test_null_owner_investigation_is_rejected():
    """Verify that an investigation with NULL owner is strictly rejected (no legacy bypass)."""
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id="user-normal-uuid",
        email="normal@test.com",
    )

    mock_db = MagicMock()
    mock_inv_query = MagicMock()
    mock_inv_query.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": "inv-null-owner",
            "owner_user_id": None,
            "status": "draft",
        }
    ]
    mock_db.table.return_value = mock_inv_query

    with patch("app.services.investigation_service.get_service_role_client", return_value=mock_db):
        resp = client.get("/api/investigations/inv-null-owner")

    assert resp.status_code == 403
    assert "forbidden" in resp.json()["detail"].lower()


def test_production_database_client_requires_service_role_key():
    """Verify that in production, get_supabase_client() raises a controlled RuntimeError if secret/service-role key is missing."""
    database.reset_supabase_client()

    fake_url = "https://prod-ref.supabase.co"
    fake_anon = "anon-key-12345"

    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "SUPABASE_URL": fake_url,
        "SUPABASE_ANON_KEY": fake_anon,
        "SUPABASE_SECRET_KEY": "",
        "SUPABASE_SERVICE_ROLE_KEY": "",
    }, clear=True):
        import pytest
        with pytest.raises(RuntimeError) as exc_info:
            database.get_supabase_client()

        assert "SUPABASE_SECRET_KEY is required" in str(exc_info.value)
        assert "SUPABASE_SERVICE_ROLE_KEY is required" in str(exc_info.value)


def test_production_database_client_works_with_only_secret_key():
    """Verify that in production, get_supabase_client() successfully initializes with only SUPABASE_SECRET_KEY."""
    database.reset_supabase_client()

    fake_url = "https://prod-ref.supabase.co"
    fake_secret = "secret-key-prod-999"

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


# ==============================================================================
# 3. RATE LIMITING TESTS
# ==============================================================================

def test_heavy_endpoint_rate_limiting():
    """Verify heavy endpoint throttles after RATE_LIMIT_ANALYZE_PER_MINUTE."""
    reset_rate_limiter()
    with patch.object(settings, "RATE_LIMIT_ENABLED", True), \
         patch.object(settings, "RATE_LIMIT_ANALYZE_PER_MINUTE", 2):

        # 1st request succeeds
        resp1 = client.post("/api/repositories/analyze", json={"github_url": "invalid-url"})
        assert resp1.status_code != 429

        # 2nd request succeeds
        resp2 = client.post("/api/repositories/analyze", json={"github_url": "invalid-url"})
        assert resp2.status_code != 429

        # 3rd request should hit rate limiter -> HTTP 429
        resp3 = client.post("/api/repositories/analyze", json={"github_url": "invalid-url"})
        assert resp3.status_code == 429
        assert "Retry-After" in resp3.headers
        assert "Rate limit exceeded" in resp3.json()["detail"]
        assert resp3.json()["error_code"] == "RATE_LIMIT_EXCEEDED"

    reset_rate_limiter()


def test_rate_limiter_can_be_disabled():
    """Verify rate limiter is bypassed when RATE_LIMIT_ENABLED=False."""
    reset_rate_limiter()
    with patch.object(settings, "RATE_LIMIT_ENABLED", False):
        for _ in range(5):
            resp = client.post("/api/repositories/analyze", json={"github_url": "invalid-url"})
            assert resp.status_code != 429
    reset_rate_limiter()


# ==============================================================================
# 4. SECURITY HEADERS TESTS
# ==============================================================================

def test_security_headers_present():
    """Verify modern OWASP security headers are present on all responses."""
    resp = client.get("/api/health")
    assert resp.status_code == 200

    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in resp.headers.get("Content-Security-Policy", "")
    assert "X-XSS-Protection" not in resp.headers  # Obsolete header must NOT be used
    assert "X-Request-ID" in resp.headers


def test_hsts_header_in_production():
    """Verify Strict-Transport-Security is enabled in production environment."""
    with patch.object(settings, "ENVIRONMENT", "production"):
        resp = client.get("/api/health")
        assert "Strict-Transport-Security" in resp.headers
        assert "max-age=" in resp.headers["Strict-Transport-Security"]


# ==============================================================================
# 5. ERROR SANITIZATION & REQUEST ID TESTS
# ==============================================================================

def test_unhandled_exception_is_sanitized_with_request_id():
    """Verify internal server errors return sanitized JSON with request_id and zero traceback leakage."""
    client_no_raise = TestClient(app, raise_server_exceptions=False)
    with patch("app.api.health.ProjectService.get_database_health", side_effect=RuntimeError("Secret database path: /var/secrets/key.pem")):
        resp = client_no_raise.get("/api/health/db")

    assert resp.status_code == 500
    data = resp.json()
    assert data["error_code"] == "INTERNAL_SERVER_ERROR"
    assert "An unexpected internal server error occurred." in data["detail"]
    assert "secret" not in data["detail"].lower()
    assert "/var/secrets" not in data["detail"]
    assert "request_id" in data
    assert resp.headers.get("X-Request-ID") == data["request_id"]


# ==============================================================================
# 6. HEALTH & READINESS PROBES
# ==============================================================================

def test_health_live_probe():
    """Verify /api/health/live returns process liveness."""
    resp = client.get("/api/health/live")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["probe"] == "liveness"


def test_health_ready_probe_healthy():
    """Verify /api/health/ready returns 200 when Git and Database are healthy."""
    with patch("shutil.which", return_value="/usr/bin/git"), \
         patch("app.services.project_service.ProjectService.get_database_health", return_value=MagicMock(status="connected")):
        resp = client.get("/api/health/ready")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["dependencies"]["git"] == "available"
    assert data["dependencies"]["database"] == "connected"


def test_health_ready_probe_db_failure_returns_503():
    """Verify /api/health/ready returns 503 when Supabase database is unreachable."""
    with patch("shutil.which", return_value="/usr/bin/git"), \
         patch("app.services.project_service.ProjectService.get_database_health", return_value=MagicMock(status="disconnected")):
        resp = client.get("/api/health/ready")

    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "unavailable"
    assert data["dependencies"]["database"] == "disconnected"


def test_health_ready_probe_git_missing_returns_503():
    """Verify /api/health/ready returns 503 when Git executable is not in PATH."""
    with patch("shutil.which", return_value=None), \
         patch("app.services.project_service.ProjectService.get_database_health", return_value=MagicMock(status="connected")):
        resp = client.get("/api/health/ready")

    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "unavailable"
    assert data["dependencies"]["git"] == "missing"


# ==============================================================================
# 7. CORS & PRODUCTION CONFIGURATION TESTS
# ==============================================================================

def test_cors_wildcard_rejected_in_production():
    """Verify wildcard '*' origin is filtered out in production mode."""
    with patch.object(settings, "ENVIRONMENT", "production"), \
         patch.object(settings, "CORS_ORIGINS", "*,https://app.example.com"):
        origins = settings.cors_origin_list
        assert "*" not in origins
        assert "https://app.example.com" in origins


def test_docs_disabled_in_production_by_default():
    """Verify documentation is disabled by default in production."""
    with patch.object(settings, "ENVIRONMENT", "production"), \
         patch.object(settings, "ENABLE_DOCS", None):
        assert settings.is_docs_enabled is False


def test_docs_enabled_in_development():
    """Verify documentation is enabled in development environment."""
    with patch.object(settings, "ENVIRONMENT", "development"), \
         patch.object(settings, "ENABLE_DOCS", None):
        assert settings.is_docs_enabled is True


# ==============================================================================
# 8. AGGREGATE EVIDENCE SIZE LIMIT TEST
# ==============================================================================

def test_aggregate_evidence_limit_enforced():
    """Verify aggregate evidence size limit per case (returns HTTP 413)."""
    mock_db = MagicMock()
    mock_inv = MagicMock()
    mock_inv.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "inv-case-1", "owner_user_id": "00000000-0000-0000-0000-000000000001", "status": "draft"}
    ]

    # Pre-existing evidence already at 1.9 MB
    big_content = "X" * 1900000
    mock_evid = MagicMock()
    mock_evid.select.return_value.eq.return_value.execute.return_value.data = [
        {"content": big_content}
    ]

    def table_mock(table):
        if table == "investigations":
            return mock_inv
        elif table == "investigation_evidence":
            return mock_evid
        return MagicMock()

    mock_db.table.side_effect = table_mock

    # Adding another 200 KB (total 2.1 MB > 2 MB max)
    payload = {
        "evidence_type": "stack_trace",
        "title": "Overflowing Trace",
        "content": "Y" * 200000,
    }

    with patch("app.services.evidence_service.get_service_role_client", return_value=mock_db), \
         patch.object(settings, "MAX_EVIDENCE_SIZE_TOTAL_PER_CASE_BYTES", 2000000):
        resp = client.post("/api/investigations/inv-case-1/evidence", json=payload)

    assert resp.status_code == 413
    assert "Aggregate evidence limit exceeded" in resp.json()["detail"]
