import React from 'react';
import { FolderGit2, Calendar, Hash, AlertCircle, AlertTriangle, Info, RefreshCw, Loader2 } from 'lucide-react';
import type { Project } from '../types';

interface ProjectsListProps {
  projects: Project[];
  isInitialLoading: boolean;
  isRefreshing: boolean;
  error: string | null;
  warning: string | null;
  onRefresh: () => void;
}

export const ProjectsList: React.FC<ProjectsListProps> = ({
  projects,
  isInitialLoading,
  isRefreshing,
  error,
  warning,
  onRefresh,
}) => {
  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return new Intl.DateTimeFormat('en-US', {
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(date);
    } catch {
      return dateString;
    }
  };

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center space-x-2.5">
          <h2 className="text-sm font-semibold tracking-wide text-slate-200 uppercase font-mono">
            Active Projects ({projects.length})
          </h2>
          <span className="hidden sm:inline text-xs text-slate-500 font-mono">
            source: Supabase PostgreSQL
          </span>
          {isRefreshing && projects.length > 0 && (
            <span className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded text-[11px] font-mono text-indigo-300 bg-indigo-950/70 border border-indigo-800/50 whitespace-nowrap">
              <Loader2 className="w-3 h-3 animate-spin text-indigo-400 shrink-0" />
              <span>Refreshing...</span>
            </span>
          )}
        </div>

        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded text-xs text-indigo-400 hover:text-indigo-300 font-mono bg-slate-900/60 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed select-none"
          title="Refresh projects list from database"
        >
          <RefreshCw className={`w-3 h-3 ${isRefreshing ? 'animate-spin text-indigo-400' : ''}`} />
          <span className="whitespace-nowrap">{isRefreshing ? 'Refreshing...' : 'Refresh Projects'}</span>
        </button>
      </div>

      {/* Non-blocking warning banner if refresh failed but previous projects are preserved */}
      {warning && projects.length > 0 && (
        <div className="bg-amber-950/25 border border-amber-800/40 rounded-lg px-4 py-2.5 flex items-center justify-between text-xs text-amber-200 gap-3">
          <div className="flex items-center space-x-2 min-w-0">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <span className="break-words [overflow-wrap:anywhere]">{warning}</span>
          </div>
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="text-amber-300 hover:text-amber-100 underline font-mono text-xs cursor-pointer whitespace-nowrap shrink-0 disabled:opacity-50"
          >
            Retry
          </button>
        </div>
      )}

      {/* Large initial error state: ONLY displayed if projects have NEVER successfully loaded */}
      {error && projects.length === 0 ? (
        <div className="bg-rose-950/20 border border-rose-800/40 rounded-lg p-5 text-slate-300 space-y-2.5 min-h-[160px] flex flex-col justify-center">
          <div className="flex items-center space-x-2 text-rose-400 font-medium text-sm">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>Unable to retrieve projects from backend</span>
          </div>
          <p className="text-xs text-slate-400 font-mono pl-6 break-words [overflow-wrap:anywhere]">{error}</p>
          <div className="pl-6 text-xs text-slate-400">
            Check your Supabase credentials in <code className="text-slate-300 bg-slate-800 px-1 py-0.5 rounded whitespace-nowrap">backend/.env</code> and ensure the <code className="text-slate-300 bg-slate-800 px-1 py-0.5 rounded whitespace-nowrap">projects</code> table has been created using <code className="text-slate-300 bg-slate-800 px-1 py-0.5 rounded whitespace-nowrap">data/schema.sql</code>.
          </div>
        </div>
      ) : isInitialLoading && projects.length === 0 ? (
        /* Initial loading placeholder */
        <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-8 text-center text-slate-400 text-sm font-mono min-h-[160px] flex flex-col items-center justify-center space-y-2">
          <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
          <div>Querying projects via FastAPI & Supabase...</div>
        </div>
      ) : projects.length === 0 ? (
        /* Empty State */
        <div className="bg-[#0f172a] border border-slate-800/80 rounded-lg p-8 text-center space-y-3 min-h-[160px] flex flex-col items-center justify-center">
          <div className="mx-auto w-10 h-10 rounded-full bg-slate-800/80 border border-slate-700/60 flex items-center justify-center text-slate-400">
            <Info className="w-5 h-5" />
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-medium text-slate-200">No Projects Found</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              The Supabase <code className="font-mono text-slate-300">projects</code> table is currently empty or awaiting seed records.
            </p>
          </div>
          <p className="text-xs text-slate-500 font-mono">
            Run the sample INSERT statements from <code className="text-indigo-400">data/schema.sql</code> in your Supabase SQL Editor.
          </p>
        </div>
      ) : (
        /* Projects List (preserved continuously across refreshes) */
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {projects.map((project) => (
            <div
              key={project.id}
              className={`bg-[#0f172a] border border-slate-800 hover:border-slate-700 transition-all rounded-lg p-4 space-y-3 ${
                isRefreshing ? 'opacity-85' : 'opacity-100'
              }`}
            >
              <div className="flex items-start justify-between space-x-2">
                <div className="flex items-center space-x-2 min-w-0">
                  <div className="p-1.5 bg-slate-800 rounded text-indigo-400 shrink-0">
                    <FolderGit2 className="w-4 h-4" />
                  </div>
                  <h3 className="text-sm font-semibold text-slate-200 font-mono tracking-tight truncate">
                    {project.name}
                  </h3>
                </div>
              </div>

              <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed break-words [overflow-wrap:anywhere]">
                {project.description || 'No description provided.'}
              </p>

              <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400 font-mono flex-wrap gap-1">
                <span className="flex items-center space-x-1 text-slate-400 whitespace-nowrap">
                  <Hash className="w-3 h-3 text-slate-500 shrink-0" />
                  <span title={project.id}>{project.id.slice(0, 8)}...</span>
                </span>
                <span className="flex items-center space-x-1 text-slate-400 whitespace-nowrap">
                  <Calendar className="w-3 h-3 text-slate-500 shrink-0" />
                  <span>{formatDate(project.created_at)}</span>
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
};
