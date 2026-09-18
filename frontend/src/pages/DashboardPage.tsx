import React, { useEffect, useState, useCallback, useRef } from 'react';
import { SystemStatus } from '../components/SystemStatus';
import { ProjectsList } from '../components/ProjectsList';
import { FutureInvestigationArea } from '../components/FutureInvestigationArea';
import { checkBackendHealth, checkDatabaseHealth, fetchProjects, sanitizeErrorMessage } from '../services/api';
import type { Project, SystemStatusState } from '../types';

interface DashboardPageProps {
  registerRefresh: (fn: () => void) => void;
  setIsRefreshingHeader: (val: boolean) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  registerRefresh,
  setIsRefreshingHeader,
}) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isInitialProjectsLoading, setIsInitialProjectsLoading] = useState<boolean>(true);
  const [isProjectsRefreshing, setIsProjectsRefreshing] = useState<boolean>(false);
  const [isHealthRefreshing, setIsHealthRefreshing] = useState<boolean>(false);
  const [projectsError, setProjectsError] = useState<string | null>(null);
  const [projectsWarning, setProjectsWarning] = useState<string | null>(null);

  // Concurrency guard refs to prevent overlapping asynchronous requests
  const hasInitializedRef = useRef<boolean>(false);
  const isRefreshingHealthRef = useRef<boolean>(false);
  const isRefreshingProjectsRef = useRef<boolean>(false);
  const isRefreshingAllRef = useRef<boolean>(false);
  const projectsRef = useRef<Project[]>([]);
  projectsRef.current = projects;

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
      details: 'Verifying Supabase PostgreSQL probe...',
    },
  });

  const performHealthChecks = useCallback(async () => {
    // Prevent overlapping health check requests
    if (isRefreshingHealthRef.current) return;
    isRefreshingHealthRef.current = true;
    setIsHealthRefreshing(true);

    // ONLY on initial page load do we transition cards to "Checking..."
    // On subsequent refreshes, we preserve the current Connected/Disconnected cards
    if (!hasInitializedRef.current) {
      setSystemStatus((prev) => ({
        ...prev,
        backend: { status: 'checking', label: 'Checking...', details: 'Probing GET /api/health...' },
        database: { status: 'checking', label: 'Checking...', details: 'Probing database via backend...' },
      }));
    }

    let backendOk = false;

    // 1. Probe Backend
    try {
      const backendRes = await checkBackendHealth();
      backendOk = backendRes.status === 'ok';
      setSystemStatus((prev) => ({
        ...prev,
        backend: {
          status: backendOk ? 'connected' : 'disconnected',
          label: backendOk ? 'Connected' : 'Disconnected',
          details: `Service: ${backendRes.service} (HTTP 200)`,
        },
      }));
    } catch (err: any) {
      const sanitized = sanitizeErrorMessage(err, 'Cannot reach FastAPI backend.');
      setSystemStatus((prev) => ({
        ...prev,
        backend: {
          status: 'disconnected',
          label: 'Disconnected',
          details: sanitized,
        },
        database: {
          status: 'disconnected',
          label: 'Disconnected',
          details: 'Backend unreachable (database probe suspended)',
        },
      }));
      isRefreshingHealthRef.current = false;
      setIsHealthRefreshing(false);
      hasInitializedRef.current = true;
      return;
    }

    // 2. Probe Database through Backend
    if (backendOk) {
      try {
        const dbRes = await checkDatabaseHealth();
        const isDbConnected = dbRes.status === 'connected';
        setSystemStatus((prev) => ({
          ...prev,
          database: {
            status: isDbConnected ? 'connected' : 'disconnected',
            label: isDbConnected ? 'Connected' : 'Disconnected',
            details: dbRes.message,
          },
        }));
      } catch (err: any) {
        const sanitized = sanitizeErrorMessage(err, 'Supabase PostgreSQL connection failed');
        setSystemStatus((prev) => ({
          ...prev,
          database: {
            status: 'disconnected',
            label: 'Disconnected',
            details: sanitized,
          },
        }));
      }
    }

    isRefreshingHealthRef.current = false;
    setIsHealthRefreshing(false);
    hasInitializedRef.current = true;
  }, []);

  const loadProjects = useCallback(async () => {
    // Prevent overlapping project fetch requests
    if (isRefreshingProjectsRef.current) return;
    isRefreshingProjectsRef.current = true;
    setIsProjectsRefreshing(true);

    try {
      const data = await fetchProjects();
      setProjects(data);
      setProjectsError(null);
      setProjectsWarning(null);
    } catch (err: any) {
      const sanitizedMsg = sanitizeErrorMessage(
        err,
        'Unable to refresh projects. Please try again.'
      );

      // If we already have valid projects loaded, preserve them and show non-blocking warning
      if (projectsRef.current.length > 0) {
        setProjectsWarning('Refresh failed. Showing last successfully loaded data.');
        setProjectsError(null);
      } else {
        // If projects have never successfully loaded, show the large initial setup/error card
        setProjectsError(sanitizedMsg);
        setProjectsWarning(null);
      }
    } finally {
      setIsInitialProjectsLoading(false);
      isRefreshingProjectsRef.current = false;
      setIsProjectsRefreshing(false);
    }
  }, []);

  const refreshAll = useCallback(async () => {
    if (isRefreshingAllRef.current) return;
    isRefreshingAllRef.current = true;
    setIsRefreshingHeader(true);

    await Promise.allSettled([performHealthChecks(), loadProjects()]);

    isRefreshingAllRef.current = false;
    setIsRefreshingHeader(false);
  }, [performHealthChecks, loadProjects, setIsRefreshingHeader]);

  useEffect(() => {
    registerRefresh(refreshAll);
    refreshAll();
  }, [registerRefresh, refreshAll]);

  return (
    <div className="space-y-8 pb-12">
      {/* Real-time System Status Section */}
      <SystemStatus
        status={systemStatus}
        isRefreshing={isHealthRefreshing}
        onRetry={performHealthChecks}
      />

      {/* Projects Section */}
      <ProjectsList
        projects={projects}
        isInitialLoading={isInitialProjectsLoading}
        isRefreshing={isProjectsRefreshing}
        error={projectsError}
        warning={projectsWarning}
        onRefresh={loadProjects}
      />

      {/* Future Investigation Engine Area */}
      <FutureInvestigationArea />
    </div>
  );
};
