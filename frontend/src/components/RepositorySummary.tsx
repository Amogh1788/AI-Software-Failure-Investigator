import React from 'react';
import { GitBranch, ExternalLink, Code2, Files, FileCode, History, Calendar, CheckCircle2 } from 'lucide-react';
import type { Repository } from '../types';

interface RepositorySummaryProps {
  repository: Repository;
  commitsCount: number;
}

const LANGUAGE_COLORS: Record<string, string> = {
  Python: 'bg-blue-950/80 text-blue-400 border-blue-800/60',
  TypeScript: 'bg-sky-950/80 text-sky-400 border-sky-800/60',
  JavaScript: 'bg-yellow-950/80 text-yellow-400 border-yellow-800/60',
  Java: 'bg-amber-950/80 text-amber-400 border-amber-800/60',
  'C++': 'bg-pink-950/80 text-pink-400 border-pink-800/60',
  C: 'bg-slate-800 text-slate-300 border-slate-700',
  'C#': 'bg-purple-950/80 text-purple-400 border-purple-800/60',
  Go: 'bg-cyan-950/80 text-cyan-400 border-cyan-800/60',
  Rust: 'bg-orange-950/80 text-orange-400 border-orange-800/60',
  Ruby: 'bg-red-950/80 text-red-400 border-red-800/60',
  PHP: 'bg-indigo-950/80 text-indigo-400 border-indigo-800/60',
  Kotlin: 'bg-violet-950/80 text-violet-400 border-violet-800/60',
  Swift: 'bg-rose-950/80 text-rose-400 border-rose-800/60',
};

export const RepositorySummary: React.FC<RepositorySummaryProps> = ({ repository, commitsCount }) => {
  const formatDateTime = (dateStr?: string) => {
    if (!dateStr) return 'N/A';
    try {
      const date = new Date(dateStr);
      return new Intl.DateTimeFormat('en-US', {
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(date);
    } catch {
      return dateStr;
    }
  };

  const badgeColor =
    repository.primary_language && LANGUAGE_COLORS[repository.primary_language]
      ? LANGUAGE_COLORS[repository.primary_language]
      : 'bg-slate-800 text-slate-300 border-slate-700';

  return (
    <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-5 space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
        <div>
          <div className="flex items-center space-x-2">
            <h3 className="text-lg font-semibold text-slate-100 font-mono tracking-tight">
              {repository.owner} / <span className="text-indigo-400">{repository.name}</span>
            </h3>
            <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono bg-emerald-950/80 text-emerald-400 border border-emerald-800/60 whitespace-nowrap">
              <CheckCircle2 className="w-3 h-3 mr-1" />
              Analyzed
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {repository.description || 'Public GitHub Repository Analysis'}
          </p>
        </div>

        <a
          href={repository.github_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-mono text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 transition-colors shrink-0"
        >
          <span>View on GitHub</span>
          <ExternalLink className="w-3 h-3" />
        </a>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* Branch */}
        <div className="bg-slate-900/70 border border-slate-800/80 rounded p-3 space-y-1">
          <div className="flex items-center space-x-1.5 text-slate-400 text-xs font-mono">
            <GitBranch className="w-3.5 h-3.5 text-indigo-400" />
            <span>Branch</span>
          </div>
          <div className="text-sm font-semibold font-mono text-slate-200 truncate" title={repository.default_branch || 'main'}>
            {repository.default_branch || 'main'}
          </div>
        </div>

        {/* Primary Language */}
        <div className="bg-slate-900/70 border border-slate-800/80 rounded p-3 space-y-1">
          <div className="flex items-center space-x-1.5 text-slate-400 text-xs font-mono">
            <Code2 className="w-3.5 h-3.5 text-indigo-400" />
            <span>Language</span>
          </div>
          <div className="truncate">
            <span className={`inline-flex px-2 py-0.5 rounded text-xs font-mono font-medium border ${badgeColor}`}>
              {repository.primary_language || 'Detected'}
            </span>
          </div>
        </div>

        {/* Total Files */}
        <div className="bg-slate-900/70 border border-slate-800/80 rounded p-3 space-y-1">
          <div className="flex items-center space-x-1.5 text-slate-400 text-xs font-mono">
            <Files className="w-3.5 h-3.5 text-indigo-400" />
            <span>Total Files</span>
          </div>
          <div className="text-sm font-semibold font-mono text-slate-200">
            {repository.total_files.toLocaleString()}
          </div>
        </div>

        {/* Source Files */}
        <div className="bg-slate-900/70 border border-slate-800/80 rounded p-3 space-y-1">
          <div className="flex items-center space-x-1.5 text-slate-400 text-xs font-mono">
            <FileCode className="w-3.5 h-3.5 text-indigo-400" />
            <span>Source Files</span>
          </div>
          <div className="text-sm font-semibold font-mono text-slate-200">
            {repository.source_files.toLocaleString()}
          </div>
        </div>

        {/* Commits Analyzed */}
        <div className="bg-slate-900/70 border border-slate-800/80 rounded p-3 space-y-1">
          <div className="flex items-center space-x-1.5 text-slate-400 text-xs font-mono">
            <History className="w-3.5 h-3.5 text-indigo-400" />
            <span>Commits</span>
          </div>
          <div className="text-sm font-semibold font-mono text-slate-200">
            {commitsCount} analyzed
          </div>
        </div>

        {/* Analyzed Date */}
        <div className="bg-slate-900/70 border border-slate-800/80 rounded p-3 space-y-1">
          <div className="flex items-center space-x-1.5 text-slate-400 text-xs font-mono">
            <Calendar className="w-3.5 h-3.5 text-indigo-400" />
            <span>Analyzed At</span>
          </div>
          <div className="text-[11px] font-mono text-slate-300 truncate" title={formatDateTime(repository.analyzed_at)}>
            {formatDateTime(repository.analyzed_at)}
          </div>
        </div>
      </div>
    </div>
  );
};
