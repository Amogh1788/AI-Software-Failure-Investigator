import React, { useState } from 'react';
import { PlusCircle, AlertCircle, FilePlus } from 'lucide-react';
import type { Repository, CreateInvestigationPayload, Investigation } from '../types';
import { createInvestigation } from '../services/api';

interface InvestigationCreatorProps {
  repositories: Repository[];
  selectedRepoId?: string;
  onInvestigationCreated: (newInv: Investigation) => void;
  onCancel?: () => void;
}

export const InvestigationCreator: React.FC<InvestigationCreatorProps> = ({
  repositories,
  selectedRepoId,
  onInvestigationCreated,
  onCancel,
}) => {
  const [repositoryId, setRepositoryId] = useState<string>(selectedRepoId || (repositories[0]?.id ?? ''));
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repositoryId) {
      setError('Please select an analyzed repository.');
      return;
    }
    if (!title.trim()) {
      setError('Please provide an investigation title.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const payload: CreateInvestigationPayload = {
        repository_id: repositoryId,
        title: title.trim(),
        description: description.trim() || null,
      };

      const newInv = await createInvestigation(payload);
      onInvestigationCreated(newInv);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create investigation');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-5 space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <FilePlus className="w-4 h-4 text-indigo-400" />
          <h3 className="text-sm font-semibold font-mono text-slate-100 uppercase tracking-wide">
            New Failure Investigation Case
          </h3>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Repository Selection */}
        <div>
          <label className="block text-xs font-mono text-slate-300 mb-1.5 uppercase tracking-wider">
            Target Analyzed Repository *
          </label>
          {repositories.length === 0 ? (
            <div className="p-3 bg-amber-950/30 border border-amber-800/50 rounded text-xs text-amber-200">
              No analyzed repositories available. Analyze a GitHub repository above first.
            </div>
          ) : (
            <div className="relative">
              <select
                value={repositoryId}
                onChange={(e) => setRepositoryId(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700/80 rounded px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 font-mono"
              >
                {repositories.map((repo) => (
                  <option key={repo.id} value={repo.id}>
                    {repo.owner}/{repo.name} ({repo.primary_language || 'Various'} • {repo.total_files} files)
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Title */}
        <div>
          <label className="block text-xs font-mono text-slate-300 mb-1 uppercase tracking-wider">
            Investigation Case Title *
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              if (error) setError(null);
            }}
            placeholder="e.g. Intermittent 504 Gateway Timeout on checkout endpoint"
            className="w-full bg-slate-900 border border-slate-700/80 rounded px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-xs font-mono text-slate-300 mb-1 uppercase tracking-wider">
            Initial Context & Description <span className="text-slate-500">(Optional)</span>
          </label>
          <textarea
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the failure scenario, incident context, or suspected regression area..."
            className="w-full bg-slate-900 border border-slate-700/80 rounded p-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 leading-relaxed"
          />
        </div>

        {error && (
          <div className="p-3 bg-red-950/40 border border-red-800/60 rounded text-xs text-red-200 flex items-start space-x-2">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <div className="flex items-center justify-end space-x-3 pt-1">
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="px-3 py-1.5 rounded text-xs font-mono text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors cursor-pointer"
            >
              Cancel
            </button>
          )}
          <button
            type="submit"
            disabled={isSubmitting || !repositoryId || !title.trim() || repositories.length === 0}
            className="inline-flex items-center space-x-1.5 px-4 py-2 rounded text-xs font-semibold font-mono bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-500 text-white shadow-sm transition-colors cursor-pointer disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <span className="inline-block w-3 h-3 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                <span>Creating Case...</span>
              </>
            ) : (
              <>
                <PlusCircle className="w-3.5 h-3.5" />
                <span>Create Investigation Case</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
