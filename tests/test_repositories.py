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

import subprocess
import shutil
import git
from app.main import app
from app.core.config import settings
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


# 5. Partial Clone, Sparse Checkout & Size-Handling Tests (A - K)

def _create_test_git_repo(files: dict, commit_msg: str = "Initial commit") -> str:
    """Helper to initialize a real Git repository with given files in a temp directory."""
    repo_dir = tempfile.mkdtemp(prefix="test_git_src_")
    try:
        subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test Committer"], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True, capture_output=True)
        for rel_path, content in files.items():
            full_p = os.path.join(repo_dir, rel_path.replace("/", os.sep))
            os.makedirs(os.path.dirname(full_p), exist_ok=True)
            if isinstance(content, str):
                with open(full_p, "w", encoding="utf-8") as f:
                    f.write(content)
            else:
                with open(full_p, "wb") as f:
                    f.write(content)
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=repo_dir, check=True, capture_output=True)
        return repo_dir
    except Exception:
        shutil.rmtree(repo_dir, ignore_errors=True)
        raise


def _safe_cleanup(path: str):
    """Safely remove a repository directory releasing any Windows locks."""
    if path and os.path.exists(path):
        try:
            shutil.rmtree(path, onerror=GitHubService._onerror_remove_readonly)
        except Exception:
            pass


def test_a_normal_repository_within_budget_succeeds():
    """Requirement 10.A: Standard repository within budget succeeds and materializes source."""
    src_dir = _create_test_git_repo({
        "src/main.py": "def main():\n    print('Hello RepoDetective')\n",
        "README.md": "# Sample Project\n",
    })
    dest_dir = tempfile.mkdtemp(prefix="test_dest_")
    repo = None
    try:
        file_url = "file:///" + os.path.abspath(src_dir).replace("\\", "/")
        repo = GitHubService.clone_repository_safely(file_url, dest_dir)
        assert isinstance(repo, git.Repo)
        assert os.path.exists(os.path.join(dest_dir, "src", "main.py"))
        assert os.path.exists(os.path.join(dest_dir, "README.md"))
        size = GitHubService.get_directory_size_bytes(dest_dir)
        assert size > 0
        assert size < settings.MAX_REPO_SIZE_MB * 1024 * 1024
    finally:
        if repo:
            repo.close()
        _safe_cleanup(src_dir)
        _safe_cleanup(dest_dir)


def test_b_large_tracked_dist_artifact_succeeds():
    """Requirement 10.B: Tracked dist/ artifact is not materialized and repo succeeds."""
    src_dir = _create_test_git_repo({
        "src/app.py": "def run():\n    return 42\n",
        "dist/large_build.exe": b"\x00" * (2 * 1024 * 1024),  # 2 MB binary artifact
    })
    dest_dir = tempfile.mkdtemp(prefix="test_dest_")
    repo = None
    try:
        file_url = "file:///" + os.path.abspath(src_dir).replace("\\", "/")
        repo = GitHubService.clone_repository_safely(file_url, dest_dir)
        assert isinstance(repo, git.Repo)
        # Source must exist, but dist must NOT be materialized in working tree
        assert os.path.exists(os.path.join(dest_dir, "src", "app.py"))
        assert not os.path.exists(os.path.join(dest_dir, "dist"))
        # Dist does not contribute to analyzable size
        size = GitHubService.get_directory_size_bytes(dest_dir)
        assert size < 1024 * 1024  # Well under 1 MB
    finally:
        if repo:
            repo.close()
        _safe_cleanup(src_dir)
        _safe_cleanup(dest_dir)


