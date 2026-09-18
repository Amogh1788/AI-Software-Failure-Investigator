import type { BackendHealthResponse, DatabaseHealthResponse, Project } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
const TIMEOUT_MS = 5000;

/**
 * Perform a health check against the FastAPI backend with a 5-second timeout.
 */
export async function checkBackendHealth(): Promise<BackendHealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });

  if (!response.ok) {
    throw new Error(`Backend check failed (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Perform a database health check through FastAPI with a 5-second timeout.
 */
export async function checkDatabaseHealth(): Promise<DatabaseHealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health/db`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });

  if (!response.ok) {
    throw new Error(`Database check failed (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Retrieve project records from Supabase via FastAPI with a 5-second timeout.
 */
export async function fetchProjects(): Promise<Project[]> {
  const response = await fetch(`${API_BASE_URL}/projects`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });

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
