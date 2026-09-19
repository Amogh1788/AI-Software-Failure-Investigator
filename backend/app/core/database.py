import logging
import os
from typing import Optional, Tuple
from supabase import Client, create_client
from dotenv import load_dotenv
from app.core.config import settings, BASE_DIR, ROOT_DIR

logger = logging.getLogger("ai_investigator.database")

_supabase_client: Optional[Client] = None
_last_url: str = ""
_last_key: str = ""

_service_role_client: Optional[Client] = None
_last_service_url: str = ""
_last_service_key: str = ""


def get_supabase_client() -> Optional[Client]:
    """Retrieve or dynamically initialize the Supabase client."""
    global _supabase_client, _last_url, _last_key

    # Re-read environment files dynamically in case credentials were just added
    load_dotenv(dotenv_path=BASE_DIR / ".env", override=False)
    load_dotenv(dotenv_path=ROOT_DIR / ".env", override=False)

    url = (os.getenv("SUPABASE_URL") if "SUPABASE_URL" in os.environ else settings.SUPABASE_URL or "").strip()
    service_role_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if "SUPABASE_SERVICE_ROLE_KEY" in os.environ
        else settings.SUPABASE_SERVICE_ROLE_KEY or ""
    ).strip()
    anon_key = (
        os.getenv("SUPABASE_ANON_KEY")
        if "SUPABASE_ANON_KEY" in os.environ
        else settings.SUPABASE_ANON_KEY or ""
    ).strip()

    # Prioritize privileged service-role key if provided; otherwise fall back to anon key
    key = service_role_key or anon_key
    key_type = "service-role (privileged)" if service_role_key else "anon (publishable)"

    # If already created with same credentials, return existing client
    if _supabase_client is not None and url == _last_url and key == _last_key:
        return _supabase_client

    if not url or not key or "your-project" in url or "your-anon-key" in key:
        return None

    try:
        _supabase_client = create_client(url, key)
        _last_url = url
        _last_key = key
        logger.info(f"Supabase client successfully initialized for {url} using {key_type} key.")
        return _supabase_client
    except Exception as exc:
        logger.error(f"Failed to initialize Supabase client: {exc}")
        return None


def get_service_role_client() -> Optional[Client]:
    """
    Retrieve or dynamically initialize the dedicated server-side Supabase client.
    STRICT SECURITY REQUIREMENT:
    Phase 3 private investigation operations MUST use SUPABASE_SERVICE_ROLE_KEY.
    Does NOT fall back to SUPABASE_ANON_KEY.
    """
    global _service_role_client, _last_service_url, _last_service_key

    load_dotenv(dotenv_path=BASE_DIR / ".env", override=False)
    load_dotenv(dotenv_path=ROOT_DIR / ".env", override=False)

    url = (os.getenv("SUPABASE_URL") if "SUPABASE_URL" in os.environ else settings.SUPABASE_URL or "").strip()
    service_role_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if "SUPABASE_SERVICE_ROLE_KEY" in os.environ
        else settings.SUPABASE_SERVICE_ROLE_KEY or ""
    ).strip()

    if _service_role_client is not None and url == _last_service_url and service_role_key == _last_service_key:
        return _service_role_client

    if not url or not service_role_key or "your-project" in url or "your-service-role-key" in service_role_key:
        return None

    try:
        _service_role_client = create_client(url, service_role_key)
        _last_service_url = url
        _last_service_key = service_role_key
        logger.info(f"Supabase service-role client initialized for private operations.")
        return _service_role_client
    except Exception as exc:
        logger.error(f"Failed to initialize Supabase service-role client: {exc}")
        return None


def reset_supabase_client():
    """Reset the client state."""
    global _supabase_client, _last_url, _last_key, _service_role_client, _last_service_url, _last_service_key
    _supabase_client = None
    _last_url = ""
    _last_key = ""
    _service_role_client = None
    _last_service_url = ""
    _last_service_key = ""


def check_database_connection() -> Tuple[bool, str]:
    """
    Perform a real health check against Supabase PostgreSQL.
    Returns (is_connected, message).
    """
    client = get_supabase_client()
    if not client:
        return False, "Supabase client not initialized (missing or invalid SUPABASE_URL / SUPABASE_ANON_KEY / SUPABASE_SERVICE_ROLE_KEY in backend/.env)."

    try:
        # Perform a lightweight query against the projects table
        response = client.table("projects").select("id", count="exact").limit(1).execute()
        count_str = f"projects count: {response.count}" if response.count is not None else "connected"
        return True, f"Supabase PostgreSQL connected ({count_str})."
    except Exception as exc:
        error_msg = str(exc)
        logger.warning(f"Supabase connection check failed: {error_msg}")
        return False, f"Supabase connection failed: {error_msg}"
