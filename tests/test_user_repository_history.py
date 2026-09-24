import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from app.core.auth import get_current_user, AuthenticatedUser
from app.services.repository_service import RepositoryService
from app.models.repository import RepositoryResponse

client = TestClient(app)

USER_A = AuthenticatedUser(
    id="user-a-1111-1111-1111-111111111111",
    email="user_a@example.com",
    role="authenticated",
)

USER_B = AuthenticatedUser(
    id="user-b-2222-2222-2222-222222222222",
    email="user_b@example.com",
    role="authenticated",
)


class MockResult:
    def __init__(self, data):
        self.data = data


class MockTableQuery:
    def __init__(self, db, table_name):
        self.db = db
        self.table_name = table_name
        self.filters = []
        self.order_field = None
        self.order_desc = False
        self.action = "select"
        self.insert_data = None
        self.update_data = None

    def select(self, *args, **kwargs):
        self.action = "select"
        return self

    def insert(self, data, *args, **kwargs):
        self.action = "insert"
        self.insert_data = data
        return self

    def update(self, data, *args, **kwargs):
        self.action = "update"
        self.update_data = data
        return self

    def upsert(self, data, on_conflict=None, *args, **kwargs):
        self.action = "upsert"
        self.insert_data = data
        self.on_conflict = on_conflict
        return self

    def delete(self, *args, **kwargs):
        self.action = "delete"
        return self

    def eq(self, field, value):
        self.filters.append((field, "eq", value))
        return self

    def in_(self, field, values):
        self.filters.append((field, "in", values))
        return self

    def order(self, field, desc=False):
        self.order_field = field
        self.order_desc = desc
        return self

    def limit(self, count):
        return self

    def _matches(self, row):
        for field, op, val in self.filters:
            if op == "eq" and str(row.get(field)) != str(val):
                return False
            if op == "in" and row.get(field) not in val:
                return False
        return True

    def execute(self):
        rows = self.db.tables[self.table_name]

        if self.action == "select":
            matched = [dict(r) for r in rows if self._matches(r)]
            if self.order_field:
                matched.sort(
                    key=lambda r: r.get(self.order_field, ""),
                    reverse=self.order_desc,
                )
            return MockResult(matched)

        elif self.action == "insert":
            inserted = []
            payload = self.insert_data if isinstance(self.insert_data, list) else [self.insert_data]
            for item in payload:
                item_copy = dict(item)
                if "id" not in item_copy:
                    item_copy["id"] = str(uuid.uuid4())
                if "created_at" not in item_copy:
                    item_copy["created_at"] = datetime.now(timezone.utc).isoformat()
                rows.append(item_copy)
                inserted.append(item_copy)
            return MockResult(inserted)

        elif self.action == "update":
            updated = []
            for r in rows:
                if self._matches(r):
                    r.update(self.update_data)
                    updated.append(dict(r))
            return MockResult(updated)

        elif self.action == "upsert":
            item = dict(self.insert_data)
            existing = None
            if self.table_name == "user_repository_history":
                for r in rows:
                    if r.get("user_id") == item.get("user_id") and r.get("repository_id") == item.get("repository_id"):
                        existing = r
                        break
            if existing:
                existing.update(item)
                return MockResult([existing])
            else:
                if "id" not in item:
                    item["id"] = str(uuid.uuid4())
                rows.append(item)
                return MockResult([item])

        elif self.action == "delete":
            deleted = []
            retained = []
            for r in rows:
                if self._matches(r):
                    deleted.append(r)
                else:
                    retained.append(r)
            self.db.tables[self.table_name] = retained
            return MockResult(deleted)

        return MockResult([])


class MockDatabase:
    def __init__(self):
        self.tables = {
            "repositories": [],
            "user_repository_history": [],
            "repository_files": [],
            "repository_commits": [],
        }

    def table(self, name: str):
        return MockTableQuery(self, name)


@pytest.fixture
def mock_db():
    db = MockDatabase()
    with patch("app.services.repository_service.get_supabase_client", return_value=db):
        yield db


