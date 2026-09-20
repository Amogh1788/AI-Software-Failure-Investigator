import type {
  BackendHealthResponse,
  DatabaseHealthResponse,
  Project,
  Repository,
  RepositoryFile,
  RepositoryCommit,
  RepositoryDetail,
  Investigation,
  InvestigationEvidence,
  InvestigationDetail,
  CreateInvestigationPayload,
  UpdateInvestigationPayload,
  CreateEvidencePayload,
  InvestigationAnalysis,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
const DEFAULT_TIMEOUT_MS = 5000;
const ANALYZE_TIMEOUT_MS = 60000; // 60s for repository cloning and static analysis

/**
 * Robust fetch wrapper with hard AbortController timeout.
 * Guaranteed to resolve or abort within the specified timeout.
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs: number = DEFAULT_TIMEOUT_MS
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => {
    controller.abort();
  }, timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        Accept: 'application/json',
        ...(options.headers || {}),
      },
      signal: controller.signal,
    });
    return response;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Extract error detail from response safely.
 */
async function extractErrorDetail(response: Response, fallback: string): Promise<string> {
  try {
    const data = await response.json();
    if (data?.detail) return data.detail;
  } catch {
    // ignore JSON parsing failure
  }
  return `${fallback} (HTTP ${response.status})`;
}

// ==========================================
// Phase 1 API Endpoints
// ==========================================

export async function checkBackendHealth(): Promise<BackendHealthResponse> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

export async function checkDatabaseHealth(): Promise<DatabaseHealthResponse> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/health/db`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

export async function fetchProjects(): Promise<Project[]> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/projects`);
  if (!response.ok) {
    const errorMsg = await extractErrorDetail(response, 'Failed to load projects');
    throw new Error(errorMsg);
  }
  return response.json();
}

// ==========================================
// Phase 2 Repository API Endpoints
// ==========================================

/**
 * Ingest and analyze a public GitHub repository.
 */
export async function analyzeRepository(
  githubUrl: string,
  projectId?: string
): Promise<RepositoryDetail> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/repositories/analyze`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        github_url: githubUrl,
        project_id: projectId || null,
      }),
    },
    ANALYZE_TIMEOUT_MS
  );

  if (!response.ok) {
    const errorMsg = await extractErrorDetail(response, 'Repository analysis failed');
    throw new Error(errorMsg);
  }

  return response.json();
}

/**
 * List all previously analyzed repositories.
 */
export async function getRepositories(): Promise<Repository[]> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/repositories`);
  if (!response.ok) {
    const errorMsg = await extractErrorDetail(response, 'Failed to fetch repositories');
    throw new Error(errorMsg);
  }
  return response.json();
}

/**
 * Get repository summary by UUID.
 */
export async function getRepository(repositoryId: string): Promise<Repository> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/repositories/${repositoryId}`);
  if (!response.ok) {
    const errorMsg = await extractErrorDetail(response, 'Failed to fetch repository');
    throw new Error(errorMsg);
  }
  return response.json();
}

/**
 * Get files metadata for a specific repository.
 */
export async function getRepositoryFiles(repositoryId: string): Promise<RepositoryFile[]> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/repositories/${repositoryId}/files`);
  if (!response.ok) {
    const errorMsg = await extractErrorDetail(response, 'Failed to fetch repository files');
    throw new Error(errorMsg);
  }
  return response.json();
}

/**
 * Get recent Git commit history for a repository.
 */
export async function getRepositoryCommits(repositoryId: string): Promise<RepositoryCommit[]> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/repositories/${repositoryId}/commits`);
  if (!response.ok) {
    const errorMsg = await extractErrorDetail(response, 'Failed to fetch repository commits');
    throw new Error(errorMsg);
  }
  return response.json();
}

// ==========================================
// Phase 3 Investigation & Evidence API Endpoints
// ==========================================

const EVIDENCE_TIMEOUT_MS = 15000; // 15s for larger logs/traces

/**
 * Create a new investigation case linked to an analyzed repository.
 */
export async function createInvestigation(payload: CreateInvestigationPayload): Promise<Investigation> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/investigations`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
    DEFAULT_TIMEOUT_MS
  );
  if (!response.ok) {
    const errorMsg = await extractErrorDetail(response, 'Failed to create investigation');
    throw new Error(errorMsg);
  }
  return response.json();
}

/**
 * Fetch all investigation cases with evidence counts.
 */
