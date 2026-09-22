import os
import sys
from pathlib import Path
import pytest

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from app.core.config import settings
from app.core.auth import get_current_user, AuthenticatedUser
from app.middleware.rate_limit import reset_rate_limiter

DEFAULT_TEST_USER = AuthenticatedUser(
    id="00000000-0000-0000-0000-000000000001",
    email="test@example.com",
    role="authenticated",
)


@pytest.fixture(autouse=True)
def setup_test_environment():
    """
    Ensures Phase 1–4 tests execute seamlessly by providing default test authentication
    and resetting the in-memory rate limiter.
    Security and rate-limiting tests in test_production_readiness.py manage their own overrides.
    """
    prev_rate_limit = settings.RATE_LIMIT_ENABLED
    prev_env = settings.ENVIRONMENT
    settings.RATE_LIMIT_ENABLED = False
    settings.ENVIRONMENT = "test"
    reset_rate_limiter()

    app.dependency_overrides[get_current_user] = lambda: DEFAULT_TEST_USER

    yield

    app.dependency_overrides.clear()
    settings.RATE_LIMIT_ENABLED = prev_rate_limit
    settings.ENVIRONMENT = prev_env
    reset_rate_limiter()
