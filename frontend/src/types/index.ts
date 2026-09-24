export type ConnectionState = 'connected' | 'disconnected' | 'checking';

export interface Project {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
}

export interface BackendHealthResponse {
  status: string;
  service: string;
}

export interface DatabaseHealthResponse {
  status: 'connected' | 'disconnected';
  database: string;
  message: string;
}

export interface StatusCardInfo {
  status: ConnectionState;
  label: string;
  details?: string;
  isRefreshing?: boolean;
}

export interface SystemStatusState {
  frontend: StatusCardInfo;
  backend: StatusCardInfo;
  database: StatusCardInfo;
}

// Phase 2 Repository Interfaces
export interface Repository {
  id: string;
  project_id: string | null;
  github_url: string;
  owner: string;
  name: string;
  default_branch: string | null;
  description: string | null;
  primary_language: string | null;
  total_files: number;
  source_files: number;
  status?: string;
  error_message?: string | null;
  analyzed_at: string;
  created_at: string;
}

export interface RepositoryFile {
  id: string;
  repository_id: string;
  path: string;
  extension: string | null;
  language: string | null;
  file_size: number;
  lines_of_code: number;
  is_source_file: boolean;
  created_at: string;
}

export interface RepositoryCommit {
  id: string;
  repository_id: string;
  commit_hash: string;
  author_name: string | null;
  author_email: string | null;
  commit_message: string | null;
  committed_at: string | null;
  files_changed: number;
  created_at?: string;
}

export interface RepositoryDetail {
  repository: Repository;
  files: RepositoryFile[];
  commits: RepositoryCommit[];
  language_breakdown: Record<string, number>;
}

export interface FileTreeNode {
  name: string;
  path: string;
  isDirectory: boolean;
  children?: FileTreeNode[];
  file?: RepositoryFile;
}

// Phase 3 Investigation & Evidence Interfaces
export type InvestigationStatus = 'draft' | 'ready' | 'analyzing' | 'completed';
export type EvidenceType = 'bug_report' | 'application_log' | 'stack_trace' | 'test_output';

export interface Investigation {
  id: string;
  repository_id: string;
  title: string;
  description: string | null;
  status: InvestigationStatus;
  evidence_count: number;
  created_at: string;
  updated_at: string;
  repository?: Repository | null;
}

export interface InvestigationEvidence {
  id: string;
  investigation_id: string;
  evidence_type: EvidenceType;
  title: string | null;
  content: string;
  filename: string | null;
  byte_size: number;
  created_at: string;
}

export interface InvestigationDetail {
  investigation: Investigation;
  repository: Repository | null;
  evidence: InvestigationEvidence[];
}

export interface CreateInvestigationPayload {
  repository_id: string;
  title: string;
  description?: string | null;
}

export interface UpdateInvestigationPayload {
  title?: string;
  description?: string | null;
  status?: InvestigationStatus;
}

export interface CreateEvidencePayload {
  evidence_type: EvidenceType;
  title?: string | null;
  content: string;
  filename?: string | null;
}

// Phase 4 Investigation Intelligence Engine Interfaces
export type EvidenceStrength = 'high' | 'moderate' | 'low';

export interface CandidateSignals {
  stack_trace_score: number;
  test_failure_score: number;
  logs_score: number;
  bug_report_score: number;
  git_recency_score: number;
  final_score?: number;
}

export interface FailureCandidate {
  file_path: string;
  function_name?: string | null;
  method_name?: string | null;
  line_number?: number | null;
  evidence_score: number;
  evidence_strength: EvidenceStrength;
  supporting_evidence: string[];
  signals: CandidateSignals;
}

export interface FailureChainStep {
  step_number: number;
  phase: string;
  title: string;
  description: string;
  source: string;
  location?: string | null;
}

export interface RelevantCommit {
  commit_hash: string;
  author_name?: string | null;
  committed_at?: string | null;
  commit_message: string;
  relevance_reason: string;
}

export interface EvidenceSignalsSummary {
  stack_trace_signal: number;
  test_failure_signal: number;
  logs_tfidf_signal: number;
  bug_report_tfidf_signal: number;
  git_history_signal: number;
  score_formula: string;
  score_disclaimer: string;
}

export interface InvestigationAnalysis {
  id: string;
  investigation_id: string;
  engine_version: string;
  status: string;
  summary: string;
  failure_chain: FailureChainStep[];
  ranked_candidates: FailureCandidate[];
  relevant_commits: RelevantCommit[];
  evidence_signals: EvidenceSignalsSummary;
  run_duration_ms: number;
  created_at: string;
}


