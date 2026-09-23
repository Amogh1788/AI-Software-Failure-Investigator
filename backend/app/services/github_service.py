import os
import re
import shutil
import stat
import subprocess
import logging
import tempfile
from typing import Tuple, Dict, Set, Optional
from urllib.parse import urlparse
from fastapi import HTTPException, status
import git
from app.core.config import settings

logger = logging.getLogger("ai_investigator.github_service")

# Extensions of obvious non-source binary artifacts that should not count toward analyzable working tree budget
BINARY_ARTIFACT_EXTENSIONS: Set[str] = {
    ".exe", ".dll", ".so", ".dylib", ".bin", ".iso", ".img",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".jar", ".war", ".ear", ".class", ".pyc", ".pyo", ".wasm",
    ".db", ".sqlite", ".sqlite3",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
    ".parquet", ".h5", ".onnx", ".pt", ".pkl",
}

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

    @staticmethod
    def _onerror_remove_readonly(func, path, exc_info):
        """Handle read-only files on Windows during directory deletion."""
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass

    @classmethod
    def _cleanup_dir(cls, directory: str) -> None:
        """Safely delete target temporary directory, ensuring system tempdir root is never deleted."""
        if not directory or not os.path.exists(directory):
            return
        system_temp = os.path.realpath(tempfile.gettempdir())
        real_target = os.path.realpath(directory)
        if real_target == system_temp:
            return
        try:
            shutil.rmtree(directory, onerror=cls._onerror_remove_readonly)
        except Exception as exc:
            logger.warning(f"Failed to clean up repository directory {directory}: {exc}")

    @classmethod
    def is_analyzable_file(cls, filename: str, file_size_bytes: int) -> bool:
        """
        Determine if a file in the working tree is analyzable.
        - Source and configuration files within analysis limits are analyzable.
        - Obvious non-source binary artifacts are excluded from the analyzable working tree budget.
        - Genuinely oversized files (> MAX_ANALYZABLE_FILE_MB) are skipped from the budget to avoid
          counting non-source blobs or massive data dumps toward the source code budget.
        """
        _, ext = os.path.splitext(filename)
        ext = ext.lower()
        if ext in BINARY_ARTIFACT_EXTENSIONS:
            return False
        max_file_bytes = settings.MAX_ANALYZABLE_FILE_MB * 1024 * 1024
        if file_size_bytes > max_file_bytes:
            return False
        return True

    @classmethod
    def get_directory_size_bytes(
        cls,
        directory: str,
        exclude_dirs: Optional[Set[str]] = None,
    ) -> int:
        """
        Calculate total analyzable working-tree directory size in bytes.
        - .git is never counted.
        - configured excluded directories (dist, build, target, node_modules, .gradle) are never counted.
        - obvious non-source binary artifacts and oversized files are excluded per safety policy.
        - only the analyzable working tree contributes to MAX_REPO_SIZE_MB.
        """
        if exclude_dirs is None:
            exclude_dirs = {".git"}.union(settings.EXCLUDED_REPO_PATHS)

        total = 0
        try:
            for entry in os.scandir(directory):
                if entry.name in exclude_dirs:
                    continue
                if entry.is_file(follow_symlinks=False):
                    try:
                        size = entry.stat().st_size
                        if cls.is_analyzable_file(entry.name, size):
                            total += size
                    except OSError:
                        pass
                elif entry.is_dir(follow_symlinks=False):
                    total += cls.get_directory_size_bytes(entry.path, exclude_dirs=exclude_dirs)
        except Exception:
            pass
        return total

    @classmethod
    def clone_repository_safely(cls, normalized_url: str, target_dir: str) -> git.Repo:
        """
        Clone a repository into a designated temporary directory with an enforced hard timeout.
        Uses Git partial clone (--filter=blob:none, --no-checkout, --depth=MAX_COMMITS_TO_ANALYZE)
        and non-cone sparse checkout to prevent generated/build/package artifacts from materializing.
        Calculates analyzable working-tree size and enforces MAX_REPO_SIZE_MB budget.
        Guarantees cleanup of target directory on any failure or size rejection.
        """
        cls.verify_git_installation()

        env = os.environ.copy()
        # Prevent git from interactively prompting for username/password or opening credential GUI
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GIT_ASKPASS"] = ""

        # 1. Partial clone command
        clone_cmd = [
            "git",
            "clone",
            "--depth",
            str(settings.MAX_COMMITS_TO_ANALYZE),
            "--filter=blob:none",
            "--no-checkout",
            "--single-branch",
            "--quiet",
            normalized_url,
            target_dir,
        ]

        logger.info(
            f"Cloning {normalized_url} (depth={settings.MAX_COMMITS_TO_ANALYZE}, "
            f"partial_clone=True, filter=blob:none, excluded_paths={settings.EXCLUDED_REPO_PATHS}) "
            f"into temporary directory with {settings.CLONE_TIMEOUT_SECONDS}s timeout..."
        )

        try:
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
            cls._cleanup_dir(target_dir)
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Repository clone timed out after {settings.CLONE_TIMEOUT_SECONDS} seconds.",
            )
        except HTTPException:
            cls._cleanup_dir(target_dir)
            raise
        except Exception as exc:
            logger.error(f"Unexpected error running git clone: {exc}")
            cls._cleanup_dir(target_dir)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initiate repository clone operation.",
            )

        if process.returncode != 0:
            stderr_msg = process.stderr.strip() if process.stderr else ""
            logger.warning(f"Git clone failed (exit code {process.returncode}): {stderr_msg}")
            cls._cleanup_dir(target_dir)

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

        # 2. Configure sparse checkout in non-cone mode
        patterns = ["/*"]
        for name in settings.EXCLUDED_REPO_PATHS:
            clean = name.strip().strip("/")
            if not clean:
                continue
            patterns.extend([
                f"!{clean}/",
                f"!{clean}/**",
                f"!**/{clean}/",
                f"!**/{clean}/**",
            ])

        sparse_cmd = [
            "git",
            "sparse-checkout",
            "set",
            "--no-cone",
            *patterns,
        ]

        try:
            sparse_proc = subprocess.run(
                sparse_cmd,
                cwd=target_dir,
                env=env,
                timeout=settings.CLONE_TIMEOUT_SECONDS,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if sparse_proc.returncode != 0:
                err = sparse_proc.stderr.strip() if sparse_proc.stderr else ""
                logger.warning(f"Git sparse-checkout set failed (exit code {sparse_proc.returncode}): {err}")
                cls._cleanup_dir(target_dir)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to configure repository sparse checkout: {err or 'Unknown error'}",
                )
        except subprocess.TimeoutExpired:
            logger.warning(f"Sparse checkout configuration timed out for {normalized_url}")
            cls._cleanup_dir(target_dir)
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Repository sparse checkout timed out after {settings.CLONE_TIMEOUT_SECONDS} seconds.",
            )
        except HTTPException:
            cls._cleanup_dir(target_dir)
            raise
        except Exception as exc:
            logger.error(f"Unexpected error configuring sparse checkout: {exc}")
            cls._cleanup_dir(target_dir)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to configure repository sparse checkout.",
            )

        # 3. Materialize working tree via git checkout
        checkout_cmd = [
            "git",
            "checkout",
            "--quiet",
        ]

        try:
            checkout_proc = subprocess.run(
                checkout_cmd,
                cwd=target_dir,
                env=env,
                timeout=settings.CLONE_TIMEOUT_SECONDS,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if checkout_proc.returncode != 0:
                err = checkout_proc.stderr.strip() if checkout_proc.stderr else ""
                logger.warning(f"Git checkout failed (exit code {checkout_proc.returncode}): {err}")
                cls._cleanup_dir(target_dir)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to check out repository working tree: {err or 'Unknown error'}",
                )
        except subprocess.TimeoutExpired:
            logger.warning(f"Checkout timed out for {normalized_url}")
            cls._cleanup_dir(target_dir)
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Repository checkout timed out after {settings.CLONE_TIMEOUT_SECONDS} seconds.",
            )
        except HTTPException:
            cls._cleanup_dir(target_dir)
            raise
        except Exception as exc:
            logger.error(f"Unexpected error during git checkout: {exc}")
            cls._cleanup_dir(target_dir)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to materialize repository working tree.",
            )

        # 4. Calculate analyzable working-tree size and enforce limit
        total_size_bytes = cls.get_directory_size_bytes(target_dir)
        max_bytes = settings.MAX_REPO_SIZE_MB * 1024 * 1024
        if total_size_bytes > max_bytes:
            logger.warning(
                f"Repository {normalized_url} exceeded size limit: analyzable working-tree size "
                f"{total_size_bytes / (1024 * 1024):.2f} MB ({total_size_bytes} bytes) > "
                f"allowed limit {settings.MAX_REPO_SIZE_MB} MB ({max_bytes} bytes). "
                f"Excluded paths: {settings.EXCLUDED_REPO_PATHS}"
            )
            cls._cleanup_dir(target_dir)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Repository size ({total_size_bytes // (1024 * 1024)} MB) exceeds the allowed limit of {settings.MAX_REPO_SIZE_MB} MB.",
            )

        logger.info(
            f"Repository {normalized_url} successfully cloned and checked out. "
            f"Analyzable working-tree size: {total_size_bytes / (1024 * 1024):.2f} MB ({total_size_bytes} bytes), "
            f"configured maximum: {settings.MAX_REPO_SIZE_MB} MB ({max_bytes} bytes), "
            f"shallow depth: {settings.MAX_COMMITS_TO_ANALYZE}, "
            f"partial clone enabled: True (blob:none), "
            f"excluded/generated paths: {settings.EXCLUDED_REPO_PATHS}"
        )

        # 5. Open and return GitPython Repo
        try:
            repo = git.Repo(target_dir)
            return repo
        except Exception as exc:
            logger.error(f"GitPython failed to open cloned repository: {exc}")
            cls._cleanup_dir(target_dir)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to load cloned Git repository.",
            )
