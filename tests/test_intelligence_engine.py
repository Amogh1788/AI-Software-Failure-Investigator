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

    # Verify older baseline commits are NOT classified as regression-introducing commits
    baseline_commits = [
        c for c in commits
        if "add checkout service implementation" in c.commit_message
        or "initial payment request builder" in c.commit_message
    ]
    for c in baseline_commits:
        assert "Likely regression-introducing commit" not in c.relevance_reason
        assert "regression-introducing" not in c.relevance_reason.lower()
        assert "Baseline setup commit" in c.relevance_reason


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


# ====================================================================
# 6. Deterministic Testbed Commit Causal Correlation
# ====================================================================

def test_git_causal_commit_correlation_deterministic_testbed():
    """
    Validate causal commit correlation against deterministic testbed ground truth:
    - b3a44a0 = likely regression-introducing commit
    - b2e8572 = regression-detection/testing commit
    - d7993bd and 24705a6 are NOT classified as the regression-introducing commit.
    - b3a44a0 ranks above d7993bd and 24705a6.
    """
    from app.models.analysis import FailureCandidate, EvidenceStrength, CandidateSignals

    mock_candidates = [
        FailureCandidate(
            file_path="src/CheckoutService.java",
            function_name="applyDiscount",
            line_number=31,
            evidence_score=0.95,
            evidence_strength=EvidenceStrength.HIGH,
            supporting_evidence=["Stack trace at CheckoutService.java:31"],
            signals=CandidateSignals(
                stack_trace_score=1.0,
                test_failure_score=0.9,
                logs_score=0.8,
                bug_report_score=0.7,
                git_recency_score=0.8,
                final_score=0.95,
            ),
        )
    ]
    mock_stack_frames = [
        {
            "filename": "CheckoutService.java",
            "class_name": "com.example.checkout.CheckoutService",
            "function_name": "applyDiscount",
            "line_number": 31,
        }
    ]

    # Mock diffs
    mock_diff_test = MagicMock()
    mock_diff_test.b_path = "tests/CheckoutServiceTest.java"
    mock_diff_test.a_path = "tests/CheckoutServiceTest.java"
    mock_diff_test.new_file = True
    mock_diff_test.deleted_file = False
    mock_diff_test.diff = b"@@ -0,0 +1,15 @@\n+package com.example.checkout;\n+public class CheckoutServiceTest {}\n"

    mock_diff_flashsale = MagicMock()
    mock_diff_flashsale.b_path = "src/CheckoutService.java"
    mock_diff_flashsale.a_path = "src/CheckoutService.java"
    mock_diff_flashsale.new_file = False
    mock_diff_flashsale.deleted_file = False
    mock_diff_flashsale.diff = (
        b"@@ -27,6 +27,9 @@ public BigDecimal applyDiscount(String discountCode, BigDecimal subtotal) {\n"
        b"-        if (\"DISCOUNT50\".equalsIgnoreCase(discountCode)) return subtotal.multiply(new BigDecimal(\"0.50\"));\n"
        b"+        if (\"DISCOUNT50\".equalsIgnoreCase(discountCode)) {\n"
        b"+            return subtotal.multiply(new BigDecimal(\"0.50\"));\n"
        b"+        } else if (\"FLASHSALE\".equalsIgnoreCase(discountCode)) {\n"
        b"+            // Regression: returns null on promo tier\n"
        b"+            return null;\n"
        b"+        }\n"
    )

    mock_diff_initial_cs = MagicMock()
    mock_diff_initial_cs.b_path = "src/CheckoutService.java"
    mock_diff_initial_cs.a_path = "src/CheckoutService.java"
    mock_diff_initial_cs.new_file = True
    mock_diff_initial_cs.deleted_file = False
    mock_diff_initial_cs.diff = b"@@ -0,0 +1,8 @@\n+package com.example.checkout;\n"

    mock_diff_root = MagicMock()
    mock_diff_root.b_path = "src/PaymentRequestBuilder.java"
    mock_diff_root.a_path = "src/PaymentRequestBuilder.java"
    mock_diff_root.new_file = True
    mock_diff_root.deleted_file = False
    mock_diff_root.diff = b"@@ -0,0 +1,10 @@\n+package com.example.checkout;\n"

    # Commit objects (newest to oldest)
    c_test = MagicMock()
    c_test.hexsha = "b2e8572abcdef123"
    c_test.message = "test: add unit test for checkout service"
    c_test.stats.files = {"tests/CheckoutServiceTest.java": {}}
    c_test.parents = [MagicMock()]
    c_test.parents[0].diff.return_value = [mock_diff_test]

    c_flashsale = MagicMock()
    c_flashsale.hexsha = "b3a44a0abcdef123"
    c_flashsale.message = "refactor(checkout): add FLASHSALE discount promo tier"
    c_flashsale.stats.files = {"src/CheckoutService.java": {}}
    c_flashsale.parents = [MagicMock()]
    c_flashsale.parents[0].diff.return_value = [mock_diff_flashsale]

    c_base_cs = MagicMock()
    c_base_cs.hexsha = "d7993bdabcdef123"
    c_base_cs.message = "feat(checkout): add checkout service implementation"
    c_base_cs.stats.files = {"src/CheckoutService.java": {}}
    c_base_cs.parents = [MagicMock()]
    c_base_cs.parents[0].diff.return_value = [mock_diff_initial_cs]

    c_root = MagicMock()
    c_root.hexsha = "24705a6abcdef123"
    c_root.message = "feat(checkout): initial payment request builder and controller setup"
    c_root.stats.files = {"src/PaymentRequestBuilder.java": {}}
    c_root.parents = []
    c_root.diff.return_value = [mock_diff_root]

    mock_repo = MagicMock()
    mock_repo.iter_commits.return_value = [c_test, c_flashsale, c_base_cs, c_root]

    bug_report = "Checkout returns 500 when FLASHSALE discount code applied. paymentTotal null."
    logs = "Applying discount code FLASHSALE. paymentTotal cannot be null."
    test_output = "CheckoutServiceTest testProcessCheckoutWithFlashSaleDiscount FAILED"

    relevant_commits = IntelligenceEngine._correlate_git_commits(
        repo=mock_repo,
        candidates=mock_candidates,
        stack_frames=mock_stack_frames,
        bug_report=bug_report,
        logs=logs,
        test_output=test_output,
    )

    commit_map = {c.commit_hash[:7]: c for c in relevant_commits}

    # 1. b3a44a0 = likely regression-introducing commit
    assert "b3a44a0" in commit_map, "Expected b3a44a0 in relevant commits"
    assert "Likely regression-introducing commit" in commit_map["b3a44a0"].relevance_reason

    # 2. b2e8572 = regression-detection/testing commit
    assert "b2e8572" in commit_map, "Expected b2e8572 in relevant commits"
    assert "Regression-detection/testing commit" in commit_map["b2e8572"].relevance_reason

    # 3. d7993bd and 24705a6 are not classified as regression-introducing commit
    if "d7993bd" in commit_map:
        assert "Likely regression-introducing commit" not in commit_map["d7993bd"].relevance_reason
        assert "regression-introducing" not in commit_map["d7993bd"].relevance_reason.lower()
    if "24705a6" in commit_map:
        assert "Likely regression-introducing commit" not in commit_map["24705a6"].relevance_reason
        assert "regression-introducing" not in commit_map["24705a6"].relevance_reason.lower()

    # 4. b3a44a0 must rank above d7993bd and 24705a6
    hashes = [c.commit_hash[:7] for c in relevant_commits]
    assert hashes.index("b3a44a0") == 0, f"Expected b3a44a0 to rank #1, got: {hashes}"


