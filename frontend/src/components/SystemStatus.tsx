import React from 'react';
import { CheckCircle2, XCircle, Loader2, Monitor, Server, Database } from 'lucide-react';
import type { ConnectionState, SystemStatusState } from '../types';

interface SystemStatusProps {
  status: SystemStatusState;
  onRetry: () => void;
}

const StatusBadge: React.FC<{ state: ConnectionState; label: string }> = ({ state, label }) => {
  switch (state) {
    case 'connected':
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
          <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
          {label}
        </span>
      );
    case 'disconnected':
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-950/80 text-rose-400 border border-rose-800/60">
          <XCircle className="w-3.5 h-3.5 mr-1" />
          {label}
        </span>
      );
    case 'checking':
    default:
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-950/80 text-amber-400 border border-amber-800/60">
          <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />
          {label}
        </span>
      );
  }
};

export const SystemStatus: React.FC<SystemStatusProps> = ({ status, onRetry }) => {
  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold tracking-wide text-slate-200 uppercase font-mono">
            System Status
          </h2>
          <p className="text-xs text-slate-400">
            Real-time diagnostics across the three-tier system architecture.
          </p>
        </div>
        <button
          onClick={onRetry}
          className="text-xs text-indigo-400 hover:text-indigo-300 font-mono hover:underline cursor-pointer"
        >
          Check Connectivity
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Frontend Card */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-4 flex flex-col justify-between space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <div className="p-2 bg-slate-800/70 border border-slate-700/60 rounded text-slate-300">
                <Monitor className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-medium text-slate-200">Frontend Client</h3>
                <p className="text-[11px] text-slate-400 font-mono">React / Vite (SPA)</p>
              </div>
            </div>
            <StatusBadge state={status.frontend.status} label={status.frontend.label} />
          </div>
          <div className="text-xs text-slate-400 font-mono bg-slate-900/60 border border-slate-800/80 rounded px-2.5 py-1.5 break-all">
            {status.frontend.details || 'Browser application running'}
          </div>
        </div>

        {/* Backend Card */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-4 flex flex-col justify-between space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <div className="p-2 bg-slate-800/70 border border-slate-700/60 rounded text-slate-300">
                <Server className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-medium text-slate-200">Backend API</h3>
                <p className="text-[11px] text-slate-400 font-mono">FastAPI / Uvicorn</p>
              </div>
            </div>
            <StatusBadge state={status.backend.status} label={status.backend.label} />
          </div>
          <div className="text-xs text-slate-400 font-mono bg-slate-900/60 border border-slate-800/80 rounded px-2.5 py-1.5 break-all">
            {status.backend.details || 'GET /api/health probe'}
          </div>
        </div>

        {/* Database Card */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-4 flex flex-col justify-between space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <div className="p-2 bg-slate-800/70 border border-slate-700/60 rounded text-slate-300">
                <Database className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-medium text-slate-200">Database</h3>
                <p className="text-[11px] text-slate-400 font-mono">Supabase PostgreSQL</p>
              </div>
            </div>
            <StatusBadge state={status.database.status} label={status.database.label} />
          </div>
          <div className="text-xs text-slate-400 font-mono bg-slate-900/60 border border-slate-800/80 rounded px-2.5 py-1.5 break-all">
            {status.database.details || 'Backend PostgreSQL connection check'}
          </div>
        </div>
      </div>
    </section>
  );
};
