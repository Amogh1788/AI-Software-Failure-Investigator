import React, { useEffect, useState, useCallback } from 'react';
import { SystemStatus } from '../components/SystemStatus';
import { ProjectsList } from '../components/ProjectsList';
import { FutureInvestigationArea } from '../components/FutureInvestigationArea';
import { checkBackendHealth, checkDatabaseHealth, fetchProjects } from '../services/api';
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
  const [projectsLoading, setProjectsLoading] = useState<boolean>(true);
  const [projectsError, setProjectsError] = useState<string | null>(null);

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
    // 1. Frontend is always connected in an active browser session
    setSystemStatus((prev) => ({
      ...prev,
      backend: { status: 'checking', label: 'Checking...', details: 'Probing GET /api/health...' },
      database: { status: 'checking', label: 'Checking...', details: 'Probing database via backend...' },
    }));

    let backendOk = false;

    // 2. Check Backend Health
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
      setSystemStatus((prev) => ({
        ...prev,
        backend: {
          status: 'disconnected',
          label: 'Disconnected',
          details: err.message || 'Cannot reach FastAPI server',
        },
        database: {
          status: 'disconnected',
          label: 'Disconnected',
          details: 'Backend unreachable (database probe suspended)',
        },
      }));
      return;
    }

    // 3. Check Database Health (only if backend is up)
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
        setSystemStatus((prev) => ({
          ...prev,
          database: {
            status: 'disconnected',
            label: 'Disconnected',
            details: err.message || 'Supabase PostgreSQL connection failed',
          },
        }));
      }
    }
  }, []);

  const loadProjects = useCallback(async () => {
    setProjectsLoading(true);
    setProjectsError(null);
    try {
      const data = await fetchProjects();
      setProjects(data);
    } catch (err: any) {
      setProjectsError(err.message || 'Failed to load projects');
      setProjects([]);
    } finally {
      setProjectsLoading(false);
    }
  }, []);

  const refreshAll = useCallback(async () => {
    setIsRefreshingHeader(true);
    await Promise.allSettled([performHealthChecks(), loadProjects()]);
    setIsRefreshingHeader(false);
  }, [performHealthChecks, loadProjects, setIsRefreshingHeader]);

  useEffect(() => {
    registerRefresh(refreshAll);
    refreshAll();
  }, [registerRefresh, refreshAll]);

  return (
    <div className="space-y-8 pb-12">
      {/* Real-time System Status Section */}
      <SystemStatus status={systemStatus} onRetry={performHealthChecks} />

      {/* Projects Section */}
      <ProjectsList
        projects={projects}
        isLoading={projectsLoading}
        error={projectsError}
        onRefresh={loadProjects}
      />

      {/* Future Investigation Engine Area */}
      <FutureInvestigationArea />
    </div>
  );
};