# ====================================================================
# 8. API Integration Test: Live Remote Commit Structure
# ====================================================================

def test_analyze_api_with_live_remote_commit_structure():
    """
    Integration test exercising the actual POST /api/investigations/{id}/analyze API endpoint
    with the exact commit structure matching the live remote repository:
    https://github.com/Amogh1788/AI-SFI-Checkout-Testbed

    Ground truth:
    - b3a44a0 refactor(checkout): add FLASHSALE discount promo tier -> Likely regression-introducing commit (#1)
    - b2e8572 test: add unit test for checkout service -> Regression-detection/testing commit
    - d7993bd feat: add checkout service and payment pipeline -> Baseline setup commit
    - 24705a6 feat: initial payment and controller setup -> Baseline setup commit
    """
    mock_db = MagicMock()

    # 1. Investigation query returning status = 'ready'
    mock_inv_query = MagicMock()
    mock_inv_query.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": MOCK_INV_ID,
            "repository_id": MOCK_REPO_ID,
            "title": "Live Remote Testbed Case",
            "status": "ready",
        }
    ]

    # 2. Repository query
    mock_repo_query = MagicMock()
    mock_repo_query.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": MOCK_REPO_ID,
            "github_url": "https://github.com/Amogh1788/AI-SFI-Checkout-Testbed",
            "clone_url": "https://github.com/Amogh1788/AI-SFI-Checkout-Testbed",
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
    inserted_runs = []
    mock_runs_query = MagicMock()
    def handle_run_insert(rec):
        run_record = {
            "id": MOCK_RUN_ID,
            "investigation_id": MOCK_INV_ID,
            "engine_version": "1.0.0",
            "status": "completed",
            "summary": rec.get("summary", ""),
            "failure_chain": rec.get("failure_chain", []),
            "ranked_candidates": rec.get("ranked_candidates", []),
            "relevant_commits": rec.get("relevant_commits", []),
            "evidence_signals": rec.get("evidence_signals", {}),
            "run_duration_ms": rec.get("run_duration_ms", 100),
            "created_at": "2026-09-19T14:30:00Z",
        }
        inserted_runs.append(run_record)
        return MagicMock(execute=MagicMock(return_value=MagicMock(data=[run_record])))

    mock_runs_query.insert.side_effect = handle_run_insert

    # Status update tracking
    mock_update = MagicMock()
    mock_update.execute.return_value.data = [{"id": MOCK_INV_ID}]
    mock_inv_query.update.return_value.eq.return_value = mock_update

    mock_db.table.side_effect = lambda table: {
        "investigations": mock_inv_query,
        "repositories": mock_repo_query,
        "investigation_evidence": mock_evid_query,
        "investigation_runs": mock_runs_query,
    }.get(table, MagicMock())

    # Build exact mock commits as found in remote testbed
    # Commit 1 (newest): 6d5ff2d - test
    c1 = MagicMock()
    c1.hexsha = "6d5ff2db974b"
    c1.message = "test: add unit test for checkout service"
    c1.stats.files = {"tests/CheckoutServiceTest.java": {}}
    mock_d1 = MagicMock()
    mock_d1.b_path = "tests/CheckoutServiceTest.java"
    mock_d1.a_path = "tests/CheckoutServiceTest.java"
    mock_d1.new_file = False
    mock_d1.diff = b"@@ -1,5 +1,15 @@\n+@Test\n+public void testFlashSale() {}\n"
    c1.parents = [MagicMock()]
    c1.parents[0].diff.return_value = [mock_d1]

    # Commit 2: 875bcf7 - refactor(checkout): add FLASHSALE discount promo tier (non-empty diff modifying CheckoutService.java)
    c2 = MagicMock()
    c2.hexsha = "875bcf7a1786"
    c2.message = "refactor(checkout): add FLASHSALE discount promo tier"
    c2.stats.files = {"src/CheckoutService.java": {}}
    mock_d2 = MagicMock()
    mock_d2.b_path = "src/CheckoutService.java"
    mock_d2.a_path = "src/CheckoutService.java"
    mock_d2.new_file = False
    mock_d2.diff = (
        b"@@ -25,2 +26,5 @@\n"
        b"+ } else if (\"FLASHSALE\".equalsIgnoreCase(discountCode)) {\n"
        b"+     return null;\n"
        b"+ }\n"
    )
    c2.parents = [MagicMock()]
    c2.parents[0].diff.return_value = [mock_d2]

    # Commit 3: 2a2701b - feat: add checkout service and payment pipeline
    c3 = MagicMock()
    c3.hexsha = "2a2701b0d6cb"
    c3.message = "feat: add checkout service and payment pipeline"
    c3.stats.files = {"src/CheckoutService.java": {}}
    mock_d3 = MagicMock()
    mock_d3.b_path = "src/CheckoutService.java"
    mock_d3.a_path = "src/CheckoutService.java"
    mock_d3.new_file = True
    mock_d3.diff = b"@@ -0,0 +1,30 @@\n+package com.example.checkout;\n"
    c3.parents = [MagicMock()]
    c3.parents[0].diff.return_value = [mock_d3]

    # Commit 4: 24705a6 - feat: initial payment and controller setup
    c4 = MagicMock()
    c4.hexsha = "24705a6faca0"
    c4.message = "feat: initial payment and controller setup"
    c4.stats.files = {"src/CheckoutController.java": {}, "src/PaymentRequestBuilder.java": {}}
    mock_d4 = MagicMock()
    mock_d4.b_path = "src/CheckoutController.java"
    mock_d4.a_path = "src/CheckoutController.java"
    mock_d4.new_file = True
    mock_d4.diff = b"@@ -0,0 +1,20 @@\n+package com.example.checkout;\n"
    c4.parents = []
    c4.diff.return_value = [mock_d4]

    mock_git_repo = MagicMock()
    mock_git_repo.iter_commits.return_value = [c1, c2, c3, c4]

    with patch("app.services.analysis_service.get_service_role_client", return_value=mock_db), \
         patch("app.services.evidence_service.get_service_role_client", return_value=mock_db), \
         patch("app.services.analysis_service.GitHubService.clone_repository_safely", return_value=mock_git_repo), \
         patch("os.path.exists", return_value=True), \
         patch("app.services.intelligence_engine.IntelligenceEngine._collect_repository_source_files", return_value={
             "src/CheckoutService.java": (FIXTURE_PATH / "src" / "CheckoutService.java").read_text(encoding="utf-8")
         }):
        response = client.post(f"/api/investigations/{MOCK_INV_ID}/analyze")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"

    commits = data.get("relevant_commits", [])
    assert len(commits) >= 2, "Expected correlated commits in API response"

    # Assert summary references 875bcf7 and Likely regression-introducing commit
    assert "875bcf7a" in data["summary"]
    assert "Likely regression-introducing commit" in data["summary"]

    # 1. Rank #1 must be 875bcf7 with 'Likely regression-introducing commit'
    top_commit = commits[0]
    assert top_commit["commit_hash"] == "875bcf7a"
    assert "Likely regression-introducing commit" in top_commit["relevance_reason"]
    assert "CheckoutService.java" in top_commit["relevance_reason"]

    # Summary commit == relevant_commits[0]
    assert top_commit["commit_hash"] in data["summary"]

    # 2. Test commit must be 6d5ff2d with 'Regression-detection/testing commit'
    test_commit = commits[1]
    assert test_commit["commit_hash"].startswith("6d5ff2d")
    assert "Regression-detection/testing commit" in test_commit["relevance_reason"]

    # 3. Commit 3 must be 2a2701b with 'Baseline setup commit'
    base_commit1 = commits[2]
    assert base_commit1["commit_hash"].startswith("2a2701b")
    assert "Baseline setup commit" in base_commit1["relevance_reason"]
    assert "Likely regression-introducing commit" not in base_commit1["relevance_reason"]

    # 4. Commit 4 must be 24705a6 with 'Baseline setup commit'
    base_commit2 = commits[3]
    assert base_commit2["commit_hash"].startswith("24705a6")
    assert "Baseline setup commit" in base_commit2["relevance_reason"]
    assert "Likely regression-introducing commit" not in base_commit2["relevance_reason"]


