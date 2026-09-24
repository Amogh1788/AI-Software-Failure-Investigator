import React, { useState, useEffect, useCallback } from 'react';
import {
  FilePlus,
  Layers,
  RefreshCw,
  AlertCircle,
  FolderGit2,
} from 'lucide-react';
import type { Investigation, Repository } from '../types';
import { getInvestigations, getRepositories, deleteInvestigation } from '../services/api';
import { InvestigationCreator } from './InvestigationCreator';
import { InvestigationList } from './InvestigationList';
import { InvestigationDetail } from './InvestigationDetail';

export const InvestigationManager: React.FC = () => {
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selectedInvestigationId, setSelectedInvestigationId] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async (isSilent = false) => {
    try {
      if (!isSilent) setLoading(true);
      else setRefreshing(true);
      setError(null);

      const [invs, repos] = await Promise.all([
        getInvestigations(),
        getRepositories().catch(() => [] as Repository[]),
      ]);

      setInvestigations(invs);
      setRepositories(repos);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load investigation cases');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleInvestigationCreated = (newInv: Investigation) => {
    setInvestigations((prev) => [newInv, ...prev]);
    setIsCreating(false);
    setSelectedInvestigationId(newInv.id);
  };

  const handleCloseDetail = () => {
    setSelectedInvestigationId(null);
    loadData(true);
  };

  const handleInvestigationUpdated = (updated?: Investigation) => {
    if (updated) {
      setInvestigations((prev) =>
        prev.map((inv) => (inv.id === updated.id ? { ...inv, ...updated } : inv))
      );
    }
    loadData(true);
  };

  const handleDeleteInvestigation = async (id: string) => {
    try {
      await deleteInvestigation(id);
      setInvestigations((prev) => prev.filter((i) => i.id !== id));
      if (selectedInvestigationId === id) {
        setSelectedInvestigationId(null);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to delete investigation');
    }
  };

  return (
    <section className="space-y-4">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold tracking-wide text-slate-200 uppercase font-mono">
            Recent Investigations
          </h2>
          <p className="text-xs text-slate-400">
            Track failure investigations and attach runtime evidence (logs, stack traces, bug reports, and test output).
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => loadData(true)}
            disabled={loading || refreshing}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-mono text-slate-300 bg-slate-900 border border-slate-700/80 hover:bg-slate-800 transition-colors cursor-pointer disabled:opacity-50"
            title="Refresh investigations"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          {!isCreating && !selectedInvestigationId && (
            <button
              onClick={() => setIsCreating(true)}
              disabled={repositories.length === 0}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-mono font-semibold bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-500 text-white transition-colors cursor-pointer disabled:cursor-not-allowed"
            >
              <FilePlus className="w-3.5 h-3.5" />
              <span>New Investigation Case</span>
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-950/40 border border-red-800/60 rounded text-xs text-red-200 flex items-start space-x-2">
          <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* Selected Investigation Detail View */}
      {selectedInvestigationId ? (
        <InvestigationDetail
          investigationId={selectedInvestigationId}
          onClose={handleCloseDetail}
          onUpdated={handleInvestigationUpdated}
        />
      ) : isCreating ? (
        <InvestigationCreator
          repositories={repositories}
          onInvestigationCreated={handleInvestigationCreated}
          onCancel={() => setIsCreating(false)}
        />
      ) : (
        <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <div className="flex items-center space-x-2">
              <Layers className="w-4 h-4 text-indigo-400" />
              <h3 className="text-xs font-semibold font-mono text-slate-200 uppercase tracking-wide">
                Investigations ({investigations.length})
              </h3>
            </div>
            {repositories.length === 0 && (
              <span className="text-xs text-amber-400 font-mono flex items-center space-x-1">
                <FolderGit2 className="w-3.5 h-3.5" />
                <span>Analyze a repository above to create cases</span>
              </span>
            )}
          </div>

          {loading ? (
            <div className="p-8 text-center space-y-2">
              <span className="inline-block w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-xs text-slate-400 font-mono">Loading investigation cases...</p>
            </div>
          ) : (
            <InvestigationList
              investigations={investigations}
              repositories={repositories}
              selectedId={selectedInvestigationId}
              onSelectInvestigation={(id) => setSelectedInvestigationId(id)}
              onDeleteInvestigation={handleDeleteInvestigation}
            />
          )}
        </div>
      )}
    </section>
  );
};
