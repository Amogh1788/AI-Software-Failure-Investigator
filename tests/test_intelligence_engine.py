import os
import sys
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import git
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from app.services.intelligence_engine import IntelligenceEngine
from app.models.analysis import EvidenceStrength

client = TestClient(app)

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "checkout-testbed"
MOCK_REPO_ID = "11111111-1111-1111-1111-111111111111"
MOCK_INV_ID = "22222222-2222-2222-2222-222222222222"
MOCK_RUN_ID = "44444444-4444-4444-4444-444444444444"


@pytest.fixture
def temp_checkout_repo(tmp_path):
    """
    Creates a temporary Git repository with deterministic commit history
    reproducing the checkout-testbed scenario:
    1. Initial payment/controller setup
    2. Checkout service implementation
    3. FLASHSALE discount promo regression (modifies known target area)
    4. Checkout test
    """
    tmp_repo_dir = tmp_path / "checkout-testbed"
    tmp_repo_dir.mkdir(parents=True, exist_ok=True)

    src_dir = tmp_repo_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    tests_dir = tmp_repo_dir / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)

    # Initialize Git repository
    repo = git.Repo.init(str(tmp_repo_dir))
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test Dev")
        config.set_value("user", "email", "testdev@example.com")

    # 1. Initial payment/controller setup
    shutil.copyfile(
        FIXTURE_PATH / "src" / "PaymentRequestBuilder.java",
        src_dir / "PaymentRequestBuilder.java",
    )
    shutil.copyfile(
        FIXTURE_PATH / "src" / "CheckoutController.java",
        src_dir / "CheckoutController.java",
    )
    repo.git.add(A=True)
    repo.index.commit("feat(checkout): initial payment request builder and controller setup")

    # 2. Checkout service implementation (initial working version before promo tier)
    initial_checkout_service = """package com.example.checkout;

import java.math.BigDecimal;

public class CheckoutService {
    private final PaymentGateway paymentGateway = new PaymentGateway();

    public CheckoutResponse processCheckout(CheckoutRequest request) {
        BigDecimal subtotal = request.getSubtotal();
        BigDecimal paymentTotal = subtotal;

        if (request.getDiscountCode() != null && !request.getDiscountCode().isEmpty()) {
            paymentTotal = applyDiscount(request.getDiscountCode(), subtotal);
        }

        PaymentRequest paymentRequest = new PaymentRequestBuilder()
            .setCustomerId(request.getCustomerId())
            .setAmount(paymentTotal)
            .build();

        return paymentGateway.charge(paymentRequest);
    }

    public BigDecimal applyDiscount(String discountCode, BigDecimal subtotal) {
        if ("DISCOUNT50".equalsIgnoreCase(discountCode)) {
            return subtotal.multiply(new BigDecimal("0.50"));
        }
        return subtotal;
    }
}
"""
    (src_dir / "CheckoutService.java").write_text(initial_checkout_service, encoding="utf-8")
    repo.git.add(A=True)
    repo.index.commit("feat(checkout): add checkout service implementation")

    # 3. FLASHSALE discount promo regression (modifies known target area)
    shutil.copyfile(
        FIXTURE_PATH / "src" / "CheckoutService.java",
        src_dir / "CheckoutService.java",
    )
    repo.git.add(A=True)
    repo.index.commit("refactor(checkout): add FLASHSALE discount promo tier")

    # 4. Checkout test
    shutil.copyfile(
        FIXTURE_PATH / "tests" / "CheckoutServiceTest.java",
        tests_dir / "CheckoutServiceTest.java",
    )
    repo.git.add(A=True)
    repo.index.commit("test: add unit test for checkout service")

    try:
        yield tmp_repo_dir, repo
    finally:
        repo.close()


# ====================================================================
# 1. Deterministic Evaluation Fixture & Recall Metrics
# ====================================================================

