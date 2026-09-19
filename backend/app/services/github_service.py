import os
import re
import shutil
import subprocess
import logging
from typing import Tuple, Dict
from urllib.parse import urlparse
from fastapi import HTTPException, status
import git
from app.core.config import settings

logger = logging.getLogger("ai_investigator.github_service")

# Regex strictly matching public GitHub HTTPS repository URLs
GITHUB_HTTPS_REGEX = re.compile(
    r"^https://(?:www\.)?github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(?:\.git)?/?$"
)


class GitHubService:
    """Service for validating, parsing, and securely cloning GitHub repositories."""

    @staticmethod
    def verify_git_installation() -> str:
        """
        Verify that the Git executable is installed and reachable via PATH.
        Raises an HTTPException with a clear setup error if not available.
        """
        git_path = shutil.which("git")
        if not git_path:
            logger.error("Git executable not found in system PATH.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="System configuration error: Git executable is not installed or not available in PATH.",
            )
        return git_path

    @staticmethod
    def validate_and_parse_url(url: str) -> Tuple[str, str, str]:
        """
        Validate and normalize a public GitHub HTTPS URL.
        Returns (normalized_url, owner, repo_name).
        Raises HTTPException(400) if the URL is invalid, non-GitHub, SSH, or malformed.
        """
        if not url or not isinstance(url, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Repository URL is required.",
            )

        trimmed = url.strip()

        # Reject SSH, file, and non-https schemes
        if trimmed.startswith("git@") or "ssh://" in trimmed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SSH URLs are not supported. Please provide a public GitHub HTTPS URL (e.g. https://github.com/owner/repo).",
            )

        if not trimmed.startswith("https://"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only HTTPS URLs are supported. URL must start with https://github.com/.",
            )

        match = GITHUB_HTTPS_REGEX.match(trimmed)
        if not match:
            # Check if domain is non-GitHub
            parsed = urlparse(trimmed)
            if parsed.netloc and "github.com" not in parsed.netloc.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported host '{parsed.netloc}'. Only public GitHub repositories (github.com) are supported.",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed GitHub URL. Expected format: https://github.com/owner/repository",
            )

        owner = match.group(1)
        name = match.group(2)

        # Disallow directory traversal or illegal naming
        if owner in (".", "..") or name in (".", "..") or "/" in owner or "/" in name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid characters in repository owner or name.",
            )

        normalized_url = f"https://github.com/{owner}/{name}"
        return normalized_url, owner, name

    @classmethod
    def clone_repository_safely(cls, normalized_url: str, target_dir: str) -> git.Repo:
        """
        Clone a public repository into a designated temporary directory with an enforced hard timeout.
        Uses depth=50 shallow clone to safely inspect recent history without downloading full history.
        Enforces process-level termination on timeout and checks size limits.
        """
        cls.verify_git_installation()

        env = os.environ.copy()
        # Prevent git from interactively prompting for username/password or opening credential GUI
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GIT_ASKPASS"] = ""

        clone_cmd = [
            "git",
            "clone",
            "--depth",
            str(settings.MAX_COMMITS_TO_ANALYZE),
            "--single-branch",
            "--quiet",
            normalized_url,
            target_dir,
        ]

        logger.info(f"Cloning {normalized_url} into temporary directory with {settings.CLONE_TIMEOUT_SECONDS}s timeout...")

        try:
            # Execute with hard enforced timeout and process termination
            process = subprocess.run(
                clone_cmd,
                env=env,
                timeout=settings.CLONE_TIMEOUT_SECONDS,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
        except subprocess.TimeoutExpired:
            logger.warning(f"Clone timed out after {settings.CLONE_TIMEOUT_SECONDS}s for {normalized_url}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Repository clone timed out after {settings.CLONE_TIMEOUT_SECONDS} seconds.",
            )
        except Exception as exc:
            logger.error(f"Unexpected error running git clone: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initiate repository clone operation.",
            )

        if process.returncode != 0:
            stderr_msg = process.stderr.strip() if process.stderr else ""
            logger.warning(f"Git clone failed (exit code {process.returncode}): {stderr_msg}")

            if "Authentication failed" in stderr_msg or "could not read Username" in stderr_msg:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Repository not found or requires authentication. Only public repositories are supported.",
                )
            if "Repository not found" in stderr_msg or "not found" in stderr_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Repository could not be found on GitHub. Verify the owner and repository name.",
                )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to clone repository from GitHub: {stderr_msg or 'Remote repository inaccessible'}",
            )

        # Check repository size on disk
        total_size_bytes = cls.get_directory_size_bytes(target_dir)
        max_bytes = settings.MAX_REPO_SIZE_MB * 1024 * 1024
        if total_size_bytes > max_bytes:
            logger.warning(f"Repository {normalized_url} exceeded size limit: {total_size_bytes} > {max_bytes}")
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Repository size ({total_size_bytes // (1024 * 1024)} MB) exceeds the allowed limit of {settings.MAX_REPO_SIZE_MB} MB.",
            )

        try:
            repo = git.Repo(target_dir)
            return repo
        except Exception as exc:
            logger.error(f"GitPython failed to open cloned repository: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to load cloned Git repository.",
            )

    @staticmethod
    def get_directory_size_bytes(directory: str) -> int:
        """Calculate total directory size in bytes."""
        total = 0
        try:
            for entry in os.scandir(directory):
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat().st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += GitHubService.get_directory_size_bytes(entry.path)
        except Exception:
            pass
        return total
