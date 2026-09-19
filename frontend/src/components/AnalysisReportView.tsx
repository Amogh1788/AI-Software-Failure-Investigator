import React from 'react';
import type { InvestigationAnalysis, FailureCandidate, FailureChainStep, RelevantCommit } from '../types';

interface AnalysisReportViewProps {
  analysis: InvestigationAnalysis;
  onReanalyze?: () => void;
  isAnalyzing?: boolean;
}

export const AnalysisReportView: React.FC<AnalysisReportViewProps> = ({
  analysis,
  onReanalyze,
  isAnalyzing = false,
}) => {
  const topCandidate = analysis.ranked_candidates[0] as FailureCandidate | undefined;
  const topScore = topCandidate ? topCandidate.evidence_score : 0;
  const topStrength = topCandidate ? topCandidate.evidence_strength : 'low';

  const getStrengthBadgeClass = (strength: string) => {
    switch (strength) {
      case 'high':
        return 'bg-emerald-950/60 text-emerald-400 border-emerald-700/50';
      case 'moderate':
      case 'medium':
        return 'bg-amber-950/60 text-amber-400 border-amber-700/50';
      case 'low':
      default:
        return 'bg-zinc-800 text-zinc-400 border-zinc-700';
    }
  };

  const getSourceBadgeClass = (source: string) => {
    const s = source.toLowerCase();
    if (s.includes('stack')) return 'bg-red-950/50 text-red-300 border-red-800/40';
    if (s.includes('test')) return 'bg-amber-950/50 text-amber-300 border-amber-800/40';
    if (s.includes('log')) return 'bg-blue-950/50 text-blue-300 border-blue-800/40';
    if (s.includes('bug') || s.includes('report')) return 'bg-purple-950/50 text-purple-300 border-purple-800/40';
    return 'bg-zinc-800 text-zinc-400 border-zinc-700';
  };

  return (
    <div className="space-y-6">
      {/* Header Banner & Score */}
      <div className="p-5 bg-gradient-to-br from-zinc-900 via-zinc-900/90 to-zinc-950 border border-zinc-800 rounded-xl shadow-lg">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide bg-indigo-950/70 text-indigo-400 border border-indigo-800/60">
                ENGINE v{analysis.engine_version}
              </span>
              <span className="text-xs text-zinc-400">
                Run: {new Date(analysis.created_at).toLocaleString()}
              </span>
              {analysis.run_duration_ms > 0 && (
                <span className="text-xs text-zinc-500 font-mono">
                  ({analysis.run_duration_ms}ms)
                </span>
              )}
            </div>
            <h3 className="text-lg font-bold text-zinc-100 flex items-center gap-2">
              <svg className="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              Deterministic Evidence Correlation Report
            </h3>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right">
              <div className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                Top Defect Evidence Score
              </div>
              <div className="flex items-baseline justify-end gap-2 mt-0.5">
                <span className="text-3xl font-extrabold text-indigo-400 tracking-tight">
                  {(topScore * 100).toFixed(1)}%
                </span>
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border uppercase tracking-wider ${getStrengthBadgeClass(
                    topStrength
                  )}`}
                >
                  {topStrength} strength
                </span>
              </div>
            </div>

            {onReanalyze && (
              <button
                type="button"
                onClick={onReanalyze}
                disabled={isAnalyzing}
                className="inline-flex items-center gap-2 px-3 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-zinc-800 disabled:text-zinc-600 text-white rounded-lg text-xs font-medium transition shadow-sm cursor-pointer disabled:cursor-not-allowed"
              >
                {isAnalyzing ? (
                  <>
                    <svg className="animate-spin -ml-0.5 h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Re-analyzing...
                  </>
                ) : (
                  <>
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Re-run Engine
                  </>
                )}
              </button>
            )}
          </div>
        </div>

        {/* Mandatory Explicit Disclaimer */}
        <div className="mt-4 p-3 bg-zinc-950/80 border border-zinc-800/80 rounded-lg flex items-start gap-2.5">
          <svg className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="text-xs text-zinc-300 leading-relaxed">
            <span className="font-semibold text-zinc-200">Notice:</span> {analysis.evidence_signals.score_disclaimer || "Evidence score is a weighted measure of supporting evidence and is not a probability."}
            <div className="mt-1">
              Computed using: <code className="text-zinc-300 font-mono text-[11px]">{analysis.evidence_signals.score_formula}</code>
            </div>
          </div>
        </div>
      </div>

      {/* Signals Summary Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-lg">
          <div className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider">Stack Trace Signal</div>
          <div className="text-xl font-bold text-red-400 mt-1">
            {(analysis.evidence_signals.stack_trace_signal * 100).toFixed(0)}%
          </div>
        </div>
        <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-lg">
          <div className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider">Test Failure Signal</div>
          <div className="text-xl font-bold text-amber-400 mt-1">
            {(analysis.evidence_signals.test_failure_signal * 100).toFixed(0)}%
          </div>
        </div>
        <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-lg">
          <div className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider">Logs TF-IDF</div>
          <div className="text-xl font-bold text-blue-400 mt-1">
            {(analysis.evidence_signals.logs_tfidf_signal * 100).toFixed(0)}%
          </div>
        </div>
        <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-lg">
          <div className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider">Bug Report TF-IDF</div>
          <div className="text-xl font-bold text-purple-400 mt-1">
            {(analysis.evidence_signals.bug_report_tfidf_signal * 100).toFixed(0)}%
          </div>
        </div>
        <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-lg">
          <div className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider">Git History Signal</div>
          <div className="text-xl font-bold text-emerald-400 mt-1">
            {(analysis.evidence_signals.git_history_signal * 100).toFixed(0)}%
          </div>
        </div>
      </div>

      {/* Executive Summary */}
      <div className="p-5 bg-zinc-900 border border-zinc-800 rounded-xl space-y-2">
        <h4 className="text-sm font-semibold text-zinc-200 uppercase tracking-wider flex items-center gap-2">
          <svg className="w-4 h-4 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Executive Summary
        </h4>
        <p className="text-sm text-zinc-300 leading-relaxed font-sans bg-zinc-950/60 p-3 rounded-lg border border-zinc-800/60 whitespace-pre-line">
          {analysis.summary}
        </p>
      </div>

      {/* Ranked Defect Candidates */}
      <div className="p-5 bg-zinc-900 border border-zinc-800 rounded-xl space-y-4">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-zinc-200 uppercase tracking-wider flex items-center gap-2">
            <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
            </svg>
            Ranked Suspect Source Files ({analysis.ranked_candidates.length})
          </h4>
          <span className="text-xs text-zinc-500 font-mono">Ranked by evidence_score</span>
        </div>

        {analysis.ranked_candidates.length === 0 ? (
          <div className="text-center py-6 text-zinc-500 text-sm">
            No source file candidates identified from available evidence.
          </div>
        ) : (
          <div className="space-y-3">
            {analysis.ranked_candidates.map((candidate: FailureCandidate, idx: number) => {
              const funcOrMethod = candidate.function_name || candidate.method_name;
              return (
                <div
                  key={candidate.file_path}
                  className="p-4 bg-zinc-950/60 border border-zinc-800/80 rounded-lg space-y-3 hover:border-zinc-700 transition"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-start sm:items-center gap-3">
                      <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-zinc-800 text-zinc-200 font-bold text-xs shrink-0">
                        #{idx + 1}
                      </span>
                      <div>
                        <div className="font-mono text-sm font-medium text-indigo-300">
                          {candidate.file_path}
                        </div>
                        {(funcOrMethod || candidate.line_number) && (
                          <div className="text-xs text-zinc-400 font-mono mt-0.5">
                            {funcOrMethod && `function: ${funcOrMethod}() `}
                            {candidate.line_number && `line: ${candidate.line_number}`}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-start sm:self-auto">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border uppercase tracking-wider ${getStrengthBadgeClass(
                          candidate.evidence_strength
                        )}`}
                      >
                        {candidate.evidence_strength}
                      </span>
                      <span className="font-mono font-bold text-sm text-zinc-200">
                        {(candidate.evidence_score * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>

                  {/* Signals breakdown bar */}
                  <div className="grid grid-cols-5 gap-1.5 pt-2 border-t border-zinc-900 text-[11px] font-mono">
                    <div className="bg-zinc-900/80 p-1.5 rounded text-center">
                      <span className="text-zinc-500 block text-[9px] uppercase">Stack</span>
                      <span className="text-red-400 font-bold">{(candidate.signals.stack_trace_score * 100).toFixed(0)}%</span>
                    </div>
                    <div className="bg-zinc-900/80 p-1.5 rounded text-center">
                      <span className="text-zinc-500 block text-[9px] uppercase">Test</span>
                      <span className="text-amber-400 font-bold">{(candidate.signals.test_failure_score * 100).toFixed(0)}%</span>
                    </div>
                    <div className="bg-zinc-900/80 p-1.5 rounded text-center">
                      <span className="text-zinc-500 block text-[9px] uppercase">Log</span>
                      <span className="text-blue-400 font-bold">{(candidate.signals.logs_score * 100).toFixed(0)}%</span>
                    </div>
                    <div className="bg-zinc-900/80 p-1.5 rounded text-center">
                      <span className="text-zinc-500 block text-[9px] uppercase">Report</span>
                      <span className="text-purple-400 font-bold">{(candidate.signals.bug_report_score * 100).toFixed(0)}%</span>
                    </div>
                    <div className="bg-zinc-900/80 p-1.5 rounded text-center">
                      <span className="text-zinc-500 block text-[9px] uppercase">Git</span>
                      <span className="text-emerald-400 font-bold">{(candidate.signals.git_recency_score * 100).toFixed(0)}%</span>
                    </div>
                  </div>

                  {/* Supporting evidence bullets */}
                  {candidate.supporting_evidence.length > 0 && (
                    <div className="pt-2">
                      <div className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider mb-1">
                        Supporting Evidence
                      </div>
                      <ul className="space-y-1">
                        {candidate.supporting_evidence.map((evidence, eIdx) => (
                          <li key={eIdx} className="text-xs text-zinc-300 flex items-start gap-2">
                            <span className="text-indigo-400 mt-0.5">•</span>
                            <span>{evidence}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Probable Failure Chain */}
      <div className="p-5 bg-zinc-900 border border-zinc-800 rounded-xl space-y-4">
        <h4 className="text-sm font-semibold text-zinc-200 uppercase tracking-wider flex items-center gap-2">
          <svg className="w-4 h-4 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          Probable Failure Chain ({analysis.failure_chain.length} Steps)
        </h4>

        {analysis.failure_chain.length === 0 ? (
          <div className="text-center py-6 text-zinc-500 text-sm">
            Insufficient correlated evidence to construct failure chain.
          </div>
        ) : (
          <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-zinc-800">
            {analysis.failure_chain.map((step: FailureChainStep) => (
              <div key={step.step_number} className="relative group">
                <div className="absolute -left-6 top-1.5 w-5 h-5 rounded-full bg-zinc-900 border-2 border-indigo-500 text-indigo-400 flex items-center justify-center text-[10px] font-bold">
                  {step.step_number}
                </div>
                <div className="p-3.5 bg-zinc-950/60 border border-zinc-800/80 rounded-lg space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium border uppercase tracking-wider ${getSourceBadgeClass(
                        step.source
                      )}`}
                    >
                      {step.phase} • {step.source}
                    </span>
                    {step.location && (
                      <span className="text-xs font-mono text-zinc-400">
                        {step.location}
                      </span>
                    )}
                  </div>
                  <div className="font-semibold text-xs text-zinc-200">{step.title}</div>
                  <p className="text-xs text-zinc-300 leading-relaxed">
                    {step.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Correlated Git Commits */}
      <div className="p-5 bg-zinc-900 border border-zinc-800 rounded-xl space-y-4">
        <h4 className="text-sm font-semibold text-zinc-200 uppercase tracking-wider flex items-center gap-2">
          <svg className="w-4 h-4 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Correlated Git History ({analysis.relevant_commits.length} Recent Commits)
        </h4>

        {analysis.relevant_commits.length === 0 ? (
          <div className="text-center py-6 text-zinc-500 text-sm">
            No recent commits directly touched the suspect source files.
          </div>
        ) : (
          <div className="space-y-3">
            {analysis.relevant_commits.map((commit: RelevantCommit) => (
              <div
                key={commit.commit_hash}
                className="p-3.5 bg-zinc-950/60 border border-zinc-800/80 rounded-lg space-y-2"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-purple-300 bg-purple-950/50 px-2 py-0.5 rounded border border-purple-800/50">
                      {commit.commit_hash.slice(0, 7)}
                    </span>
                    <span className="text-xs font-medium text-zinc-200">
                      {commit.commit_message.split('\n')[0]}
                    </span>
                  </div>
                  <div className="text-xs text-zinc-400">
                    {commit.author_name || 'Git'} • {commit.committed_at ? new Date(commit.committed_at).toLocaleDateString() : 'Recent'}
                  </div>
                </div>

                <div className="text-xs text-zinc-400 flex items-start gap-2">
                  <span className="text-purple-400 font-semibold text-[11px] uppercase tracking-wide shrink-0">
                    Relevance:
                  </span>
                  <span>{commit.relevance_reason}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
