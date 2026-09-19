from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class EvidenceStrength(str, Enum):
    """
    Categorical rating of evidence strength.
    Evidence score is a weighted measure of supporting evidence and is not a probability.
    """
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


class CandidateSignals(BaseModel):
    """
    Normalized [0, 1] component signals contributing to the candidate's evidence score.
    Formula:
      evidence_score =
        0.35 * stack_trace_score +
        0.25 * test_failure_score +
        0.20 * logs_score +
        0.10 * bug_report_score +
        0.10 * git_recency_score
    """
    stack_trace_score: float = Field(0.0, ge=0.0, le=1.0, description="Stack trace match signal [0, 1]")
    test_failure_score: float = Field(0.0, ge=0.0, le=1.0, description="Test failure correlation signal [0, 1]")
    logs_score: float = Field(0.0, ge=0.0, le=1.0, description="TF-IDF log text similarity signal [0, 1]")
    bug_report_score: float = Field(0.0, ge=0.0, le=1.0, description="TF-IDF bug report text similarity signal [0, 1]")
    git_recency_score: float = Field(0.0, ge=0.0, le=1.0, description="Git commit recency/touch signal [0, 1]")
    final_score: float = Field(0.0, ge=0.0, le=1.0, description="Weighted evidence score [0, 1]")


class FailureCandidate(BaseModel):
    """
    Ranked code location identified by multi-source evidence correlation.
    Evidence score is a weighted measure of supporting evidence and is not a probability.
    """
    file_path: str = Field(..., description="Repository-relative file path")
    function_name: Optional[str] = Field(None, description="Suspect function or method name")
    line_number: Optional[int] = Field(None, description="Suspect line number if pinpointed")
    evidence_score: float = Field(..., ge=0.0, le=1.0, description="Weighted evidence score [0, 1]")
    evidence_strength: EvidenceStrength = Field(..., description="Evidence strength rating ('high', 'moderate', 'low')")
    supporting_evidence: List[str] = Field(default_factory=list, description="Itemized explainable justifications")
    signals: CandidateSignals = Field(..., description="Normalized breakdown of individual evidence signals")

    model_config = ConfigDict(from_attributes=True)


class FailureChainStep(BaseModel):
    """A single step in the reconstructed temporal/causal failure progression."""
    step_number: int = Field(..., description="Sequential position in the chain (1-indexed)")
    phase: str = Field(..., description="Phase label (e.g. 'Trigger', 'Entrypoint', 'Fault Location', 'Exception', 'Test Failure')")
    title: str = Field(..., description="Brief step title")
    description: str = Field(..., description="Detailed description of what occurred at this step")
    source: str = Field(..., description="Evidence source (e.g. 'Bug Report', 'Application Logs', 'Stack Trace', 'Test Output')")
    location: Optional[str] = Field(None, description="Code location or endpoint (e.g. 'CheckoutService.java:31')")


class RelevantCommit(BaseModel):
    """A Git commit correlated with the candidate files or incident description."""
    commit_hash: str = Field(..., description="Full or abbreviated commit SHA")
    author_name: Optional[str] = Field(None, description="Commit author")
    committed_at: Optional[str] = Field(None, description="Commit timestamp")
    commit_message: str = Field(..., description="Commit message headline")
    relevance_reason: str = Field(..., description="Explanation of why this commit is correlated with the failure")


class EvidenceSignalsSummary(BaseModel):
    """Aggregate signal strengths across the entire investigation evidence corpus."""
    stack_trace_signal: float = Field(0.0, ge=0.0, le=1.0)
    test_failure_signal: float = Field(0.0, ge=0.0, le=1.0)
    logs_tfidf_signal: float = Field(0.0, ge=0.0, le=1.0)
    bug_report_tfidf_signal: float = Field(0.0, ge=0.0, le=1.0)
    git_history_signal: float = Field(0.0, ge=0.0, le=1.0)
    score_formula: str = Field(
        "evidence_score = 0.35 * stack_trace + 0.25 * test_failure + 0.20 * logs + 0.10 * bug_report + 0.10 * git_recency",
        description="Explicit mathematical formula used to compute evidence score"
    )
    score_disclaimer: str = Field(
        "Evidence score is a weighted measure of supporting evidence and is not a probability.",
        description="Mandatory score interpretation notice"
    )


class InvestigationAnalysisResponse(BaseModel):
    """Complete Investigation Intelligence Engine v1 analysis report."""
    id: str = Field(..., description="Analysis run UUID")
    investigation_id: str = Field(..., description="Associated investigation UUID")
    engine_version: str = Field("1.0.0", description="Intelligence engine version")
    status: str = Field("completed", description="Run status ('completed' or 'failed')")
    summary: str = Field(..., description="Explainable executive summary of the investigation findings")
    failure_chain: List[FailureChainStep] = Field(default_factory=list, description="Probable causal failure chain")
    ranked_candidates: List[FailureCandidate] = Field(default_factory=list, description="Ranked failure candidate files and functions")
    relevant_commits: List[RelevantCommit] = Field(default_factory=list, description="Correlated recent Git commits")
    evidence_signals: EvidenceSignalsSummary = Field(..., description="Aggregate multi-source signal breakdown")
    run_duration_ms: int = Field(0, description="Execution time in milliseconds")
    created_at: str = Field(..., description="Analysis completion timestamp")

    model_config = ConfigDict(from_attributes=True)
