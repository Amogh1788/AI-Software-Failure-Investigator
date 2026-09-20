import React from 'react';
import {
  FolderGit2,
  Clock,
  Layers,
  ChevronRight,
  CheckCircle2,
  FileEdit,
  Trash2,
  Loader2,
} from 'lucide-react';
import type { Investigation, Repository, InvestigationStatus } from '../types';

interface InvestigationListProps {
  investigations: Investigation[];
  repositories: Repository[];
  selectedId: string | null;
  onSelectInvestigation: (id: string) => void;
  onDeleteInvestigation?: (id: string) => Promise<void>;
}

const renderStatusBadge = (status: InvestigationStatus) => {
  switch (status) {
    case 'completed':
      return (
        <span
          data-testid="status-badge-completed"
          className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase bg-purple-950/80 text-purple-400 border border-purple-800/60"
        >
          <CheckCircle2 className="w-3 h-3 text-purple-400" />
          <span>Completed</span>
        </span>
      );
    case 'analyzing':
      return (
        <span
          data-testid="status-badge-analyzing"
          className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase bg-indigo-950/80 text-indigo-400 border border-indigo-800/60"
        >
          <Loader2 className="w-3 h-3 animate-spin text-indigo-400" />
          <span>Analyzing</span>
        </span>
      );
    case 'ready':
      return (
        <span
          data-testid="status-badge-ready"
          className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase bg-emerald-950/80 text-emerald-400 border border-emerald-800/60"
        >
          <CheckCircle2 className="w-3 h-3" />
          <span>Ready</span>
        </span>
      );
    case 'draft':
    default:
      return (
        <span
          data-testid="status-badge-draft"
          className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase bg-amber-950/80 text-amber-400 border border-amber-800/60"
        >
          <FileEdit className="w-3 h-3" />
          <span>Draft</span>
        </span>
      );
  }
};

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
                {renderStatusBadge(inv.status)}
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
