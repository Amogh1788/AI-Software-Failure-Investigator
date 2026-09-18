import React, { useEffect, useState, useCallback, useRef } from 'react';
import { SystemStatus } from '../components/SystemStatus';
import { ProjectsList } from '../components/ProjectsList';
import { FutureInvestigationArea } from '../components/FutureInvestigationArea';
import { checkBackendHealth, checkDatabaseHealth, fetchProjects } from '../services/api';
import type { Project, SystemStatusState, StatusCardInfo } from '../types';

interface DashboardPageProps {
  registerRefresh: (fn: () => void) => void;
  setIsRefreshingHeader: (val: boolean) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  registerRefresh,
  setIsRefreshingHeader,
}) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isProjectsLoading, setIsProjectsLoading] = useState<boolean>(true);
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

  // Guard refs to prevent duplicate/overlapping requests
  const isRefreshingProjectsRef = useRef<boolean>(false);
  const isCheckingConnectivityRef = useRef<boolean>(false);
  const projectsCountRef = useRef<number>(0);
  projectsCountRef.current = projects.length;

  /**
   * Check Backend and Database connectivity in parallel.
   * Only this function updates the backend/database cards to Checking... state.
   */
  const checkConnectivity = useCallback(async () => {
    if (isCheckingConnectivityRef.current) return;
    isCheckingConnectivityRef.current = true;
    setIsCheckingConnectivity(true);

    setSystemStatus((prev) => ({
      ...prev,
      backend: { status: 'checking', label: 'Checking...', details: 'Probing GET /api/health...' },
      database: { status: 'checking', label: 'Checking...', details: 'Probing GET /api/health/db...' },
    }));

    // Run health checks in parallel
    const [backendResult, dbResult] = await Promise.allSettled([
      checkBackendHealth(),
      checkDatabaseHealth(),
    ]);

    let newBackendState: StatusCardInfo;
    if (backendResult.status === 'fulfilled' && backendResult.value.status === 'ok') {
      newBackendState = {
        status: 'connected',
        label: 'Connected',
        details: `Service: ${backendResult.value.service} (HTTP 200)`,
      };
    } else {
      newBackendState = {
        status: 'disconnected',
        label: 'Disconnected',
        details: 'Cannot connect to FastAPI backend server',
      };
    }

    let newDbState: StatusCardInfo;
    if (dbResult.status === 'fulfilled' && dbResult.value.status === 'connected') {
      newDbState = {
        status: 'connected',
        label: 'Connected',
        details: dbResult.value.message || 'Supabase PostgreSQL connected',
      };
    } else {
      const reason =
        dbResult.status === 'fulfilled'
          ? dbResult.value.message
          : 'Database connection failed';
      newDbState = {
        status: 'disconnected',
        label: 'Disconnected',
        details: reason,
      };
    }

    setSystemStatus((prev) => ({
      ...prev,
      backend: newBackendState,
      database: newDbState,
    }));

    isCheckingConnectivityRef.current = false;
    setIsCheckingConnectivity(false);
  }, []);

  /**
   * Refresh projects only (GET /api/projects).
   * Does NOT touch backend/database status cards or set them to Checking.
   * Keeps existing project list visible while updating.
   */
  const refreshProjects = useCallback(async () => {
    if (isRefreshingProjectsRef.current) return;
    isRefreshingProjectsRef.current = true;
    setIsProjectsRefreshing(true);
    setIsRefreshingHeader(true);

    try {
      const data = await fetchProjects();
      setProjects(data);
      setProjectsError(null);
      setProjectsWarning(null);
    } catch {
      // If previous project data exists, keep it visible and show small non-blocking message
      if (projectsCountRef.current > 0) {
        setProjectsWarning('Unable to refresh projects. Showing previous data.');
      } else {
        setProjectsError('Unable to retrieve projects from backend.');
      }
    } finally {
      setIsProjectsLoading(false);
      isRefreshingProjectsRef.current = false;
      setIsProjectsRefreshing(false);
      setIsRefreshingHeader(false);
    }
  }, [setIsRefreshingHeader]);

  // Initial load: run connectivity checks and project fetch in parallel
  useEffect(() => {
    registerRefresh(refreshProjects);
    Promise.allSettled([checkConnectivity(), refreshProjects()]);
  }, [registerRefresh, checkConnectivity, refreshProjects]);

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
        isInitialLoading={isProjectsLoading}
        isRefreshing={isProjectsRefreshing}
        error={projectsError}
        warning={projectsWarning}
        onRefresh={refreshProjects}
      />

      {/* Future Investigation Engine Area */}
      <FutureInvestigationArea />
    </div>
  );
};
