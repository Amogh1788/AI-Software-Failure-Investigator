import type { BackendHealthResponse, DatabaseHealthResponse, Project } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

/**
 * Perform a real health check against the FastAPI backend.
 */
export async function checkBackendHealth(): Promise<BackendHealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Backend health check failed: HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * Perform a real database health check through FastAPI to Supabase PostgreSQL.
 */
export async function checkDatabaseHealth(): Promise<DatabaseHealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health/db`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Database health check failed: HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * Retrieve project records from Supabase via FastAPI backend.
 */
export async function fetchProjects(): Promise<Project[]> {
  const response = await fetch(`${API_BASE_URL}/projects`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}`;
    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        errorDetail = errorJson.detail;
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail);
  }

  return response.json();
}
