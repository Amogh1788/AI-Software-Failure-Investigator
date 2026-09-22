import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Search for .env in current directory, backend directory, and root directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BASE_DIR.parent

load_dotenv(dotenv_path=BASE_DIR / ".env")
load_dotenv(dotenv_path=ROOT_DIR / ".env")


class Settings(BaseSettings):
    """Application runtime settings for Phase 5 Production Readiness."""

    # Supabase credentials
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""

    # Server configuration
    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"

    # Service meta & Environment
    SERVICE_NAME: str = "ai-software-failure-investigator"
    ENVIRONMENT: str = "development"  # development, staging, production, test
    LOG_LEVEL: str = "INFO"
    ENABLE_DOCS: Optional[bool] = None

    # Phase 2 Security & Resource Limits
    MAX_REPO_SIZE_MB: int = 100
    MAX_REPO_FILES: int = 10000
    MAX_FILE_SIZE_BYTES: int = 1048576  # 1 MB
    CLONE_TIMEOUT_SECONDS: int = 60
    ANALYSIS_TIMEOUT_SECONDS: int = 60
    MAX_COMMITS_TO_ANALYZE: int = 50

    # Phase 3 Failure Evidence Size Limits (bytes)
    MAX_EVIDENCE_BUG_REPORT_BYTES: int = 51200      # 50 KB
    MAX_EVIDENCE_APP_LOGS_BYTES: int = 512000       # 500 KB
    MAX_EVIDENCE_STACK_TRACE_BYTES: int = 204800    # 200 KB
    MAX_EVIDENCE_TEST_OUTPUT_BYTES: int = 204800    # 200 KB

    # Phase 5 Production Hardening & Limits
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT_PER_MINUTE: int = 120
    RATE_LIMIT_ANALYZE_PER_MINUTE: int = 6
    MAX_EVIDENCE_SIZE_TOTAL_PER_CASE_BYTES: int = 2097152  # 2 MB aggregate per case
    TRUSTED_PROXY_COUNT: int = 0
    BOOTSTRAP_OWNER_USER_ID: str = "00000000-0000-0000-0000-000000000001"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> List[str]:
        origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        if self.ENVIRONMENT.lower() == "production":
            # Strict rejection of wildcard '*' in production when credentials are active
            origins = [o for o in origins if o != "*"]
        return origins

    @property
    def is_docs_enabled(self) -> bool:
        if self.ENABLE_DOCS is not None:
            return self.ENABLE_DOCS
        return self.ENVIRONMENT.lower() != "production"


settings = Settings()
