import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Search for .env in current directory, backend directory, and root directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BASE_DIR.parent

load_dotenv(dotenv_path=BASE_DIR / ".env")
load_dotenv(dotenv_path=ROOT_DIR / ".env")


class Settings(BaseSettings):
    """Application runtime settings."""

    # Supabase credentials
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # Server configuration
    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"

    # Service meta
    SERVICE_NAME: str = "ai-software-failure-investigator"
    ENVIRONMENT: str = "development"

    # Phase 2 Security & Resource Limits
    MAX_REPO_SIZE_MB: int = 100
    MAX_REPO_FILES: int = 10000
    MAX_FILE_SIZE_BYTES: int = 1048576  # 1 MB
    CLONE_TIMEOUT_SECONDS: int = 60
    ANALYSIS_TIMEOUT_SECONDS: int = 60
    MAX_COMMITS_TO_ANALYZE: int = 50

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