@pytest.fixture
def mock_git_pipeline():
    """Mock the clone and static analysis pipeline so we test persistence and isolation."""
    with patch("app.services.github_service.GitHubService.clone_repository_safely") as mock_clone, \
         patch("app.services.git_history_analyzer.GitHistoryAnalyzer.get_default_branch", return_value="main"), \
         patch("app.services.repository_analyzer.RepositoryAnalyzer.analyze") as mock_analyze, \
         patch("app.services.git_history_analyzer.GitHistoryAnalyzer.extract_recent_commits", return_value=[]):

        mock_clone.return_value = MagicMock()
        mock_analyze.return_value = {
            "primary_language": "Python",
            "total_files": 12,
            "source_files": 10,
            "files": [],
            "language_breakdown": {"Python": 10, "Markdown": 2},
        }
        yield


# ==============================================================================
# Requirement A: Authenticated User A analyzing repo creates user_repository_history entry
# ==============================================================================
def test_a_user_a_analyzing_repo_creates_user_repository_history(mock_db, mock_git_pipeline):
    app.dependency_overrides[get_current_user] = lambda: USER_A

    resp = client.post("/api/repositories/analyze", json={"github_url": "https://github.com/org/repo-alpha"})
    assert resp.status_code == 201

    repo_id = resp.json()["repository"]["id"]
    assert len(mock_db.tables["repositories"]) == 1
    assert mock_db.tables["repositories"][0]["id"] == repo_id

    # user_repository_history entry must exist for User A
    assert len(mock_db.tables["user_repository_history"]) == 1
    history_entry = mock_db.tables["user_repository_history"][0]
    assert history_entry["user_id"] == USER_A.id
    assert history_entry["repository_id"] == repo_id


# ==============================================================================
# Requirement B: Authenticated User B analyzing same repo links User B without duplicating repositories record
# ==============================================================================
def test_b_user_b_analyzing_same_repo_links_without_duplicate(mock_db, mock_git_pipeline):
    # User A analyzes first
    app.dependency_overrides[get_current_user] = lambda: USER_A
    resp_a = client.post("/api/repositories/analyze", json={"github_url": "https://github.com/org/shared-repo"})
    assert resp_a.status_code == 201
    repo_id = resp_a.json()["repository"]["id"]

    # User B analyzes the same repository
    app.dependency_overrides[get_current_user] = lambda: USER_B
    resp_b = client.post("/api/repositories/analyze", json={"github_url": "https://github.com/org/shared-repo"})
    assert resp_b.status_code == 201
    assert resp_b.json()["repository"]["id"] == repo_id

    # Repository table must NOT duplicate the repository record
    assert len(mock_db.tables["repositories"]) == 1

    # Both User A and User B must have history entries pointing to the same repo_id
    assert len(mock_db.tables["user_repository_history"]) == 2
    user_ids = {h["user_id"] for h in mock_db.tables["user_repository_history"]}
    assert user_ids == {USER_A.id, USER_B.id}
    assert all(h["repository_id"] == repo_id for h in mock_db.tables["user_repository_history"])


# ==============================================================================
# Requirement C: User A listing repositories sees only User A repositories
# ==============================================================================
def test_c_user_a_listing_repositories_sees_only_user_a(mock_db, mock_git_pipeline):
    # User A analyzes repo-a
    app.dependency_overrides[get_current_user] = lambda: USER_A
    client.post("/api/repositories/analyze", json={"github_url": "https://github.com/org/repo-a"})

    # User B analyzes repo-b
    app.dependency_overrides[get_current_user] = lambda: USER_B
    client.post("/api/repositories/analyze", json={"github_url": "https://github.com/org/repo-b"})

    # User A lists repositories
    app.dependency_overrides[get_current_user] = lambda: USER_A
    resp = client.get("/api/repositories")
    assert resp.status_code == 200
    repos = resp.json()
    assert len(repos) == 1
    assert repos[0]["name"] == "repo-a"


# ==============================================================================
# Requirement D: User B listing repositories sees only User B repositories
# ==============================================================================
def test_d_user_b_listing_repositories_sees_only_user_b(mock_db, mock_git_pipeline):
    # User A analyzes repo-a
    app.dependency_overrides[get_current_user] = lambda: USER_A
    client.post("/api/repositories/analyze", json={"github_url": "https://github.com/org/repo-a"})

    # User B analyzes repo-b1 and repo-b2
    app.dependency_overrides[get_current_user] = lambda: USER_B
    client.post("/api/repositories/analyze", json={"github_url": "https://github.com/org/repo-b1"})
    client.post("/api/repositories/analyze", json={"github_url": "https://github.com/org/repo-b2"})

    # User B lists repositories
    resp = client.get("/api/repositories")
    assert resp.status_code == 200
    repos = resp.json()
    assert len(repos) == 2
    repo_names = {r["name"] for r in repos}
    assert repo_names == {"repo-b1", "repo-b2"}
    assert "repo-a" not in repo_names