def test_intelligence_engine_evaluation_fixture_recall(temp_checkout_repo):
    """
    Evaluate IntelligenceEngine on the deterministic checkout-testbed fixture.
    Measures Recall@1 and Recall@3 against known ground-truth defect target:
    'src/CheckoutService.java'.
    """
    tmp_repo_dir, git_repo = temp_checkout_repo
    evidence_dir = FIXTURE_PATH / "evidence"
    bug_report = (evidence_dir / "bug_report.txt").read_text(encoding="utf-8")
    app_log = (evidence_dir / "application.log").read_text(encoding="utf-8")
    stack_trace = (evidence_dir / "stack_trace.txt").read_text(encoding="utf-8")
    test_output = (evidence_dir / "test_output.txt").read_text(encoding="utf-8")

    evidence_items = [
        {"evidence_type": "bug_report", "content": bug_report},
        {"evidence_type": "application_log", "content": app_log},
        {"evidence_type": "stack_trace", "content": stack_trace},
        {"evidence_type": "test_output", "content": test_output},
    ]

    candidates, chain, commits, signals_summary, summary = IntelligenceEngine.analyze(
        repo_dir=str(tmp_repo_dir),
        git_repo=git_repo,
        evidence_items=evidence_items,
    )

    # Validate output structure
    assert len(candidates) > 0, "Expected at least one candidate ranked"
    assert signals_summary is not None
    assert summary is not None

    # Ground-truth target
    ground_truth_target = "src/CheckoutService.java"

    # Evaluate Recall@1
    top_1_candidates = [c.file_path for c in candidates[:1]]
    recall_at_1 = 1.0 if ground_truth_target in top_1_candidates else 0.0

    # Evaluate Recall@3
    top_3_candidates = [c.file_path for c in candidates[:3]]
    recall_at_3 = 1.0 if ground_truth_target in top_3_candidates else 0.0

    print(f"\n[EVALUATION METRIC] Recall@1: {recall_at_1}")
    print(f"[EVALUATION METRIC] Recall@3: {recall_at_3}")

    assert recall_at_1 == 1.0, f"Expected {ground_truth_target} at Rank #1, got {top_1_candidates}"
    assert recall_at_3 == 1.0, f"Expected {ground_truth_target} within top 3"

    # Verify candidate details for Rank #1
    top_candidate = candidates[0]
    assert top_candidate.file_path == ground_truth_target
    assert top_candidate.evidence_strength == EvidenceStrength.HIGH
    assert top_candidate.function_name in ["applyDiscount", "processCheckout"]
    assert top_candidate.line_number in [21, 31, 38]

    # Verify signals breakdown
    sig = top_candidate.signals
    assert sig.stack_trace_score > 0, "Expected stack trace frame match"
    assert sig.test_failure_score > 0, "Expected test failure match"
    assert sig.logs_score > 0, "Expected error log match"
    assert sig.bug_report_score > 0, "Expected bug report token match"
    assert sig.git_recency_score > 0, "Expected git recency score"

    # Verify scoring formula strictly follows:
    # 0.35 * stack + 0.25 * test + 0.20 * logs + 0.10 * bug + 0.10 * git
    expected_score = round(
        0.35 * sig.stack_trace_score
        + 0.25 * sig.test_failure_score
        + 0.20 * sig.logs_score
        + 0.10 * sig.bug_report_score
        + 0.10 * sig.git_recency_score,
        4,
    )
    assert top_candidate.evidence_score == expected_score

    # Verify failure chain synthesis
    assert len(chain) >= 3
    sources = [step.source for step in chain]
    assert any("Bug Report" in s for s in sources)
    assert any("Logs" in s or "Stack Trace" in s for s in sources)
    assert any("Test" in s for s in sources)

    # Verify correlated git commits rank regression commit first
    assert len(commits) > 0
    top_commit = commits[0]
    assert "FLASHSALE" in top_commit.commit_message, "Expected FLASHSALE regression commit to be top relevant commit"
    assert "Likely regression-introducing commit" in top_commit.relevance_reason

    # Verify later test commit is identified as regression-detection/testing commit
    test_commits = [c for c in commits if "add unit test" in c.commit_message or "test:" in c.commit_message]
    assert len(test_commits) > 0, "Expected test commit in relevant commits"
    assert "Regression-detection/testing commit" in test_commits[0].relevance_reason


# ====================================================================
# 2. HTTP 409 Guard on Draft Investigation
# ====================================================================

def test_analyze_draft_investigation_returns_409():
    """
    Attempting to analyze an investigation in 'draft' status must return HTTP 409.
    """
    mock_db = MagicMock()

    mock_inv_query = MagicMock()
    mock_inv_query.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": MOCK_INV_ID,
            "repository_id": MOCK_REPO_ID,
            "title": "Unready Case",
            "status": "draft",
        }
    ]

    mock_db.table.side_effect = lambda table: {
        "investigations": mock_inv_query,
    }.get(table, MagicMock())

    with patch("app.services.analysis_service.get_service_role_client", return_value=mock_db):
        response = client.post(f"/api/investigations/{MOCK_INV_ID}/analyze")

    assert response.status_code == 409
    data = response.json()
    assert "Investigation must be marked ready before analysis" in data["detail"]


