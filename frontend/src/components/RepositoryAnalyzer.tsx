import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  FolderGit2,
  Search,
  Loader2,
  AlertCircle,
  FolderTree,
  History,
  LayoutDashboard,
  ChevronDown,
  X,
} from 'lucide-react';
import {
  analyzeRepository,
  getRepositories,
  getRepositoryFiles,
  getRepositoryCommits,
  deleteRepositoryHistory,
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

  // History dropdown state
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [deletingRepoId, setDeletingRepoId] = useState<string | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const historyRef = useRef<HTMLDivElement>(null);

  // Close history dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (historyRef.current && !historyRef.current.contains(event.target as Node)) {
        setIsHistoryOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

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

      if (
        rawMsg.includes('timed out') ||
        rawMsg.includes('signal is aborted') ||
        rawMsg.includes('aborted') ||
        rawMsg.includes('504')
      ) {
        setErrorMessage('Repository analysis timed out. The repository may be too large or complex to analyze within the current processing limit.');
      } else if (rawMsg.includes('exceeds the allowed limit')) {
        setErrorMessage('Repository exceeds the allowed analysis size limit.');
      } else if (rawMsg.includes('could not be found') || rawMsg.includes('404')) {
        setErrorMessage('Repository could not be cloned. Ensure it exists and is public.');
      } else {
        setErrorMessage(rawMsg || 'Failed to analyze repository. Please verify the URL and try again.');
      }
    }
  };

  const handleDeleteHistory = async (repoId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setDeletingRepoId(repoId);
    setHistoryError(null);
    try {
      await deleteRepositoryHistory(repoId);
      const remaining = analyzedRepos.filter((r) => r.id !== repoId);
      setAnalyzedRepos(remaining);
      if (selectedRepo?.id === repoId) {
        if (remaining.length > 0) {
          loadRepositoryDetails(remaining[0]);
        } else {
          setSelectedRepo(null);
          setRepoFiles([]);
          setRepoCommits([]);
        }
      }
    } catch (err: any) {
      setHistoryError(err.message || 'Failed to remove repository from history.');
    } finally {
      setDeletingRepoId(null);
    }
  };

  return (
    <section className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold tracking-wide text-slate-200 uppercase font-mono">
            Analyze Repository
          </h2>
          <p className="text-xs text-slate-400">
            Analyze public GitHub repositories, inspect codebase structure, and extract commit history.
          </p>
        </div>

        <div className="relative" ref={historyRef}>
          <div className="flex items-center space-x-2">
            <span className="text-xs text-slate-400 font-mono">History:</span>
            <button
              type="button"
              onClick={() => setIsHistoryOpen((prev) => !prev)}
              className="flex items-center justify-between gap-2 bg-slate-900 border border-slate-800 hover:border-slate-700 rounded px-2.5 py-1 text-xs text-slate-200 font-mono outline-none focus:border-indigo-500 transition-colors"
              aria-expanded={isHistoryOpen}
              aria-haspopup="true"
            >
              <span className="truncate max-w-[200px] sm:max-w-[240px]">
                {selectedRepo
                  ? `${selectedRepo.owner}/${selectedRepo.name}`
                  : analyzedRepos.length > 0
                  ? 'Select repository...'
                  : 'No repository history'}
              </span>
              <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform ${isHistoryOpen ? 'rotate-180' : ''}`} />
            </button>
          </div>

          {isHistoryOpen && (
            <div className="absolute right-0 mt-1.5 w-80 sm:w-96 bg-slate-900 border border-slate-800 rounded-md shadow-xl z-50 overflow-hidden text-xs">
              {historyError && (
                <div className="p-2.5 bg-red-950/60 border-b border-red-800/60 text-red-300 flex items-center justify-between text-xs" role="alert">
                  <div className="flex items-center space-x-1.5 truncate">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0 text-red-400" />
                    <span className="truncate">{historyError}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setHistoryError(null)}
                    className="text-red-400 hover:text-red-200 ml-2"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              )}

              {analyzedRepos.length === 0 ? (
                <div className="p-4 text-center space-y-1">
                  <p className="font-semibold text-slate-300">No repository history yet.</p>
                  <p className="text-slate-400">Analyze a public GitHub repository to see it here.</p>
                </div>
              ) : (
                <div className="max-h-64 overflow-y-auto divide-y divide-slate-800/60">
                  {analyzedRepos.map((repo) => {
                    const isSelected = selectedRepo?.id === repo.id;
                    const isDeleting = deletingRepoId === repo.id;
                    return (
                      <div
                        key={repo.id}
                        onClick={() => {
                          loadRepositoryDetails(repo);
                          setIsHistoryOpen(false);
                        }}
                        className={`group flex items-center justify-between p-2.5 cursor-pointer transition-colors ${
                          isSelected ? 'bg-indigo-950/40 text-indigo-200' : 'hover:bg-slate-800/60 text-slate-200'
                        }`}
                      >
                        <div className="min-w-0 flex-1 pr-2">
                          <div className="flex items-center space-x-2">
                            <span className="font-mono font-medium truncate">
                              {repo.owner}/{repo.name}
                            </span>
                            {repo.primary_language && (
                              <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 border border-slate-700/50">
                                {repo.primary_language}
                              </span>
                            )}
                          </div>
                          {repo.analyzed_at && (
                            <p className="text-[10px] text-slate-400 mt-0.5">
                              {new Date(repo.analyzed_at).toLocaleDateString(undefined, {
                                month: 'short',
                                day: 'numeric',
                                year: 'numeric',
                              })}
                            </p>
                          )}
                        </div>

                        <button
                          type="button"
                          aria-label={`Remove ${repo.owner}/${repo.name} from history`}
                          disabled={isDeleting}
                          onClick={(e) => handleDeleteHistory(repo.id, e)}
                          className="p-1 rounded text-slate-400 hover:text-red-400 hover:bg-slate-800 transition-colors shrink-0 disabled:opacity-50"
                        >
                          {isDeleting ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin text-slate-400" />
                          ) : (
                            <X className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
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
