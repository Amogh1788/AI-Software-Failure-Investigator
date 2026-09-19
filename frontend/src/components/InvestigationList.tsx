import React from 'react';
import {
  FolderGit2,
  Clock,
  Layers,
  ChevronRight,
  CheckCircle2,
  FileEdit,
  Trash2,
} from 'lucide-react';
import type { Investigation, Repository } from '../types';

interface InvestigationListProps {
  investigations: Investigation[];
  repositories: Repository[];
  selectedId: string | null;
  onSelectInvestigation: (id: string) => void;
  onDeleteInvestigation?: (id: string) => Promise<void>;
}

export const InvestigationList: React.FC<InvestigationListProps> = ({
  investigations,
  repositories,
  selectedId,
  onSelectInvestigation,
  onDeleteInvestigation,
}) => {
  const getRepoName = (repoId: string) => {
    const repo = repositories.find((r) => r.id === repoId);
    return repo ? `${repo.owner}/${repo.name}` : 'Unknown Repository';
  };

  if (investigations.length === 0) {
    return (
      <div className="p-8 border border-dashed border-slate-800 rounded-lg text-center space-y-2 bg-slate-900/30">
        <Layers className="w-8 h-8 text-slate-600 mx-auto" />
        <p className="text-xs text-slate-300 font-mono">No investigation cases created yet.</p>
        <p className="text-[11px] text-slate-400">
          Create an investigation case above to begin collecting failure evidence.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2.5">
      {investigations.map((inv) => {
        const isSelected = selectedId === inv.id;
        const isReady = inv.status === 'ready';

        return (
          <div
            key={inv.id}
            onClick={() => onSelectInvestigation(inv.id)}
            className={`flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-lg border transition-all cursor-pointer ${
              isSelected
                ? 'bg-slate-800/90 border-indigo-500/80 shadow-sm'
                : 'bg-slate-900/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900/90'
            }`}
          >
            <div className="space-y-1.5 min-w-0 pr-4">
              <div className="flex items-center space-x-2.5">
                <h4 className="text-sm font-semibold text-slate-100 truncate">
                  {inv.title}
                </h4>
                <span
                  className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase ${
                    isReady
                      ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/60'
                      : 'bg-amber-950/80 text-amber-400 border border-amber-800/60'
                  }`}
                >
                  {isReady ? (
                    <>
                      <CheckCircle2 className="w-3 h-3" />
                      <span>Ready</span>
                    </>
                  ) : (
                    <>
                      <FileEdit className="w-3 h-3" />
                      <span>Draft</span>
                    </>
                  )}
                </span>
              </div>

              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400 font-mono">
                <span className="flex items-center space-x-1 text-slate-300">
                  <FolderGit2 className="w-3.5 h-3.5 text-indigo-400" />
                  <span>{getRepoName(inv.repository_id)}</span>
                </span>
                <span className="flex items-center space-x-1">
                  <Layers className="w-3.5 h-3.5 text-slate-400" />
                  <span>{inv.evidence_count} evidence item{inv.evidence_count === 1 ? '' : 's'}</span>
                </span>
                <span className="flex items-center space-x-1">
                  <Clock className="w-3 h-3 text-slate-400" />
                  <span>{new Date(inv.created_at).toLocaleDateString()}</span>
                </span>
              </div>

              {inv.description && (
                <p className="text-xs text-slate-400 line-clamp-1 pt-0.5">{inv.description}</p>
              )}
            </div>

            <div className="flex items-center space-x-2 pt-2 sm:pt-0 shrink-0">
              {onDeleteInvestigation && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (window.confirm(`Delete investigation "${inv.title}"?`)) {
                      onDeleteInvestigation(inv.id);
                    }
                  }}
                  className="p-1.5 text-slate-400 hover:text-red-400 rounded hover:bg-slate-800 transition-colors"
                  title="Delete case"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
              <ChevronRight
                className={`w-4 h-4 transition-transform ${
                  isSelected ? 'text-indigo-400 translate-x-0.5' : 'text-slate-400'
                }`}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
};