# ====================================================================
# 3. Status Transition to Analyzing -> Completed
# ====================================================================

def test_analyze_ready_investigation_success(temp_checkout_repo):
    """
    Analyzing a ready investigation executes intelligence engine,
    persists run into investigation_runs, and updates status to completed.
    """
    tmp_repo_dir, _ = temp_checkout_repo
    mock_db = MagicMock()

    # 1. Investigation query returning status = 'ready'
    mock_inv_query = MagicMock()
    mock_inv_query.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": MOCK_INV_ID,
            "repository_id": MOCK_REPO_ID,
            "title": "Checkout Null Pointer Case",
            "status": "ready",
        }
    ]

    # 2. Repository query pointing to temporary git repo
    mock_repo_query = MagicMock()
    mock_repo_query.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": MOCK_REPO_ID,
            "github_url": str(tmp_repo_dir),
            "clone_url": str(tmp_repo_dir),
            "default_branch": "main",
        }
    ]

    # 3. Evidence mock
    evidence_dir = FIXTURE_PATH / "evidence"
    evidence_data = [
        {"id": "1", "investigation_id": MOCK_INV_ID, "evidence_type": "bug_report", "title": "Report", "content": (evidence_dir / "bug_report.txt").read_text(), "filename": "bug_report.txt", "byte_size": 100, "created_at": "2026-09-19T10:00:00Z"},
        {"id": "2", "investigation_id": MOCK_INV_ID, "evidence_type": "application_log", "title": "Logs", "content": (evidence_dir / "application.log").read_text(), "filename": "application.log", "byte_size": 100, "created_at": "2026-09-19T10:00:00Z"},
        {"id": "3", "investigation_id": MOCK_INV_ID, "evidence_type": "stack_trace", "title": "Trace", "content": (evidence_dir / "stack_trace.txt").read_text(), "filename": "stack_trace.txt", "byte_size": 100, "created_at": "2026-09-19T10:00:00Z"},
        {"id": "4", "investigation_id": MOCK_INV_ID, "evidence_type": "test_output", "title": "Test", "content": (evidence_dir / "test_output.txt").read_text(), "filename": "test_output.txt", "byte_size": 100, "created_at": "2026-09-19T10:00:00Z"},
    ]
    mock_evid_query = MagicMock()
    mock_evid_query.select.return_value.eq.return_value.order.return_value.execute.return_value.data = evidence_data

    # 4. Runs insert query
    mock_runs_query = MagicMock()
    mock_runs_query.insert.side_effect = lambda rec: MagicMock(
        execute=MagicMock(return_value=MagicMock(data=[{
            "id": MOCK_RUN_ID,
            "investigation_id": MOCK_INV_ID,
            "engine_version": "1.0.0",
            "status": "completed",
            "summary": rec["summary"],
            "failure_chain": rec["failure_chain"],
            "ranked_candidates": rec["ranked_candidates"],
            "relevant_commits": rec["relevant_commits"],
            "evidence_signals": rec["evidence_signals"],
            "run_duration_ms": rec["run_duration_ms"],
            "created_at": "2026-09-19T14:30:00Z",
        }]))
    )

    # Status update tracking
    update_statuses = []
    mock_update = MagicMock()
    mock_update.execute.return_value.data = [{"id": MOCK_INV_ID}]
    
    def handle_inv_update(payload):
        if "status" in payload:
            update_statuses.append(payload["status"])
        return MagicMock(eq=MagicMock(return_value=mock_update))
        
    mock_inv_query.update.side_effect = handle_inv_update

    mock_db.table.side_effect = lambda table: {
        "investigations": mock_inv_query,
        "repositories": mock_repo_query,
        "investigation_evidence": mock_evid_query,
        "investigation_runs": mock_runs_query,
    }.get(table, MagicMock())

    with patch("app.services.analysis_service.get_service_role_client", return_value=mock_db), \
         patch("app.services.evidence_service.get_service_role_client", return_value=mock_db):
        response = client.post(f"/api/investigations/{MOCK_INV_ID}/analyze")

    assert response.status_code == 200
    data = response.json()
    assert data["investigation_id"] == MOCK_INV_ID
    assert data["engine_version"] == "1.0.0"
    assert data["status"] == "completed"
    assert len(data["ranked_candidates"]) > 0
    assert data["ranked_candidates"][0]["file_path"] == "src/CheckoutService.java"

    # Verify status transitions: first 'analyzing', then 'completed'
    assert "analyzing" in update_statuses
    assert "completed" in update_statuses


