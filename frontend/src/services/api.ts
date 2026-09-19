import type { BackendHealthResponse, DatabaseHealthResponse, Project } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
const TIMEOUT_MS = 5000;

/**
 * Robust fetch wrapper with hard 5-second AbortController timeout.
 * Guaranteed to resolve or abort within 5 seconds.
 */
async function fetchWithTimeout(url: string): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => {
    controller.abort();
  }, TIMEOUT_MS);

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      signal: controller.signal,
    });
    return response;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Check backend health with a hard 5-second AbortController timeout.
 */
export async function checkBackendHealth(): Promise<BackendHealthResponse> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/health`);

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * Check database health through backend with a hard 5-second AbortController timeout.
 */
export async function checkDatabaseHealth(): Promise<DatabaseHealthResponse> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/health/db`);

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * Retrieve projects from Supabase via FastAPI with a hard 5-second AbortController timeout.
 */
export async function fetchProjects(): Promise<Project[]> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/projects`);

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}`;
    try {
      const data = await response.json();
      if (data?.detail) errorDetail = data.detail;
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail);
  }

  return response.json();
}
