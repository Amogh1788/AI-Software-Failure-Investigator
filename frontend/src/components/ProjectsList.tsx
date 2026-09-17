import React from 'react';
import { FolderGit2, Calendar, Hash, AlertCircle, Info } from 'lucide-react';
import type { Project } from '../types';

interface ProjectsListProps {
  projects: Project[];
  isLoading: boolean;
  error: string | null;
  onRefresh: () => void;
}

export const ProjectsList: React.FC<ProjectsListProps> = ({
  projects,
  isLoading,
  error,
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
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <h2 className="text-sm font-semibold tracking-wide text-slate-200 uppercase font-mono">
            Active Projects ({projects.length})
          </h2>
          <span className="text-xs text-slate-500 font-mono">source: Supabase PostgreSQL</span>
        </div>
        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="text-xs text-indigo-400 hover:text-indigo-300 font-mono hover:underline cursor-pointer disabled:opacity-50"
        >
          {isLoading ? 'Fetching...' : 'Refresh Projects'}
        </button>
      </div>

      {error ? (
        <div className="bg-rose-950/20 border border-rose-800/40 rounded-lg p-5 text-slate-300 space-y-2">
          <div className="flex items-center space-x-2 text-rose-400 font-medium text-sm">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>Unable to retrieve projects from backend</span>
          </div>
          <p className="text-xs text-slate-400 font-mono pl-6">{error}</p>
          <div className="pl-6 text-xs text-slate-400">
            Check your Supabase credentials in <code className="text-slate-300 bg-slate-800 px-1 py-0.5 rounded">backend/.env</code> and ensure the <code className="text-slate-300 bg-slate-800 px-1 py-0.5 rounded">projects</code> table has been created using <code className="text-slate-300 bg-slate-800 px-1 py-0.5 rounded">data/schema.sql</code>.
          </div>
        </div>
      ) : isLoading && projects.length === 0 ? (
        <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-8 text-center text-slate-400 text-sm font-mono">
          <div className="inline-block animate-spin rounded-full h-5 w-5 border-2 border-slate-600 border-t-indigo-400 mb-2" />
          <div>Querying projects via FastAPI & Supabase...</div>
        </div>
      ) : projects.length === 0 ? (
        <div className="bg-[#0f172a] border border-slate-800/80 rounded-lg p-8 text-center space-y-3">
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
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {projects.map((project) => (
            <div
              key={project.id}
              className="bg-[#0f172a] border border-slate-800 hover:border-slate-700 transition-colors rounded-lg p-4 space-y-3"
            >
              <div className="flex items-start justify-between space-x-2">
                <div className="flex items-center space-x-2">
                  <div className="p-1.5 bg-slate-800 rounded text-indigo-400">
                    <FolderGit2 className="w-4 h-4" />
                  </div>
                  <h3 className="text-sm font-semibold text-slate-200 font-mono tracking-tight">
                    {project.name}
                  </h3>
                </div>
              </div>

              <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                {project.description || 'No description provided.'}
              </p>

              <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400 font-mono">
                <span className="flex items-center space-x-1 text-slate-400">
                  <Hash className="w-3 h-3 text-slate-400" />
                  <span title={project.id}>{project.id.slice(0, 8)}...</span>
                </span>
                <span className="flex items-center space-x-1 text-slate-400">
                  <Calendar className="w-3 h-3 text-slate-400" />
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