export async function getInvestigations(): Promise<Investigation[]> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/investigations`,
    {
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        Pragma: 'no-cache',
      },
    },
    DEFAULT_TIMEOUT_MS
  );
  if (!response.ok) {
    const errorMsg = await extractErrorDetail(response, 'Failed to fetch investigations');
    throw new Error(errorMsg);
  }
  return response.json();
}

/**
 * Fetch details of a specific investigation, including repository and attached evidence.
 */
export async function getInvestigation(investigationId: string): Promise<InvestigationDetail> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/investigations/${investigationId}`,
    {
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        Pragma: 'no-cache',
      },
    },
    DEFAULT_TIMEOUT_MS
  );
  if (!response.ok) {
    const errorMsg = await extractErrorDetail(response, 'Failed to fetch investigation details');
    throw new Error(errorMsg);
  }
  return response.json();
}

/**
 * Update title, description, or status of an investigation.
 */
export async function updateInvestigation(
  investigationId: string,
  payload: UpdateInvestigationPayload
): Promise<Investigation> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/investigations/${investigationId}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
    DEFAULT_TIMEOUT_MS
  );
  if (!response.ok) {
    const errorMsg = await extractErrorDetail(response, 'Failed to update investigation');
    throw new Error(errorMsg);
  }
  return response.json();
}

/**
 * Delete an investigation case and its attached evidence.
 */
export async function deleteInvestigation(investigationId: string): Promise<void> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/investigations/${investigationId}`,
    { method: 'DELETE' },
    DEFAULT_TIMEOUT_MS
  );
  if (!response.ok) {
    const errorMsg = await extractErrorDetail(response, 'Failed to delete investigation');
    throw new Error(errorMsg);
  }
}

/**
 * Attach failure evidence to an investigation case.
 */
export async function addEvidence(
  investigationId: string,
  payload: CreateEvidencePayload
): Promise<InvestigationEvidence> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/investigations/${investigationId}/evidence`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
    EVIDENCE_TIMEOUT_MS
  );
  if (!response.ok) {
    const errorMsg = await extractErrorDetail(response, 'Failed to attach evidence');
    throw new Error(errorMsg);
  }
  return response.json();
}

/**
 * Fetch all evidence items for an investigation.
 */
export async function getInvestigationEvidence(investigationId: string): Promise<InvestigationEvidence[]> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/investigations/${investigationId}/evidence`);
  if (!response.ok) {
    const errorMsg = await extractErrorDetail(response, 'Failed to fetch evidence items');
    throw new Error(errorMsg);
  }
  return response.json();
}

/**
 * Delete a single evidence item.
 */
export async function deleteEvidence(investigationId: string, evidenceId: string): Promise<void> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/investigations/${investigationId}/evidence/${evidenceId}`,
    { method: 'DELETE' },
    DEFAULT_TIMEOUT_MS
  );
  if (!response.ok) {
    const errorMsg = await extractErrorDetail(response, 'Failed to delete evidence item');
    throw new Error(errorMsg);
  }
}

// ====================================================================
// Phase 4 — Investigation Intelligence Engine APIs
// ====================================================================

/**
 * Execute Phase 4 analysis on a ready investigation.
 */
export async function analyzeInvestigation(investigationId: string): Promise<InvestigationAnalysis> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/investigations/${investigationId}/analyze`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    },
    ANALYZE_TIMEOUT_MS
  );
  if (!response.ok) {
    const errorMsg = await extractErrorDetail(response, 'Investigation analysis failed');
    throw new Error(errorMsg);
  }
  return response.json();
}

/**
 * Fetch latest analysis results for an investigation.
 */
export async function getInvestigationAnalysis(investigationId: string): Promise<InvestigationAnalysis> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/investigations/${investigationId}/analysis`,
    {
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        Pragma: 'no-cache',
      },
    },
    DEFAULT_TIMEOUT_MS
  );
  if (!response.ok) {
    const errorMsg = await extractErrorDetail(response, 'Failed to fetch investigation analysis');
    throw new Error(errorMsg);
  }
  return response.json();
}

/**
 * Fetch all historical analysis runs for an investigation.
 */
export async function listAnalysisRuns(investigationId: string): Promise<InvestigationAnalysis[]> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/investigations/${investigationId}/analysis/runs`,
    {},
    DEFAULT_TIMEOUT_MS
  );
  if (!response.ok) {
    const errorMsg = await extractErrorDetail(response, 'Failed to fetch analysis runs');
    throw new Error(errorMsg);
  }
  return response.json();
}

