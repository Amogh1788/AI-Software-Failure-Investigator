import React, { useEffect, useState, useCallback, useRef } from 'react';
import { SystemStatus } from '../components/SystemStatus';
import { ProjectsList } from '../components/ProjectsList';
import { RepositoryAnalyzer } from '../components/RepositoryAnalyzer';
import { InvestigationManager } from '../components/InvestigationManager';
import { FutureInvestigationArea } from '../components/FutureInvestigationArea';
import { checkBackendHealth, checkDatabaseHealth, fetchProjects } from '../services/api';
import type { Project, SystemStatusState } from '../types';

interface DashboardPageProps {
  registerRefresh: (fn: () => void) => void;
  onProjectsRefreshingChange?: (isRefreshing: boolean) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  registerRefresh,
  onProjectsRefreshingChange,
}) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isProjectsInitialLoading, setIsProjectsInitialLoading] = useState<boolean>(true);
  const [isProjectsRefreshing, setIsProjectsRefreshing] = useState<boolean>(false);
  const [projectsError, setProjectsError] = useState<string | null>(null);
  const [projectsWarning, setProjectsWarning] = useState<string | null>(null);

  const [isCheckingConnectivity, setIsCheckingConnectivity] = useState<boolean>(false);
  const [systemStatus, setSystemStatus] = useState<SystemStatusState>({
    frontend: {
      status: 'connected',
      label: 'Connected',
      details: 'Active React client session',
    },
    backend: {
      status: 'checking',
      label: 'Checking...',
      details: 'Connecting to FastAPI...',
    },
    database: {
      status: 'checking',
      label: 'Checking...',
      details: 'Verifying Supabase PostgreSQL...',
    },
  });

  // Guard refs to prevent duplicate requests
  const isRefreshingProjectsRef = useRef<boolean>(false);
  const isCheckingConnectivityRef = useRef<boolean>(false);
  const projectsRef = useRef<Project[]>([]);
  projectsRef.current = projects;

  /**
   * Probe Backend Health independently with 5s timeout.
   */
  const checkBackend = async () => {
    setSystemStatus((prev) => ({
      ...prev,
      backend: { status: 'checking', label: 'Checking...', details: 'Connecting to FastAPI...' },
    }));

    try {
      const res = await checkBackendHealth();
      if (res.status === 'ok') {
        setSystemStatus((prev) => ({
          ...prev,
          backend: {
            status: 'connected',
            label: 'Connected',
            details: `Service: ${res.service} (HTTP 200)`,
          },
        }));
      } else {
        setSystemStatus((prev) => ({
          ...prev,
          backend: {
            status: 'disconnected',
            label: 'Disconnected',
            details: 'Backend returned unexpected status',
          },
        }));
      }
    } catch (err: any) {
      const isTimeout = err?.name === 'AbortError';
      setSystemStatus((prev) => ({
        ...prev,
        backend: {
          status: 'disconnected',
          label: 'Disconnected',
          details: isTimeout ? 'Connection timed out (5s)' : 'Cannot reach FastAPI backend server',
        },
      }));
    }
  };

  /**
   * Probe Database Health independently with 5s timeout.
   */
  const checkDatabase = async () => {
    setSystemStatus((prev) => ({
      ...prev,
      database: { status: 'checking', label: 'Checking...', details: 'Verifying Supabase PostgreSQL...' },
    }));

    try {
      const res = await checkDatabaseHealth();
      if (res.status === 'connected') {
        setSystemStatus((prev) => ({
          ...prev,
          database: {
            status: 'connected',
            label: 'Connected',
            details: res.message || 'Supabase PostgreSQL connected',
          },
        }));
      } else {
        setSystemStatus((prev) => ({
          ...prev,
          database: {
            status: 'disconnected',
            label: 'Disconnected',
            details: res.message || 'Database disconnected',
          },
        }));
      }
    } catch (err: any) {
      const isTimeout = err?.name === 'AbortError';
      setSystemStatus((prev) => ({
        ...prev,
        database: {
          status: 'disconnected',
          label: 'Disconnected',
          details: isTimeout ? 'Connection timed out (5s)' : 'Database connection check failed',
        },
      }));
    }
  };

  /**
   * Dedicated connectivity check (Backend + Database in parallel).
   * Only this action modifies Backend and Database status cards.
   */
  const checkConnectivity = useCallback(async () => {
    if (isCheckingConnectivityRef.current) return;
    isCheckingConnectivityRef.current = true;
    setIsCheckingConnectivity(true);

    try {
      await Promise.allSettled([checkBackend(), checkDatabase()]);
    } finally {
      isCheckingConnectivityRef.current = false;
      setIsCheckingConnectivity(false);
    }
  }, []);

  /**
   * Refresh projects only (GET /api/projects).
   * Does NOT touch backend or database status.
   * Does NOT activate global loading state.
   * Guaranteed to clear loading state in finally.
   */
  const refreshProjects = useCallback(async () => {
    if (isRefreshingProjectsRef.current) return;
    isRefreshingProjectsRef.current = true;
    setIsProjectsRefreshing(true);
    onProjectsRefreshingChange?.(true);

    try {
      const data = await fetchProjects();
      setProjects(data);
      setProjectsError(null);
      setProjectsWarning(null);
    } catch (err: any) {
      console.error('Projects refresh failed:', err);
      if (projectsRef.current.length > 0) {
        setProjectsWarning('Unable to refresh projects. Showing previous data.');
      } else {
        const isTimeout = err?.name === 'AbortError';
        setProjectsError(
          isTimeout
            ? 'Request timed out (5s). Ensure FastAPI is running on port 8000.'
            : 'Unable to retrieve projects from backend.'
        );
      }
    } finally {
      setIsProjectsInitialLoading(false);
      isRefreshingProjectsRef.current = false;
      setIsProjectsRefreshing(false);
      onProjectsRefreshingChange?.(false);
    }
  }, [onProjectsRefreshingChange]);

  // Keep registered refresh callback updated without re-running mount requests
  useEffect(() => {
    registerRefresh(refreshProjects);
  }, [registerRefresh, refreshProjects]);

  // Run on first load only: connectivity and projects in parallel
  useEffect(() => {
    Promise.allSettled([checkConnectivity(), refreshProjects()]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-8 pb-12">
      {/* Real-time System Status Section */}
      <SystemStatus
        status={systemStatus}
        isChecking={isCheckingConnectivity}
        onCheckConnectivity={checkConnectivity}
      />

      {/* Projects Section */}
      <ProjectsList
        projects={projects}
        isInitialLoading={isProjectsInitialLoading}
        isRefreshing={isProjectsRefreshing}
        error={projectsError}
        warning={projectsWarning}
        onRefresh={refreshProjects}
      />

      {/* Phase 2: Repository Ingestion & Codebase Analysis */}
      <RepositoryAnalyzer />

      {/* Phase 3: Investigation Cases & Failure Evidence Collection */}
      <InvestigationManager />

      {/* Future Investigation Engine Area */}
      <FutureInvestigationArea />
    </div>
  );
};
