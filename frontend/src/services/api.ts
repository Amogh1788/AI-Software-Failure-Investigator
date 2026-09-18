import type { BackendHealthResponse, DatabaseHealthResponse, Project } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

/**
 * Sanitize low-level system, socket, or network errors into concise, user-friendly messages.
 * Keeps full diagnostic details logged in the browser console for developer inspection.
 */
export function sanitizeErrorMessage(err: unknown, fallbackMessage: string): string {
  // Always log raw error to console for developer diagnostics
  console.error('[API Diagnostic Error]:', err);

  if (!err) return fallbackMessage;

  const raw = typeof err === 'string' ? err : (err as any)?.message || String(err);

  // Check for raw low-level Windows socket or connection errors (e.g. WinError 10035, 10061, ECONNREFUSED)
  if (
    /WinError|socket|10035|10061|ECONNREFUSED|ETIMEDOUT|ENOTFOUND|ERR_CONNECTION_REFUSED/i.test(raw)
  ) {
    return 'Unable to refresh projects. Please try again.';
  }

  // Check for standard browser fetch network errors
  if (/Failed to fetch|NetworkError|Load failed/i.test(raw)) {
    return 'Unable to connect to backend server. Please ensure FastAPI is running on port 8000.';
  }

  // If the backend returned an actionable configuration detail
  if (raw.includes('Database connection is not configured') || raw.includes('SUPABASE_URL')) {
    return 'Database connection is not configured. Ensure SUPABASE_URL and SUPABASE_ANON_KEY are set in backend/.env.';
  }

  // Check for raw Python tracebacks or internal 500 errors
  if (/Traceback|Internal Server Error/i.test(raw)) {
    return 'An internal server error occurred while retrieving data. Please check backend logs.';
  }

  // If the message is excessively long or contains unformatted dumps, return concise fallback
  if (raw.length > 180) {
    return fallbackMessage;
  }

  return raw;
}

/**
 * Perform a real health check against the FastAPI backend.
 */
export async function checkBackendHealth(): Promise<BackendHealthResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });
  } catch (netErr) {
    throw new Error(sanitizeErrorMessage(netErr, 'Unable to connect to FastAPI backend.'));
  }

  if (!response.ok) {
    throw new Error(`Backend health check failed: HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * Perform a real database health check through FastAPI to Supabase PostgreSQL.
 */
export async function checkDatabaseHealth(): Promise<DatabaseHealthResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/health/db`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });
  } catch (netErr) {
    throw new Error(sanitizeErrorMessage(netErr, 'Unable to probe database through backend.'));
  }

  if (!response.ok) {
    throw new Error(`Database health check failed: HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * Retrieve project records from Supabase via FastAPI backend.
 */
export async function fetchProjects(): Promise<Project[]> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/projects`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });
  } catch (netErr) {
    throw new Error(sanitizeErrorMessage(netErr, 'Unable to refresh projects. Please try again.'));
  }

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}`;
    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        errorDetail = errorJson.detail;
      }
    } catch {
      // ignore json parse failure
    }
    throw new Error(sanitizeErrorMessage(errorDetail, 'Unable to refresh projects. Please try again.'));
  }

  return response.json();
}
