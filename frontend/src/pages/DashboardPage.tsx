import React, { useEffect, useState, useCallback, useRef } from 'react';
import { SystemStatus } from '../components/SystemStatus';
import { RepositoryAnalyzer } from '../components/RepositoryAnalyzer';
import { InvestigationManager } from '../components/InvestigationManager';
import { FutureInvestigationArea } from '../components/FutureInvestigationArea';
import { checkBackendHealth, checkDatabaseHealth } from '../services/api';
import type { SystemStatusState } from '../types';

interface DashboardPageProps {
  registerRefresh: (fn: () => void) => void;
  onProjectsRefreshingChange?: (isRefreshing: boolean) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  registerRefresh,
  onProjectsRefreshingChange,
}) => {
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

  const isCheckingConnectivityRef = useRef<boolean>(false);

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
   */
  const checkConnectivity = useCallback(async () => {
    if (isCheckingConnectivityRef.current) return;
    isCheckingConnectivityRef.current = true;
    setIsCheckingConnectivity(true);
    onProjectsRefreshingChange?.(true);

    try {
      await Promise.allSettled([checkBackend(), checkDatabase()]);
    } finally {
      isCheckingConnectivityRef.current = false;
      setIsCheckingConnectivity(false);
      onProjectsRefreshingChange?.(false);
    }
  }, [onProjectsRefreshingChange]);

  // Keep registered refresh callback updated without re-running mount requests
  useEffect(() => {
    registerRefresh(checkConnectivity);
  }, [registerRefresh, checkConnectivity]);

  // Run on first load: check connectivity
  useEffect(() => {
    checkConnectivity();
  }, [checkConnectivity]);

  return (
    <div className="space-y-8 pb-12">
      {/* 1. Analyze Repository */}
      <RepositoryAnalyzer />

      {/* 2. Recent Investigations */}
      <InvestigationManager />

      {/* 3. Investigation Analysis Overview */}
      <FutureInvestigationArea />

      {/* 4. Compact Real-time System Status */}
      <SystemStatus
        status={systemStatus}
        isChecking={isCheckingConnectivity}
        onCheckConnectivity={checkConnectivity}
      />
    </div>
  );
};
