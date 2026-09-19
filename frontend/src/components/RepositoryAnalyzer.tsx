import React, { useState, useEffect, useCallback } from 'react';
import {
  FolderGit2,
  Search,
  Loader2,
  AlertCircle,
  FolderTree,
  History,
  LayoutDashboard,
} from 'lucide-react';
import {
  analyzeRepository,
  getRepositories,
  getRepositoryFiles,
  getRepositoryCommits,
} from '../services/api';
import type { Repository, RepositoryFile, RepositoryCommit } from '../types';
import { RepositorySummary } from './RepositorySummary';
import { RepositoryFiles } from './RepositoryFiles';
import { RepositoryHistory } from './RepositoryHistory';

type AnalysisState = 'idle' | 'analyzing' | 'success' | 'error';
type ActiveTab = 'summary' | 'files' | 'history';

export const RepositoryAnalyzer: React.FC = () => {
  const [urlInput, setUrlInput] = useState('');
  const [analysisState, setAnalysisState] = useState<AnalysisState>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Available analyzed repositories from database
  const [analyzedRepos, setAnalyzedRepos] = useState<Repository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<Repository | null>(null);
  const [repoFiles, setRepoFiles] = useState<RepositoryFile[]>([]);
  const [repoCommits, setRepoCommits] = useState<RepositoryCommit[]>([]);
  const [activeTab, setActiveTab] = useState<ActiveTab>('summary');

  // Load previously analyzed repositories on mount
  const loadExistingRepositories = useCallback(async () => {
    try {
      const repos = await getRepositories();
      setAnalyzedRepos(repos);
      if (repos.length > 0 && !selectedRepo) {
        // Select the most recent repository by default
        loadRepositoryDetails(repos[0]);
      }
    } catch {
      // ignore on mount if backend/db is not seeded yet
    }
  }, [selectedRepo]);

  useEffect(() => {
    loadExistingRepositories();
  }, [loadExistingRepositories]);

  const loadRepositoryDetails = async (repo: Repository) => {
    setSelectedRepo(repo);
    try {
      const [files, commits] = await Promise.all([
        getRepositoryFiles(repo.id),
        getRepositoryCommits(repo.id),
      ]);
      setRepoFiles(files);
      setRepoCommits(commits);
    } catch {
      // fallback
    }
  };

  const handleAnalyze = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();

    const trimmed = urlInput.trim();
    if (!trimmed) return;

    // Client-side quick validation
    if (!trimmed.startsWith('https://github.com/')) {
      setAnalysisState('error');
      setErrorMessage('Only public GitHub HTTPS repositories are supported (e.g. https://github.com/owner/repo).');
      return;
    }

    setAnalysisState('analyzing');
    setErrorMessage(null);

    try {
      const detail = await analyzeRepository(trimmed);
      setAnalysisState('success');
      setSelectedRepo(detail.repository);
      setRepoFiles(detail.files);
      setRepoCommits(detail.commits);
      setActiveTab('summary');
      setUrlInput('');

      // Refresh repository dropdown list
      setAnalyzedRepos((prev) => [
        detail.repository,
        ...prev.filter((r) => r.id !== detail.repository.id),
      ]);
    } catch (err: any) {
      setAnalysisState('error');
      const rawMsg = err.message || '';

      if (rawMsg.includes('timed out')) {
        setErrorMessage('Repository analysis timed out. The repository may be too large.');
      } else if (rawMsg.includes('exceeds the allowed limit')) {
        setErrorMessage('Repository exceeds the allowed analysis size limit.');
      } else if (rawMsg.includes('could not be found') || rawMsg.includes('404')) {
        setErrorMessage('Repository could not be cloned. Ensure it exists and is public.');
      } else {
        setErrorMessage(rawMsg || 'Failed to analyze repository. Please verify the URL and try again.');
      }
    }
  };

  return (
    <section className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold tracking-wide text-slate-200 uppercase font-mono">
            Repository Ingestion & Codebase Analysis
          </h2>
          <p className="text-xs text-slate-400">
            Phase 2: Ingest public GitHub repositories, perform static code inspection, and extract commit history.
          </p>
        </div>

        {analyzedRepos.length > 0 && (
          <div className="flex items-center space-x-2">
            <span className="text-xs text-slate-400 font-mono">History:</span>
            <select
              value={selectedRepo?.id || ''}
              onChange={(e) => {
                const target = analyzedRepos.find((r) => r.id === e.target.value);
                if (target) loadRepositoryDetails(target);
              }}
              className="bg-slate-900 border border-slate-800 rounded px-2.5 py-1 text-xs text-slate-200 font-mono outline-none focus:border-indigo-500"
            >
              {analyzedRepos.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.owner}/{r.name} ({r.primary_language || 'Repo'})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* URL Input Form */}
      <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-4 space-y-3">
        <form onSubmit={handleAnalyze} className="flex flex-col sm:flex-row items-center gap-3">
          <div className="relative flex-1 w-full">
            <FolderGit2 className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
            <input
              type="text"
              placeholder="https://github.com/owner/repository"
              value={urlInput}
              onChange={(e) => {
                setUrlInput(e.target.value);
                if (analysisState === 'error') setAnalysisState('idle');
              }}
              disabled={analysisState === 'analyzing'}
              className="w-full bg-slate-900/90 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-md pl-9 pr-4 py-2 text-xs font-mono text-slate-100 placeholder:text-slate-500 outline-none transition-colors disabled:opacity-50"
            />
          </div>

          <button
            type="submit"
            disabled={analysisState === 'analyzing' || !urlInput.trim()}
            className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-4 py-2 rounded-md text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer whitespace-nowrap"
          >
            {analysisState === 'analyzing' ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Analyzing repository...</span>
              </>
            ) : (
              <>
                <Search className="w-3.5 h-3.5" />
                <span>Analyze Repository</span>
              </>
            )}
          </button>
        </form>

        {/* Quick sample link and format note */}
        <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 flex-wrap gap-2">
          <span>Supported: Public GitHub HTTPS repositories only (e.g. https://github.com/owner/repo)</span>
          <button
            type="button"
            onClick={() => setUrlInput('https://github.com/octocat/Hello-World')}
            className="text-indigo-400 hover:text-indigo-300 hover:underline cursor-pointer"
          >
            Use sample: octocat/Hello-World
          </button>
        </div>

        {/* Analyzing Status Indicator */}
        {analysisState === 'analyzing' && (
          <div className="bg-indigo-950/40 border border-indigo-800/40 rounded-md p-3 flex items-center space-x-3 text-xs text-indigo-200">
            <Loader2 className="w-4 h-4 animate-spin text-indigo-400 shrink-0" />
            <div className="space-y-0.5">
              <p className="font-semibold">Cloning and statically inspecting repository...</p>
              <p className="text-[11px] text-slate-400 font-mono">
                Executing shallow clone, mapping programming languages, and parsing recent commits.
              </p>
            </div>
          </div>
        )}

        {/* Error Alert */}
        {analysisState === 'error' && errorMessage && (
          <div className="bg-rose-950/30 border border-rose-800/50 rounded-md p-3 flex items-start space-x-2 text-xs text-rose-300">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <span className="break-words">{errorMessage}</span>
          </div>
        )}
      </div>

      {/* Selected Repository Analysis View */}
      {selectedRepo && (
        <div className="space-y-3">
          {/* Tab Navigation */}
          <div className="flex items-center space-x-2 border-b border-slate-800 pb-2">
            <button
              onClick={() => setActiveTab('summary')}
              className={`inline-flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-mono transition-colors cursor-pointer ${
                activeTab === 'summary'
                  ? 'bg-slate-800 text-white border border-slate-700 font-semibold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <LayoutDashboard className="w-3.5 h-3.5 text-indigo-400" />
              <span>Overview & Metrics</span>
            </button>

            <button
              onClick={() => setActiveTab('files')}
              className={`inline-flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-mono transition-colors cursor-pointer ${
                activeTab === 'files'
                  ? 'bg-slate-800 text-white border border-slate-700 font-semibold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <FolderTree className="w-3.5 h-3.5 text-indigo-400" />
              <span>File Tree ({repoFiles.length})</span>
            </button>

            <button
              onClick={() => setActiveTab('history')}
              className={`inline-flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-mono transition-colors cursor-pointer ${
                activeTab === 'history'
                  ? 'bg-slate-800 text-white border border-slate-700 font-semibold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <History className="w-3.5 h-3.5 text-indigo-400" />
              <span>Git Commits ({repoCommits.length})</span>
            </button>
          </div>

          {/* Active Tab Content */}
          {activeTab === 'summary' && (
            <RepositorySummary repository={selectedRepo} commitsCount={repoCommits.length} />
          )}

          {activeTab === 'files' && <RepositoryFiles files={repoFiles} />}

          {activeTab === 'history' && <RepositoryHistory commits={repoCommits} />}
        </div>
      )}
    </section>
  );
};
