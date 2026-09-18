import React from 'react';
import { CheckCircle2, XCircle, Loader2, Monitor, Server, Database, RefreshCw } from 'lucide-react';
import type { ConnectionState, SystemStatusState } from '../types';

interface SystemStatusProps {
  status: SystemStatusState;
  isChecking: boolean;
  onCheckConnectivity: () => void;
}

const StatusBadge: React.FC<{ state: ConnectionState; label: string }> = ({ state, label }) => {
  switch (state) {
    case 'connected':
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-950/80 text-emerald-400 border border-emerald-800/60 whitespace-nowrap shrink-0">
          <CheckCircle2 className="w-3.5 h-3.5 mr-1 shrink-0" />
          <span>{label}</span>
        </span>
      );
    case 'disconnected':
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-950/80 text-rose-400 border border-rose-800/60 whitespace-nowrap shrink-0">
          <XCircle className="w-3.5 h-3.5 mr-1 shrink-0" />
          <span>{label}</span>
        </span>
      );
    case 'checking':
    default:
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-950/80 text-amber-400 border border-amber-800/60 whitespace-nowrap shrink-0">
          <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin shrink-0" />
          <span>{label}</span>
        </span>
      );
  }
};

const renderDetails = (details?: string) => {
  if (!details) {
    return <span className="text-slate-500">No diagnostic info</span>;
  }

  // Prevent awkward breaking of HTTP status codes like HTTP 200
  const match = details.match(/(.*?)(\(?HTTP\s+\d+\)?)(.*)/i);
  if (match) {
    return (
      <span className="break-words [overflow-wrap:anywhere]">
        {match[1]}
        <span className="whitespace-nowrap font-medium text-slate-300 bg-slate-800/90 px-1 py-0.5 rounded mx-0.5 border border-slate-700/50">
          {match[2]}
        </span>
        {match[3]}
      </span>
    );
  }

  return <span className="break-words [overflow-wrap:anywhere]">{details}</span>;
};

export const SystemStatus: React.FC<SystemStatusProps> = ({
  status,
  isChecking,
  onCheckConnectivity,
}) => {
  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold tracking-wide text-slate-200 uppercase font-mono">
          System Status
        </h2>
        <button
          onClick={onCheckConnectivity}
          disabled={isChecking}
          className="inline-flex items-center space-x-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-mono hover:underline cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed disabled:no-underline"
          title="Probe backend and database connectivity in parallel"
        >
          <RefreshCw className={`w-3 h-3 ${isChecking ? 'animate-spin text-indigo-400' : ''}`} />
          <span>{isChecking ? 'Checking...' : 'Check Connectivity'}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-stretch">
        {/* Frontend Card */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-4 sm:p-5 flex flex-col justify-between h-full min-h-[140px] space-y-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center space-x-2.5 min-w-0">
              <div className="p-2 bg-slate-800/70 border border-slate-700/60 rounded text-slate-300 shrink-0">
                <Monitor className="w-4 h-4" />
              </div>
              <div className="min-w-0">
                <h3 className="text-sm font-medium text-slate-200 whitespace-nowrap">Frontend Client</h3>
                <p className="text-[11px] text-slate-400 font-mono whitespace-nowrap">React / Vite (SPA)</p>
              </div>
            </div>
            <StatusBadge state={status.frontend.status} label={status.frontend.label} />
          </div>
          <div className="text-xs text-slate-400 font-mono bg-slate-900/60 border border-slate-800/80 rounded px-3 py-2 min-h-[44px] flex items-center leading-relaxed overflow-hidden">
            {renderDetails(status.frontend.details)}
          </div>
        </div>

        {/* Backend Card */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-4 sm:p-5 flex flex-col justify-between h-full min-h-[140px] space-y-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center space-x-2.5 min-w-0">
              <div className="p-2 bg-slate-800/70 border border-slate-700/60 rounded text-slate-300 shrink-0">
                <Server className="w-4 h-4" />
              </div>
              <div className="min-w-0">
                <h3 className="text-sm font-medium text-slate-200 whitespace-nowrap">Backend API</h3>
                <p className="text-[11px] text-slate-400 font-mono whitespace-nowrap">FastAPI / Uvicorn</p>
              </div>
            </div>
            <StatusBadge state={status.backend.status} label={status.backend.label} />
          </div>
          <div className="text-xs text-slate-400 font-mono bg-slate-900/60 border border-slate-800/80 rounded px-3 py-2 min-h-[44px] flex items-center leading-relaxed overflow-hidden">
            {renderDetails(status.backend.details)}
          </div>
        </div>

        {/* Database Card */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-4 sm:p-5 flex flex-col justify-between h-full min-h-[140px] space-y-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center space-x-2.5 min-w-0">
              <div className="p-2 bg-slate-800/70 border border-slate-700/60 rounded text-slate-300 shrink-0">
                <Database className="w-4 h-4" />
              </div>
              <div className="min-w-0">
                <h3 className="text-sm font-medium text-slate-200 whitespace-nowrap">Database</h3>
                <p className="text-[11px] text-slate-400 font-mono whitespace-nowrap">Supabase PostgreSQL</p>
              </div>
            </div>
            <StatusBadge state={status.database.status} label={status.database.label} />
          </div>
          <div className="text-xs text-slate-400 font-mono bg-slate-900/60 border border-slate-800/80 rounded px-3 py-2 min-h-[44px] flex items-center leading-relaxed overflow-hidden">
            {renderDetails(status.database.details)}
          </div>
        </div>
      </div>
    </section>
  );
};