def test_c_nested_generated_directories_not_materialized():
    """Requirement 10.C: Nested generated directories (node_modules, build, target, .gradle) are not materialized."""
    src_dir = _create_test_git_repo({
        "packages/app/node_modules/pkg/index.js": "module.exports = {};\n",
        "client/build/static/bundle.js": "console.log('build');\n",
        "foo/bar/target/classes/Main.class": b"\xca\xfe\xba\xbe",
        "android/.gradle/caches/cache.bin": b"\x01\x02\x03\x04",
        "src/core/engine.py": "class Engine:\n    pass\n",
    })
    dest_dir = tempfile.mkdtemp(prefix="test_dest_")
    repo = None
    try:
        file_url = "file:///" + os.path.abspath(src_dir).replace("\\", "/")
        repo = GitHubService.clone_repository_safely(file_url, dest_dir)
        assert isinstance(repo, git.Repo)
        # Analyzable source must exist
        assert os.path.exists(os.path.join(dest_dir, "src", "core", "engine.py"))
        # Excluded nested directories must NOT exist on disk
        assert not os.path.exists(os.path.join(dest_dir, "packages", "app", "node_modules"))
        assert not os.path.exists(os.path.join(dest_dir, "client", "build"))
        assert not os.path.exists(os.path.join(dest_dir, "foo", "bar", "target"))
        assert not os.path.exists(os.path.join(dest_dir, "android", ".gradle"))
    finally:
        if repo:
            repo.close()
        _safe_cleanup(src_dir)
        _safe_cleanup(dest_dir)


def test_d_source_tree_genuinely_exceeding_budget_raises_413():
    """Requirement 10.D: Source tree genuinely exceeding MAX_REPO_SIZE_MB raises HTTP 413 and cleans up."""
    dest_dir = tempfile.mkdtemp(prefix="test_dest_")
    with patch("app.services.github_service.GitHubService.get_directory_size_bytes", return_value=120 * 1024 * 1024):
        with patch("subprocess.run") as mock_sub:
            mock_sub.return_value = MagicMock(returncode=0)
            with pytest.raises(HTTPException) as exc:
                GitHubService.clone_repository_safely("https://github.com/org/oversized-repo", dest_dir)
            assert exc.value.status_code == 413
            assert "exceeds the allowed limit" in exc.value.detail
            # Must clean up destination directory on 413
            assert not os.path.exists(dest_dir)


def test_e_large_non_excluded_binary_handled_by_per_file_safety_policy():
    """Requirement 10.E: Obvious non-source binary artifacts outside excluded dirs are skipped by policy."""
    # 1. Direct classification assertions
    assert GitHubService.is_analyzable_file("installer.exe", 25 * 1024 * 1024) is False
    assert GitHubService.is_analyzable_file("model.bin", 50 * 1024 * 1024) is False
    assert GitHubService.is_analyzable_file("data.parquet", 20 * 1024 * 1024) is False
    assert GitHubService.is_analyzable_file("app.py", 500 * 1024) is True
    assert GitHubService.is_analyzable_file("config.json", 100 * 1024) is True
    # Oversized file exceeding MAX_ANALYZABLE_FILE_MB (10 MB)
    assert GitHubService.is_analyzable_file("huge_dump.unknown", 15 * 1024 * 1024) is False

    # 2. Integration: Repo with large binary artifact alongside source code
    src_dir = _create_test_git_repo({
        "src/app.py": "def process():\n    return True\n",
        "archive.zip": b"PK\x03\x04" + (b"\x00" * (500 * 1024)),
    })
    dest_dir = tempfile.mkdtemp(prefix="test_dest_")
    repo = None
    try:
        file_url = "file:///" + os.path.abspath(src_dir).replace("\\", "/")
        repo = GitHubService.clone_repository_safely(file_url, dest_dir)
        assert isinstance(repo, git.Repo)
        # get_directory_size_bytes excludes archive.zip because it is a binary artifact
        analyzable_size = GitHubService.get_directory_size_bytes(dest_dir)
        # Only src/app.py contributes (< 1000 bytes)
        assert analyzable_size < 1000
    finally:
        if repo:
            repo.close()
        _safe_cleanup(src_dir)
        _safe_cleanup(dest_dir)


def test_f_gitpython_repository_opening_works():
    """Requirement 10.F: GitPython repository inspection works seamlessly with partial clone."""
    src_dir = _create_test_git_repo({
        "src/service.py": "class Service:\n    pass\n",
        "README.md": "# Test Repo\n",
    })
    dest_dir = tempfile.mkdtemp(prefix="test_dest_")
    repo = None
    try:
        file_url = "file:///" + os.path.abspath(src_dir).replace("\\", "/")
        repo = GitHubService.clone_repository_safely(file_url, dest_dir)
        assert repo.active_branch.name == "main"
        assert len(repo.heads) > 0
        analysis = RepositoryAnalyzer.analyze(dest_dir)
        assert analysis["total_files"] == 2
        assert analysis["source_files"] == 1
        assert analysis["primary_language"] == "Python"
    finally:
        if repo:
            repo.close()
        _safe_cleanup(src_dir)
        _safe_cleanup(dest_dir)


