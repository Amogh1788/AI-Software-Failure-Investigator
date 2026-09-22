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
    secret_key = (
        os.getenv("SUPABASE_SECRET_KEY")
        if "SUPABASE_SECRET_KEY" in os.environ
        else settings.SUPABASE_SECRET_KEY or ""
    ).strip()
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

    env_mode = (os.getenv("ENVIRONMENT") or settings.ENVIRONMENT or "development").strip().lower()

    # In production, require SUPABASE_SECRET_KEY (or legacy SUPABASE_SERVICE_ROLE_KEY)
    # for server data operations rather than silently falling back to publishable SUPABASE_ANON_KEY.
    if env_mode == "production":
        if secret_key and "your-secret-key" not in secret_key:
            key = secret_key
            key_type = "secret (privileged)"
            logger.info("Using SUPABASE_SECRET_KEY for database operations in production environment.")
        elif service_role_key and "your-service-role-key" not in service_role_key:
            key = service_role_key
            key_type = "legacy service-role (privileged)"
            logger.warning(
                "Using legacy SUPABASE_SERVICE_ROLE_KEY fallback for database operations in production environment. "
                "Please migrate to SUPABASE_SECRET_KEY."
            )
        else:
            logger.error(
                "Configuration error: SUPABASE_SECRET_KEY is required for database operations in production environment. "
                "Falling back to publishable anon key is strictly prohibited in production."
            )
            raise RuntimeError(
                "Database configuration error: SUPABASE_SECRET_KEY is required for server database operations in production "
                "(SUPABASE_SERVICE_ROLE_KEY is required as legacy fallback)."
            )
    else:
        # In non-production (development / test), prioritize secret key, then legacy service-role key;
        # otherwise fall back to anon key.
        if secret_key and "your-secret-key" not in secret_key:
            key = secret_key
            key_type = "secret (privileged)"
        elif service_role_key and "your-service-role-key" not in service_role_key:
            key = service_role_key
            key_type = "legacy service-role (privileged)"
        else:
            key = anon_key
            key_type = "anon (publishable)"

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
    Private investigation operations MUST use SUPABASE_SECRET_KEY (or legacy SUPABASE_SERVICE_ROLE_KEY).
    Does NOT fall back to SUPABASE_ANON_KEY.
    """
    global _service_role_client, _last_service_url, _last_service_key

    load_dotenv(dotenv_path=BASE_DIR / ".env", override=False)
    load_dotenv(dotenv_path=ROOT_DIR / ".env", override=False)

    url = (os.getenv("SUPABASE_URL") if "SUPABASE_URL" in os.environ else settings.SUPABASE_URL or "").strip()
    secret_key = (
        os.getenv("SUPABASE_SECRET_KEY")
        if "SUPABASE_SECRET_KEY" in os.environ
        else settings.SUPABASE_SECRET_KEY or ""
    ).strip()
    service_role_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if "SUPABASE_SERVICE_ROLE_KEY" in os.environ
        else settings.SUPABASE_SERVICE_ROLE_KEY or ""
    ).strip()

    key = ""
    is_secret = False
    if secret_key and "your-secret-key" not in secret_key:
        key = secret_key
        is_secret = True
    elif service_role_key and "your-service-role-key" not in service_role_key:
        key = service_role_key
        is_secret = False

    if _service_role_client is not None and url == _last_service_url and key == _last_service_key:
        return _service_role_client

    if not url or not key or "your-project" in url:
        return None

    try:
        _service_role_client = create_client(url, key)
        _last_service_url = url
        _last_service_key = key
        if is_secret:
            logger.info("Supabase service client initialized using SUPABASE_SECRET_KEY.")
        else:
            logger.warning("Supabase service client initialized using legacy SUPABASE_SERVICE_ROLE_KEY fallback.")
        return _service_role_client
    except Exception as exc:
        logger.error(f"Failed to initialize Supabase service client: {exc}")
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
    try:
        client = get_supabase_client()
    except RuntimeError as cfg_err:
        return False, str(cfg_err)
    except Exception as exc:
        return False, f"Supabase initialization error: {exc}"

    if not client:
        return False, "Supabase client not initialized (missing or invalid SUPABASE_URL / SUPABASE_SECRET_KEY / SUPABASE_SERVICE_ROLE_KEY / SUPABASE_ANON_KEY in backend/.env)."

    try:
        # Perform a lightweight query against the projects table
        response = client.table("projects").select("id", count="exact").limit(1).execute()
        count_str = f"projects count: {response.count}" if response.count is not None else "connected"
        return True, f"Supabase PostgreSQL connected ({count_str})."
    except Exception as exc:
        error_msg = str(exc)
        logger.warning(f"Supabase connection check failed: {error_msg}")
        return False, f"Supabase connection failed: {error_msg}"