# ==============================================================================
# Requirement E: Unauthenticated requests to list repositories return 401
# ==============================================================================
def test_e_unauthenticated_list_repositories_returns_401():
    app.dependency_overrides.clear()
    resp = client.get("/api/repositories")
    assert resp.status_code == 401


# ==============================================================================
# Requirement F: User A deleting User A repo history deletes only history row, not repositories record
# ==============================================================================
def test_f_user_a_deletes_history_preserves_repositories_row(mock_db, mock_git_pipeline):
    app.dependency_overrides[get_current_user] = lambda: USER_A
    resp_create = client.post("/api/repositories/analyze", json={"github_url": "https://github.com/org/to-delete"})
    repo_id = resp_create.json()["repository"]["id"]

    # Delete history
    resp_del = client.delete(f"/api/repositories/{repo_id}/history")
    assert resp_del.status_code == 204

    # History row for User A must be removed
    user_a_hist = [h for h in mock_db.tables["user_repository_history"] if h["user_id"] == USER_A.id]
    assert len(user_a_hist) == 0

    # Underlying repositories row must STILL exist!
    assert len(mock_db.tables["repositories"]) == 1
    assert mock_db.tables["repositories"][0]["id"] == repo_id


# ==============================================================================
# Requirement G: After User A deletes history, User B still has repository in history
# ==============================================================================
def test_g_user_a_delete_does_not_affect_user_b_history(mock_db, mock_git_pipeline):
    # Both users analyze the shared repository
    app.dependency_overrides[get_current_user] = lambda: USER_A
    resp_a = client.post("/api/repositories/analyze", json={"github_url": "https://github.com/org/shared-keep"})
    repo_id = resp_a.json()["repository"]["id"]

    app.dependency_overrides[get_current_user] = lambda: USER_B
    client.post("/api/repositories/analyze", json={"github_url": "https://github.com/org/shared-keep"})

    # User A deletes their history entry
    app.dependency_overrides[get_current_user] = lambda: USER_A
    resp_del = client.delete(f"/api/repositories/{repo_id}/history")
    assert resp_del.status_code == 204

    # User A sees 0 repos
    resp_list_a = client.get("/api/repositories")
    assert len(resp_list_a.json()) == 0

    # User B STILL sees the repository in history
    app.dependency_overrides[get_current_user] = lambda: USER_B
    resp_list_b = client.get("/api/repositories")
    assert resp_list_b.status_code == 200
    assert len(resp_list_b.json()) == 1
    assert resp_list_b.json()[0]["id"] == repo_id


# ==============================================================================
# Requirement H: User A attempting to delete repo only in User B's history returns 403 Forbidden
# ==============================================================================
def test_h_user_a_deleting_user_b_repo_returns_403(mock_db, mock_git_pipeline):
    # User B analyzes repo-b
    app.dependency_overrides[get_current_user] = lambda: USER_B
    resp_b = client.post("/api/repositories/analyze", json={"github_url": "https://github.com/org/repo-b-private"})
    repo_id = resp_b.json()["repository"]["id"]

    # User A attempts to delete it
    app.dependency_overrides[get_current_user] = lambda: USER_A
    resp_del = client.delete(f"/api/repositories/{repo_id}/history")
    assert resp_del.status_code == 403
    assert "permission" in resp_del.json()["detail"].lower()


# ==============================================================================
# Requirement I: Attempting to delete non-existent repository returns 404 Not Found
# ==============================================================================
def test_i_delete_non_existent_repository_returns_404(mock_db):
    app.dependency_overrides[get_current_user] = lambda: USER_A
    fake_id = "00000000-0000-0000-0000-999999999999"
    resp = client.delete(f"/api/repositories/{fake_id}/history")
    assert resp.status_code == 404
    assert f"Repository '{fake_id}' not found." in resp.json()["detail"]


# ==============================================================================
# Requirement J: Unauthenticated delete requests return 401 Unauthorized
# ==============================================================================
def test_j_unauthenticated_delete_returns_401():
    app.dependency_overrides.clear()
    resp = client.delete("/api/repositories/00000000-0000-0000-0000-111111111111/history")
    assert resp.status_code == 401