def test_repeated_analysis_runs_consistency():
    """
    Run analysis twice on the same investigation.
    Verify:
    Run 1: one complete consistent result.
    Run 2: new run ID, one complete consistent result, no stale Git classifications inherited.
    """
    mock_db = MagicMock()
    run_records_in_db = []

    # Investigation mock query
    mock_inv_query = MagicMock()
    mock_inv_query.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": MOCK_INV_ID,
            "repository_id": MOCK_REPO_ID,
            "title": "Repeated Run Case",
            "status": "ready",
        }
    ]

    # Repository mock query
    mock_repo_query = MagicMock()
    mock_repo_query.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": MOCK_REPO_ID,
            "github_url": "https://github.com/Amogh1788/AI-SFI-Checkout-Testbed",
            "clone_url": "https://github.com/Amogh1788/AI-SFI-Checkout-Testbed",
            "default_branch": "main",
        }
    ]

    # Evidence mock
    evidence_dir = FIXTURE_PATH / "evidence"
    evidence_data = [
        {"id": "1", "investigation_id": MOCK_INV_ID, "evidence_type": "bug_report", "title": "Report", "content": (evidence_dir / "bug_report.txt").read_text(), "filename": "bug_report.txt", "byte_size": 100, "created_at": "2026-09-19T10:00:00Z"},
        {"id": "2", "investigation_id": MOCK_INV_ID, "evidence_type": "application_log", "title": "Logs", "content": (evidence_dir / "application.log").read_text(), "filename": "application.log", "byte_size": 100, "created_at": "2026-09-19T10:00:00Z"},
        {"id": "3", "investigation_id": MOCK_INV_ID, "evidence_type": "stack_trace", "title": "Trace", "content": (evidence_dir / "stack_trace.txt").read_text(), "filename": "stack_trace.txt", "byte_size": 100, "created_at": "2026-09-19T10:00:00Z"},
        {"id": "4", "investigation_id": MOCK_INV_ID, "evidence_type": "test_output", "title": "Test", "content": (evidence_dir / "test_output.txt").read_text(), "filename": "test_output.txt", "byte_size": 100, "created_at": "2026-09-19T10:00:00Z"},
    ]
    mock_evid_query = MagicMock()
    mock_evid_query.select.return_value.eq.return_value.order.return_value.execute.return_value.data = evidence_data

    # Investigation runs mock
    import uuid
    mock_runs_query = MagicMock()

    def handle_insert(rec):
        new_id = str(uuid.uuid4())
        rec_copy = dict(rec)
        rec_copy["id"] = new_id
        rec_copy["created_at"] = "2026-09-20T17:35:00Z"
        run_records_in_db.append(rec_copy)
        return MagicMock(execute=MagicMock(return_value=MagicMock(data=[rec_copy])))

    mock_runs_query.insert.side_effect = handle_insert

    def handle_select_runs(*args, **kwargs):
        # Return newest run first
        sorted_runs = sorted(run_records_in_db, key=lambda r: r["created_at"], reverse=True)
        m = MagicMock()
        m.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = sorted_runs[:1]
        m.eq.return_value.order.return_value.execute.return_value.data = sorted_runs
        return m

    mock_runs_query.select.side_effect = handle_select_runs

    # Status update tracking
    mock_update = MagicMock()
    mock_update.execute.return_value.data = [{"id": MOCK_INV_ID}]
    mock_inv_query.update.return_value.eq.return_value = mock_update

    mock_db.table.side_effect = lambda table: {
        "investigations": mock_inv_query,
        "repositories": mock_repo_query,
        "investigation_evidence": mock_evid_query,
        "investigation_runs": mock_runs_query,
    }.get(table, MagicMock())

    # Build commits
    c1 = MagicMock(hexsha="6d5ff2db974b", message="test: add unit test for checkout service")
    c1.stats.files = {"tests/CheckoutServiceTest.java": {}}
    mock_d1 = MagicMock(b_path="tests/CheckoutServiceTest.java", a_path="tests/CheckoutServiceTest.java", new_file=False, diff=b"+@Test\n")
    c1.parents = [MagicMock()]
    c1.parents[0].diff.return_value = [mock_d1]

    c2 = MagicMock(hexsha="875bcf7a1786", message="refactor(checkout): add FLASHSALE discount promo tier")
    c2.stats.files = {"src/CheckoutService.java": {}}
    mock_d2 = MagicMock(
        b_path="src/CheckoutService.java",
        a_path="src/CheckoutService.java",
        new_file=False,
        diff=b"@@ -25,2 +26,5 @@\n+ } else if (\"FLASHSALE\".equalsIgnoreCase(discountCode)) {\n+     return null;\n+ }\n",
    )
    c2.parents = [MagicMock()]
    c2.parents[0].diff.return_value = [mock_d2]

    c3 = MagicMock(hexsha="2a2701b0d6cb", message="feat: add checkout service and payment pipeline")
    c3.stats.files = {"src/CheckoutService.java": {}}
    mock_d3 = MagicMock(b_path="src/CheckoutService.java", a_path="src/CheckoutService.java", new_file=True, diff=b"+package com.example.checkout;\n")
    c3.parents = [MagicMock()]
    c3.parents[0].diff.return_value = [mock_d3]

    c4 = MagicMock(hexsha="24705a6faca0", message="feat: initial payment and controller setup")
    c4.stats.files = {"src/CheckoutController.java": {}, "src/PaymentRequestBuilder.java": {}}
    mock_d4 = MagicMock(b_path="src/CheckoutController.java", a_path="src/CheckoutController.java", new_file=True, diff=b"+package com.example.checkout;\n")
    c4.parents = []
    c4.diff.return_value = [mock_d4]

    mock_git_repo = MagicMock()
    mock_git_repo.iter_commits.return_value = [c1, c2, c3, c4]

    with patch("app.services.analysis_service.get_service_role_client", return_value=mock_db), \
         patch("app.services.evidence_service.get_service_role_client", return_value=mock_db), \
         patch("app.services.analysis_service.GitHubService.clone_repository_safely", return_value=mock_git_repo), \
         patch("os.path.exists", return_value=True), \
         patch("app.services.intelligence_engine.IntelligenceEngine._collect_repository_source_files", return_value={
             "src/CheckoutService.java": (FIXTURE_PATH / "src" / "CheckoutService.java").read_text(encoding="utf-8")
         }):
        # Run 1
        resp1 = client.post(f"/api/investigations/{MOCK_INV_ID}/analyze")
        assert resp1.status_code == 200
        run1 = resp1.json()

        # Run 2 (Re-run Engine)
        resp2 = client.post(f"/api/investigations/{MOCK_INV_ID}/analyze")
        assert resp2.status_code == 200
        run2 = resp2.json()

    # Verify Run 2 has a new ID and is not mixing data
    assert run1["id"] != run2["id"], "Each analysis execution must create a new run ID"
    assert run2["status"] == "completed"

    # Verify Run 2 is internally consistent
    assert "875bcf7a" in run2["summary"]
    assert "Likely regression-introducing commit" in run2["summary"]
    assert run2["relevant_commits"][0]["commit_hash"] == "875bcf7a"
    assert "Likely regression-introducing commit" in run2["relevant_commits"][0]["relevance_reason"]
    assert run2["relevant_commits"][1]["commit_hash"].startswith("6d5ff2d")
    assert "Regression-detection/testing commit" in run2["relevant_commits"][1]["relevance_reason"]
    assert run2["relevant_commits"][2]["commit_hash"].startswith("2a2701b")
    assert "Baseline setup commit" in run2["relevant_commits"][2]["relevance_reason"]
    assert run2["relevant_commits"][3]["commit_hash"].startswith("24705a6")
    assert "Baseline setup commit" in run2["relevant_commits"][3]["relevance_reason"]



