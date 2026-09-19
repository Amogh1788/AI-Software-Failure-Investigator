import React from 'react';
import { GitCommit, User, Calendar, FileDiff } from 'lucide-react';
import type { RepositoryCommit } from '../types';

interface RepositoryHistoryProps {
  commits: RepositoryCommit[];
}

export const RepositoryHistory: React.FC<RepositoryHistoryProps> = ({ commits }) => {
  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return 'N/A';
    try {
      const d = new Date(dateStr);
      return new Intl.DateTimeFormat('en-US', {
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(d);
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-5 space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <div>
          <h3 className="text-sm font-semibold tracking-wide text-slate-200 uppercase font-mono">
            Recent Git History ({commits.length} commits)
          </h3>
          <p className="text-xs text-slate-400">
            Metadata extracted from the latest repository commits. Diffs excluded in Phase 2.
          </p>
        </div>
      </div>

      {commits.length === 0 ? (
        <div className="text-center py-8 text-slate-500 font-mono text-xs">
          No commits found or commit history could not be retrieved.
        </div>
      ) : (
        <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
          {commits.map((commit) => (
            <div
              key={commit.commit_hash}
              className="bg-slate-900/70 border border-slate-800/80 hover:border-slate-700 transition-colors rounded p-3.5 space-y-2"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center space-x-2 min-w-0">
                  <div className="p-1 bg-slate-800 rounded text-indigo-400 shrink-0">
                    <GitCommit className="w-3.5 h-3.5" />
                  </div>
                  <span className="text-xs font-mono font-semibold text-slate-200 truncate">
                    {commit.commit_message || 'Commit without message'}
                  </span>
                </div>

                <span className="font-mono text-[11px] text-indigo-400 bg-indigo-950/60 border border-indigo-800/50 px-2 py-0.5 rounded shrink-0">
                  {commit.commit_hash.slice(0, 7)}
                </span>
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono flex-wrap gap-2 pt-1 border-t border-slate-800/60">
                <div className="flex items-center space-x-3">
                  <span className="flex items-center space-x-1 text-slate-300">
                    <User className="w-3 h-3 text-slate-500" />
                    <span>{commit.author_name || 'Unknown Author'}</span>
                  </span>
                  <span className="flex items-center space-x-1 text-slate-400">
                    <Calendar className="w-3 h-3 text-slate-500" />
                    <span>{formatDate(commit.committed_at)}</span>
                  </span>
                </div>

                <span className="flex items-center space-x-1 text-slate-400">
                  <FileDiff className="w-3 h-3 text-indigo-400" />
                  <span>{commit.files_changed} files changed</span>
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