def test_g_commit_history_works():
    """Requirement 10.G: Commit history inspection extracts all commit metadata correctly."""
    src_dir = _create_test_git_repo({
        "src/app.py": "x = 1\n",
    }, commit_msg="First commit")

    # Add second commit
    with open(os.path.join(src_dir, "src", "app.py"), "w", encoding="utf-8") as f:
        f.write("x = 2\n")
    subprocess.run(["git", "add", "."], cwd=src_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Second commit: update x"], cwd=src_dir, check=True, capture_output=True)

    dest_dir = tempfile.mkdtemp(prefix="test_dest_")
    repo = None
    try:
        file_url = "file:///" + os.path.abspath(src_dir).replace("\\", "/")
        repo = GitHubService.clone_repository_safely(file_url, dest_dir)
        commits = GitHistoryAnalyzer.extract_recent_commits(repo)
        assert len(commits) == 2
        messages = [c["commit_message"] for c in commits]
        assert "Second commit: update x" in messages
        assert "First commit" in messages
    finally:
        if repo:
            repo.close()
        _safe_cleanup(src_dir)
        _safe_cleanup(dest_dir)


def test_h_diff_and_stat_analysis_works():
    """Requirement 10.H: Commit diff and stats extraction works on partial-clone repository."""
    src_dir = _create_test_git_repo({
        "src/module.py": "def foo(): pass\n",
    }, commit_msg="Initial feature")

    with open(os.path.join(src_dir, "src", "module.py"), "w", encoding="utf-8") as f:
        f.write("def foo():\n    return 'bar'\n")
    subprocess.run(["git", "add", "."], cwd=src_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Modify module.py return value"], cwd=src_dir, check=True, capture_output=True)

    dest_dir = tempfile.mkdtemp(prefix="test_dest_")
    repo = None
    try:
        file_url = "file:///" + os.path.abspath(src_dir).replace("\\", "/")
        repo = GitHubService.clone_repository_safely(file_url, dest_dir)
        head_commit = repo.head.commit
        # Verify stats
        assert "src/module.py" in head_commit.stats.files
        # Verify diff
        parent = head_commit.parents[0]
        diffs = parent.diff(head_commit, create_patch=True)
        assert len(diffs) == 1
        assert diffs[0].b_path == "src/module.py"
    finally:
        if repo:
            repo.close()
        _safe_cleanup(src_dir)
        _safe_cleanup(dest_dir)


def test_clone_timeout_setting_is_300_seconds():
    """Verify backend CLONE_TIMEOUT_SECONDS is configured to 300s for large repositories."""
    assert settings.CLONE_TIMEOUT_SECONDS == 300


def test_i_clone_timeout_returns_504_and_cleans_up():
    """Requirement 10.I: Clone timeout returns HTTP 504 and cleans up directory."""
    dest_dir = tempfile.mkdtemp(prefix="test_dest_timeout_")
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git clone", timeout=settings.CLONE_TIMEOUT_SECONDS)):
        with pytest.raises(HTTPException) as exc:
            GitHubService.clone_repository_safely("https://github.com/org/timeout-repo", dest_dir)
        assert exc.value.status_code == 504
        assert "timed out after 300 seconds" in exc.value.detail
        assert not os.path.exists(dest_dir)


def test_j_clone_and_sparse_failure_cleans_up():
    """Requirement 10.J: Clone or sparse-checkout failure cleans up temporary directory."""
    # 1. Clone exit code != 0
    dest_dir_clone = tempfile.mkdtemp(prefix="test_dest_fail1_")
    with patch("subprocess.run", return_value=MagicMock(returncode=128, stderr="fatal: remote error")):
        with pytest.raises(HTTPException) as exc:
            GitHubService.clone_repository_safely("https://github.com/org/fail-repo", dest_dir_clone)
        assert exc.value.status_code == 400
        assert not os.path.exists(dest_dir_clone)

    # 2. Sparse checkout exit code != 0
    dest_dir_sparse = tempfile.mkdtemp(prefix="test_dest_fail2_")
    call_count = 0

    def mock_sub(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return MagicMock(returncode=0)  # clone succeeds
        return MagicMock(returncode=1, stderr="fatal: unable to set sparse patterns")  # sparse fails

    with patch("subprocess.run", side_effect=mock_sub):
        with pytest.raises(HTTPException) as exc:
            GitHubService.clone_repository_safely("https://github.com/org/fail-repo", dest_dir_sparse)
        assert exc.value.status_code == 500
        assert not os.path.exists(dest_dir_sparse)


def test_k_tictactoe_arena_regression():
    """
    Requirement 11: Regression test representing TicTacToeArena.
    Contains:
    - dist/ with large Windows executable (~5 MB simulated tracked artifact)
    - target/ with Maven build outputs
    - normal Java source tree and pom.xml
    Repository must NOT be rejected and source files must be properly analyzed.
    """
    src_dir = _create_test_git_repo({
        "src/main/java/com/arena/TicTacToe.java": (
            "package com.arena;\n\n"
            "public class TicTacToe {\n"
            "    private Board board;\n"
            "    public TicTacToe() {\n"
            "        this.board = new Board();\n"
            "    }\n"
            "    public boolean makeMove(int row, int col, char player) {\n"
            "        return board.place(row, col, player);\n"
            "    }\n"
            "}\n"
        ),
        "src/main/java/com/arena/Board.java": (
            "package com.arena;\n\n"
            "public class Board {\n"
            "    private char[][] grid = new char[3][3];\n"
            "    public boolean place(int r, int c, char p) {\n"
            "        grid[r][c] = p;\n"
            "        return true;\n"
            "    }\n"
            "}\n"
        ),
        "pom.xml": (
            "<project>\n"
            "    <modelVersion>4.0.0</modelVersion>\n"
            "    <groupId>com.arena</groupId>\n"
            "    <artifactId>tictactoe-arena</artifactId>\n"
            "    <version>1.0.0</version>\n"
            "</project>\n"
        ),
        # Large tracked distribution executable in dist/
        "dist/TicTacToeArena-win64.exe": b"\x4d\x5a" + (b"\x90" * (5 * 1024 * 1024)),
        # Build artifacts in target/
        "target/classes/com/arena/TicTacToe.class": b"\xca\xfe\xba\xbe\x00\x00",
    }, commit_msg="feat: Add TicTacToe game logic and release binary")

    dest_dir = tempfile.mkdtemp(prefix="test_tictactoe_")
    repo = None
    try:
        file_url = "file:///" + os.path.abspath(src_dir).replace("\\", "/")
        # 1. Clone must succeed without throwing HTTP 413
        repo = GitHubService.clone_repository_safely(file_url, dest_dir)
        assert isinstance(repo, git.Repo)

        # 2. Excluded directories must NOT be materialized in the working tree
        assert not os.path.exists(os.path.join(dest_dir, "dist"))
        assert not os.path.exists(os.path.join(dest_dir, "target"))

        # 3. Source files must exist
        assert os.path.exists(os.path.join(dest_dir, "src", "main", "java", "com", "arena", "TicTacToe.java"))
        assert os.path.exists(os.path.join(dest_dir, "src", "main", "java", "com", "arena", "Board.java"))
        assert os.path.exists(os.path.join(dest_dir, "pom.xml"))

        # 4. Analyzable working tree size must be very small (source only)
        analyzable_size = GitHubService.get_directory_size_bytes(dest_dir)
        assert analyzable_size < 100 * 1024  # Under 100 KB
        assert analyzable_size < settings.MAX_REPO_SIZE_MB * 1024 * 1024

        # 5. RepositoryAnalyzer correctly detects Java and ignores dist/
        analysis = RepositoryAnalyzer.analyze(dest_dir)
        assert analysis["primary_language"] == "Java"
        assert analysis["source_files"] == 2
        file_paths = [f["path"] for f in analysis["files"]]
        assert "src/main/java/com/arena/TicTacToe.java" in file_paths
        assert "src/main/java/com/arena/Board.java" in file_paths
        assert not any("dist" in p for p in file_paths)
        assert not any("target" in p for p in file_paths)

        # 6. Git commit metadata is intact
        commits = GitHistoryAnalyzer.extract_recent_commits(repo)
        assert len(commits) == 1
        assert "TicTacToe" in commits[0]["commit_message"]
    finally:
        if repo:
            repo.close()
        _safe_cleanup(src_dir)
        _safe_cleanup(dest_dir)

