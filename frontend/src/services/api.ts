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
export const ANALYZE_TIMEOUT_MS = 330000; // 330s (5.5m) to allow backend 300s clone timeout to complete
const RETRY_DELAY_MS = 500;

export const TIMEOUT_ERROR_MESSAGE =
  'Repository analysis timed out. The repository may be too large or complex to analyze within the current processing limit.';

let currentAuthToken: string | null = null;

/**
 * Register or update the current Supabase access token for authenticated API requests.
 */
export function setAuthToken(token: string | null): void {
  currentAuthToken = token;
}

export function getAuthToken(): string | null {
  return currentAuthToken;
}

/**
 * Robust fetch wrapper with hard AbortController timeout,
 * JWT Authorization header injection, and single-retry for idempotent GET requests.
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs: number = DEFAULT_TIMEOUT_MS,
  isRetry: boolean = false
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => {
    controller.abort();
  }, timeoutMs);

  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  // Attach Supabase JWT Authorization header if available and not already provided
  if (currentAuthToken && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${currentAuthToken}`;
  }

  const isGet = !options.method || options.method.toUpperCase() === 'GET';

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });

    // If idempotent GET request returned a transient gateway error (502/503), retry once
    if (!isRetry && isGet && (response.status === 502 || response.status === 503)) {
      await new Promise((r) => setTimeout(r, RETRY_DELAY_MS));
      return fetchWithTimeout(url, options, timeoutMs, true);
    }

    return response;
  } catch (err: unknown) {
    // Retry once on network error for idempotent GET only
    if (!isRetry && isGet) {
      await new Promise((r) => setTimeout(r, RETRY_DELAY_MS));
      return fetchWithTimeout(url, options, timeoutMs, true);
    }
    // Transform browser abort / timeout into a user-friendly error instead of raw "signal is aborted without reason"
    if (
      err instanceof Error &&
      (err.name === 'AbortError' ||
        err.message.includes('aborted') ||
        err.message.includes('signal is aborted'))
    ) {
      throw new Error(TIMEOUT_ERROR_MESSAGE);
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Extract error detail from response safely, capturing X-Request-ID and specialized status codes.
 */
export async function extractErrorDetail(response: Response, fallback: string): Promise<string> {
  const requestId = response.headers.get('X-Request-ID');
  const reqSuffix = requestId ? ` (Request ID: ${requestId})` : '';

  if (response.status === 401) {
    return `Authentication required or session expired.${reqSuffix}`;
  }
  if (response.status === 403) {
    return `Access forbidden: You do not have permission for this resource.${reqSuffix}`;
  }
  if (response.status === 429) {
    const retryAfter = response.headers.get('Retry-After');
    const waitMsg = retryAfter ? ` Please retry in ${retryAfter}s.` : ' Please wait before retrying.';
    return `Rate limit reached.${waitMsg}${reqSuffix}`;
  }
  if (response.status === 504) {
    return TIMEOUT_ERROR_MESSAGE;
  }

  try {
    const data = await response.json();
    if (data?.detail) return `${data.detail}${reqSuffix}`;
  } catch {
    // ignore JSON parsing failure
  }
  return `${fallback} (HTTP ${response.status})${reqSuffix}`;
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
 * Ingest and analyze a public GitHub repository. Requires authentication.
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
 * Remove a repository from the authenticated user's history dropdown.
 */
export async function deleteRepositoryHistory(repositoryId: string): Promise<void> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/repositories/${repositoryId}/history`,
    {
      method: 'DELETE',
    }
  );
  if (!response.ok) {
    const errorMsg = await extractErrorDetail(response, 'Failed to delete repository from history');
    throw new Error(errorMsg);
  }
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
 * Fetch all investigation cases for authenticated user with evidence counts.
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
 * Fetch all evidence items for an authorized investigation.
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