# ====================================================================
# 4. Failure Recovery: Reset to Ready
# ====================================================================

def test_analyze_failure_reverts_status_to_ready(temp_checkout_repo):
    """
    If analysis throws an exception, status must be reverted from 'analyzing'
    back to 'ready' to prevent the case from being permanently locked.
    """
    tmp_repo_dir, _ = temp_checkout_repo
    mock_db = MagicMock()

    mock_inv_query = MagicMock()
    mock_inv_query.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": MOCK_INV_ID,
            "repository_id": MOCK_REPO_ID,
            "title": "Faulty Analysis Case",
            "status": "ready",
        }
    ]

    mock_repo_query = MagicMock()
    mock_repo_query.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": MOCK_REPO_ID,
            "github_url": str(tmp_repo_dir),
        }
    ]

    mock_evid_query = MagicMock()
    mock_evid_query.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []

    update_statuses = []
    mock_update = MagicMock()
    mock_update.execute.return_value.data = [{"id": MOCK_INV_ID}]
    mock_inv_query.update.side_effect = lambda p: (
        update_statuses.append(p.get("status")),
        MagicMock(eq=MagicMock(return_value=mock_update))
    )[1]

    mock_db.table.side_effect = lambda table: {
        "investigations": mock_inv_query,
        "repositories": mock_repo_query,
        "investigation_evidence": mock_evid_query,
    }.get(table, MagicMock())

    # Force failure during intelligence engine analysis
    with patch("app.services.analysis_service.get_service_role_client", return_value=mock_db), \
         patch("app.services.evidence_service.get_service_role_client", return_value=mock_db), \
         patch("app.services.intelligence_engine.IntelligenceEngine.analyze", side_effect=RuntimeError("Simulated engine failure")):
        
        response = client.post(f"/api/investigations/{MOCK_INV_ID}/analyze")

    assert response.status_code == 500
    assert "Simulated engine failure" in response.json()["detail"]

    # Verify status went to analyzing, and then was recovered to ready
    assert "analyzing" in update_statuses
    assert update_statuses[-1] == "ready", f"Expected final rollback to 'ready', got {update_statuses}"


# ====================================================================
# 5. Analysis Retrieval Endpoints
# ====================================================================

def test_get_latest_analysis_success():
    """Verify retrieving the latest analysis run."""
    mock_db = MagicMock()

    mock_runs_query = MagicMock()
    mock_runs_query.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {
            "id": MOCK_RUN_ID,
            "investigation_id": MOCK_INV_ID,
            "engine_version": "1.0.0",
            "status": "completed",
            "summary": "Top suspect: src/CheckoutService.java",
            "failure_chain": [],
            "ranked_candidates": [],
            "relevant_commits": [],
            "evidence_signals": {
                "stack_trace_signal": 0.8,
                "test_failure_signal": 0.9,
                "logs_tfidf_signal": 0.5,
                "bug_report_tfidf_signal": 0.4,
                "git_history_signal": 0.7,
                "score_formula": "evidence_score = ...",
                "score_disclaimer": "Evidence score is a weighted measure of supporting evidence and is not a probability.",
            },
            "run_duration_ms": 120,
            "created_at": "2026-09-19T14:30:00Z",
        }
    ]

    mock_db.table.side_effect = lambda table: {
        "investigation_runs": mock_runs_query,
    }.get(table, MagicMock())

    with patch("app.services.analysis_service.get_service_role_client", return_value=mock_db):
        response = client.get(f"/api/investigations/{MOCK_INV_ID}/analysis")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == MOCK_RUN_ID
    assert data["summary"] == "Top suspect: src/CheckoutService.java"


def test_get_latest_analysis_not_found():
    """Verify 404 when no analysis run exists for the investigation."""
    mock_db = MagicMock()

    mock_runs_query = MagicMock()
    mock_runs_query.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []

    mock_db.table.side_effect = lambda table: {
        "investigation_runs": mock_runs_query,
    }.get(table, MagicMock())

    with patch("app.services.analysis_service.get_service_role_client", return_value=mock_db):
        response = client.get(f"/api/investigations/{MOCK_INV_ID}/analysis")

    assert response.status_code == 404
    assert "No analysis results found" in response.json()["detail"]
