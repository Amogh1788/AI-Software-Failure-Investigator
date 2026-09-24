import React from 'react';
import { CheckCircle2, XCircle, Loader2, Server, Database, Cpu, RefreshCw } from 'lucide-react';
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

export const SystemStatus: React.FC<SystemStatusProps> = ({
  status,
  isChecking,
  onCheckConnectivity,
}) => {
  const backendConnected = status.backend.status === 'connected';
  const databaseConnected = status.database.status === 'connected';
  const analyzerReady = backendConnected && databaseConnected;

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
          title="Probe backend and database connectivity"
        >
          <RefreshCw className={`w-3 h-3 ${isChecking ? 'animate-spin text-indigo-400' : ''}`} />
          <span>{isChecking ? 'Checking...' : 'Check Status'}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* Backend Card */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-3.5 flex items-center justify-between">
          <div className="flex items-center space-x-2.5 min-w-0">
            <div className="p-2 bg-slate-800/70 border border-slate-700/60 rounded text-slate-300 shrink-0">
              <Server className="w-4 h-4 text-indigo-400" />
            </div>
            <div>
              <h3 className="text-xs font-semibold text-slate-200 uppercase font-mono">Backend</h3>
            </div>
          </div>
          <StatusBadge
            state={status.backend.status}
            label={backendConnected ? 'Connected' : status.backend.label}
          />
        </div>

        {/* Database Card */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-3.5 flex items-center justify-between">
          <div className="flex items-center space-x-2.5 min-w-0">
            <div className="p-2 bg-slate-800/70 border border-slate-700/60 rounded text-slate-300 shrink-0">
              <Database className="w-4 h-4 text-indigo-400" />
            </div>
            <div>
              <h3 className="text-xs font-semibold text-slate-200 uppercase font-mono">Database</h3>
            </div>
          </div>
          <StatusBadge
            state={status.database.status}
            label={databaseConnected ? 'Connected' : status.database.label}
          />
        </div>

        {/* Analyzer Card */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-3.5 flex items-center justify-between">
          <div className="flex items-center space-x-2.5 min-w-0">
            <div className="p-2 bg-slate-800/70 border border-slate-700/60 rounded text-slate-300 shrink-0">
              <Cpu className="w-4 h-4 text-indigo-400" />
            </div>
            <div>
              <h3 className="text-xs font-semibold text-slate-200 uppercase font-mono">Analyzer</h3>
            </div>
          </div>
          <StatusBadge
            state={analyzerReady ? 'connected' : status.backend.status === 'disconnected' ? 'disconnected' : 'checking'}
            label={analyzerReady ? 'Ready' : status.backend.status === 'disconnected' ? 'Offline' : 'Checking...'}
          />
        </div>
      </div>
    </section>
  );
};
