import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from app.services.github_service import GitHubService
from app.services.repository_analyzer import RepositoryAnalyzer
from app.services.git_history_analyzer import GitHistoryAnalyzer
from app.models.repository import RepositoryResponse, RepositoryDetailResponse

client = TestClient(app)


# 1. URL Validation Tests
def test_valid_github_url_parsing():
    """Verify parsing and normalization of standard GitHub HTTPS URLs."""
    url = "https://github.com/torvalds/linux"
    norm, owner, repo = GitHubService.validate_and_parse_url(url)
    assert norm == "https://github.com/torvalds/linux"
    assert owner == "torvalds"
    assert repo == "linux"


def test_valid_github_url_with_git_suffix():
    """Verify parsing with .git suffix and trailing slash."""
    url = "https://github.com/facebook/react.git/"
    norm, owner, repo = GitHubService.validate_and_parse_url(url)
    assert norm == "https://github.com/facebook/react"
    assert owner == "facebook"
    assert repo == "react"


def test_malformed_github_url():
    """Verify rejection of malformed GitHub URLs."""
    with pytest.raises(HTTPException) as exc:
        GitHubService.validate_and_parse_url("https://github.com/onlyonepart")
    assert exc.value.status_code == 400


def test_unsupported_ssh_url():
    """Verify rejection of SSH Git URLs."""
    with pytest.raises(HTTPException) as exc:
        GitHubService.validate_and_parse_url("git@github.com:torvalds/linux.git")
    assert exc.value.status_code == 400
    assert "SSH URLs are not supported" in exc.value.detail


def test_unsupported_host_url():
    """Verify rejection of non-GitHub repository hosts."""
    with pytest.raises(HTTPException) as exc:
        GitHubService.validate_and_parse_url("https://gitlab.com/gitlab-org/gitlab")
    assert exc.value.status_code == 400
    assert "Unsupported host" in exc.value.detail


# 2. Static File & Language Detection Tests
def test_repository_analyzer_file_and_language_detection():
    """Verify file classification, LOC counting, and language detection without running code."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create a Python file
        py_file = os.path.join(tmp_dir, "app.py")
        with open(py_file, "w", encoding="utf-8") as f:
            f.write("def main():\n    print('Hello World')\n\nif __name__ == '__main__':\n    main()\n")

        # Create a TypeScript file
        ts_dir = os.path.join(tmp_dir, "src")
        os.makedirs(ts_dir, exist_ok=True)
        ts_file = os.path.join(ts_dir, "index.ts")
        with open(ts_file, "w", encoding="utf-8") as f:
            f.write("export const add = (a: number, b: number) => a + b;\n")

        # Create an ignored directory and file
        ignored_dir = os.path.join(tmp_dir, "node_modules", "pkg")
        os.makedirs(ignored_dir, exist_ok=True)
        with open(os.path.join(ignored_dir, "bundle.js"), "w", encoding="utf-8") as f:
            f.write("console.log('ignored');\n")

        # Run static analyzer
        results = RepositoryAnalyzer.analyze(tmp_dir)

        assert results["total_files"] == 2  # node_modules skipped!
        assert results["source_files"] == 2
        assert results["primary_language"] in ("Python", "TypeScript")

        paths = [f["path"] for f in results["files"]]
        assert "app.py" in paths
        assert "src/index.ts" in paths

        py_entry = next(f for f in results["files"] if f["path"] == "app.py")
        assert py_entry["language"] == "Python"
        assert py_entry["is_source_file"] is True
        assert py_entry["lines_of_code"] == 5


# 3. Git Commit History Parsing Tests
def test_git_commit_parsing_mocked():
    """Verify extraction of commit metadata using a mock Git repo."""
    mock_commit = MagicMock()
    mock_commit.hexsha = "abc1234567890abcdef1234567890abcdef12345"
    mock_commit.author.name = "Test Committer"
    mock_commit.author.email = "committer@example.com"
    mock_commit.message = "Fix memory leak in worker pool\n\nDetailed message."
    mock_commit.committed_datetime.isoformat.return_value = "2026-09-18T12:00:00+00:00"
    mock_commit.stats.files = {"worker.py": {}, "test_worker.py": {}}

    mock_repo = MagicMock()
    mock_repo.iter_commits.return_value = [mock_commit]
    mock_repo.active_branch.name = "main"

    commits = GitHistoryAnalyzer.extract_recent_commits(mock_repo, max_count=50)
    assert len(commits) == 1
    assert commits[0]["commit_hash"] == "abc1234567890abcdef1234567890abcdef12345"
    assert commits[0]["author_name"] == "Test Committer"
    assert commits[0]["commit_message"] == "Fix memory leak in worker pool\n\nDetailed message."
    assert commits[0]["files_changed"] == 2

    default_branch = GitHistoryAnalyzer.get_default_branch(mock_repo)
    assert default_branch == "main"


# 4. API Endpoints & Error Handling Tests (Mocked)
def test_analyze_endpoint_invalid_url():
    """Verify POST /api/repositories/analyze returns HTTP 400 for invalid URLs."""
    response = client.post("/api/repositories/analyze", json={"github_url": "invalid-url"})
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


def test_analyze_endpoint_success_mocked():
    """Verify POST /api/repositories/analyze serialization on successful mock run."""
    mock_detail = RepositoryDetailResponse(
        repository=RepositoryResponse(
            id="12345678-1234-5678-1234-567812345678",
            project_id=None,
            github_url="https://github.com/mockuser/mockrepo",
            owner="mockuser",
            name="mockrepo",
            default_branch="main",
            description="Mock repo",
            primary_language="Python",
            total_files=5,
            source_files=4,
            analyzed_at="2026-09-19T00:00:00Z",
            created_at="2026-09-19T00:00:00Z",
        ),
        files=[],
        commits=[],
        language_breakdown={"Python": 4, "Markdown": 1},
    )

    with patch("app.services.repository_service.RepositoryService.analyze_repository", return_value=mock_detail):
        response = client.post(
            "/api/repositories/analyze",
            json={"github_url": "https://github.com/mockuser/mockrepo"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["repository"]["name"] == "mockrepo"
        assert data["repository"]["primary_language"] == "Python"


def test_list_repositories_endpoint_mocked():
    """Verify GET /api/repositories returns list of repository summaries."""
    mock_repos = [
        RepositoryResponse(
            id="12345678-1234-5678-1234-567812345678",
            project_id=None,
            github_url="https://github.com/mockuser/mockrepo",
            owner="mockuser",
            name="mockrepo",
            default_branch="main",
            description="Mock repo",
            primary_language="Python",
            total_files=10,
            source_files=8,
            analyzed_at="2026-09-19T00:00:00Z",
            created_at="2026-09-19T00:00:00Z",
        )
    ]

    with patch("app.services.repository_service.RepositoryService.list_repositories", return_value=mock_repos):
        response = client.get("/api/repositories")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["owner"] == "mockuser"


def test_size_limit_rejection_mocked():
    """Verify repository size exceeding threshold raises HTTP 413."""
    with patch("app.services.github_service.GitHubService.get_directory_size_bytes", return_value=500 * 1024 * 1024):
        with patch("subprocess.run") as mock_sub:
            mock_sub.return_value = MagicMock(returncode=0)
            with pytest.raises(HTTPException) as exc:
                GitHubService.clone_repository_safely("https://github.com/user/huge-repo", tempfile.gettempdir())
            assert exc.value.status_code == 413
            assert "exceeds the allowed limit" in exc.value.detail
