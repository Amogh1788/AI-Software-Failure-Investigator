import type {
  BackendHealthResponse,
  DatabaseHealthResponse,
  Project,
  Repository,
  RepositoryFile,
  RepositoryCommit,
  RepositoryDetail,
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
