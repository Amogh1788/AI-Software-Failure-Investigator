import React, { useState, useEffect } from 'react';
import {
  FolderGit2,
  Clock,
  CheckCircle2,
  FileEdit,
  AlertCircle,
  Cpu,
  PlusCircle,
  X,
  ShieldCheck,
  Bug,
  FileText,
  Terminal,
  FileCode,
  Play,
  RotateCw,
} from 'lucide-react';
import type {
  InvestigationDetail as IDetail,
  Investigation,
  EvidenceType,
  CreateEvidencePayload,
  InvestigationStatus,
  InvestigationAnalysis,
} from '../types';
import {
  getInvestigation,
  updateInvestigation,
  addEvidence,
  deleteEvidence,
  analyzeInvestigation,
  getInvestigationAnalysis,
} from '../services/api';
import { EvidencePanel } from './EvidencePanel';
import { EvidenceEditor } from './EvidenceEditor';
import { AnalysisReportView } from './AnalysisReportView';

interface InvestigationDetailProps {
  investigationId: string;
  onClose: () => void;
  onUpdated?: (updated?: Investigation) => void;
}

const REQUIRED_CATEGORIES: { type: EvidenceType; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { type: 'bug_report', label: 'Bug Report', icon: Bug },
  { type: 'application_log', label: 'App Logs', icon: FileText },
  { type: 'stack_trace', label: 'Stack Trace', icon: Terminal },
  { type: 'test_output', label: 'Test Output', icon: FileCode },
];

export const InvestigationDetail: React.FC<InvestigationDetailProps> = ({
  investigationId,
  onClose,
  onUpdated,
}) => {
  const [detail, setDetail] = useState<IDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [showEditor, setShowEditor] = useState(false);
  const [editorDefaultType, setEditorDefaultType] = useState<EvidenceType>('bug_report');
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [analysis, setAnalysis] = useState<InvestigationAnalysis | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getInvestigation(investigationId);
      setDetail(data);

      // Attempt to load latest analysis run
      try {
        const analysisData = await getInvestigationAnalysis(investigationId);
        setAnalysis(analysisData);
      } catch {
        // No analysis run yet
        setAnalysis(null);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load investigation details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [investigationId]);

  const handleStatusToggle = async () => {
    if (!detail) return;
    const currentStatus = detail.investigation.status;
    const nextStatus: InvestigationStatus =
      currentStatus === 'ready' || currentStatus === 'completed' ? 'draft' : 'ready';

    setIsUpdatingStatus(true);
    setStatusMessage(null);
    setError(null);

    try {
      const updated = await updateInvestigation(investigationId, {
        status: nextStatus,
      });
      setDetail((prev) => (prev ? { ...prev, investigation: updated } : null));
      onUpdated?.(updated);
      setStatusMessage(`Case status updated to "${nextStatus.toUpperCase()}".`);
      setTimeout(() => setStatusMessage(null), 3000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to update status');
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  const handleRunAnalysis = async () => {
    setIsAnalyzing(true);
    setError(null);
    setStatusMessage(null);

    // Optimistically update local and notify parent that analysis is in progress
    if (detail) {
      const analyzingInv: Investigation = {
        ...detail.investigation,
        status: 'analyzing',
      };
      setDetail({ ...detail, investigation: analyzingInv });
      onUpdated?.(analyzingInv);
    }

    try {
      const result = await analyzeInvestigation(investigationId);
      setAnalysis(result);
      const refreshedDetail = await getInvestigation(investigationId);
      setDetail(refreshedDetail);
      onUpdated?.(refreshedDetail.investigation);
      setStatusMessage('Investigation analysis completed successfully.');
      setTimeout(() => setStatusMessage(null), 4000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Investigation analysis failed');
      try {
        const revertedDetail = await getInvestigation(investigationId);
        setDetail(revertedDetail);
        onUpdated?.(revertedDetail.investigation);
      } catch {
        // ignore
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleAddEvidence = async (payload: CreateEvidencePayload) => {
    await addEvidence(investigationId, payload);
    await loadData();
    setShowEditor(false);
    onUpdated?.();
  };

  const handleDeleteEvidence = async (evidenceId: string) => {
    await deleteEvidence(investigationId, evidenceId);
    await loadData();
    onUpdated?.();
  };

  const handleOpenEditor = (type: EvidenceType) => {
    setEditorDefaultType(type);
    setShowEditor(true);
  };

  if (loading) {
    return (
      <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-12 text-center space-y-3">
        <span className="inline-block w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-xs text-slate-400 font-mono">Loading investigation case details...</p>
      </div>
    );
  }

  if (error && !detail) {
    return (
      <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-6 space-y-4">
        <div className="p-3 bg-red-950/40 border border-red-800/60 rounded text-xs text-red-200 flex items-start space-x-2">
          <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
        <button
          onClick={onClose}
          className="px-3 py-1.5 rounded text-xs font-mono text-slate-300 bg-slate-800 hover:bg-slate-700 transition-colors cursor-pointer"
        >
          Back to List
        </button>
      </div>
    );
  }

  if (!detail) return null;

  const { investigation, repository, evidence } = detail;
  const linkedRepo = repository || investigation.repository;
  const isReady = investigation.status === 'ready';
  const isCompleted = investigation.status === 'completed';
  const isAnalyzingStatus = investigation.status === 'analyzing' || isAnalyzing;

  // Check which of the 4 required categories are covered
  const coveredTypes = new Set(evidence.map((e) => e.evidence_type));
  const isAllFourCovered = REQUIRED_CATEGORIES.every((c) => coveredTypes.has(c.type));

  return (
    <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-6 space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="space-y-2">
          <div className="flex items-center space-x-2.5">
            <h2 className="text-base font-semibold text-slate-100 font-sans tracking-tight">
              {investigation.title}
            </h2>
            {isCompleted ? (
              <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded text-[11px] font-mono font-semibold uppercase bg-purple-950 text-purple-400 border border-purple-800">
                <CheckCircle2 className="w-3.5 h-3.5 text-purple-400" />
                <span>Completed</span>
              </span>
            ) : isAnalyzingStatus ? (
              <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded text-[11px] font-mono font-semibold uppercase bg-indigo-950 text-indigo-400 border border-indigo-800">
                <span className="inline-block w-3 h-3 border border-indigo-400 border-t-transparent rounded-full animate-spin" />
                <span>Analyzing</span>
              </span>
            ) : isReady ? (
              <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded text-[11px] font-mono font-semibold uppercase bg-emerald-950 text-emerald-400 border border-emerald-800">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Ready</span>
              </span>
            ) : (
              <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded text-[11px] font-mono font-semibold uppercase bg-amber-950 text-amber-400 border border-amber-800">
                <FileEdit className="w-3.5 h-3.5" />
                <span>Draft</span>
              </span>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400 font-mono">
            {linkedRepo ? (
              <span className="flex items-center space-x-1 text-slate-300">
                <FolderGit2 className="w-3.5 h-3.5 text-indigo-400" />
                <span>
                  {linkedRepo.owner}/{linkedRepo.name}
                </span>
              </span>
            ) : (
              <span className="flex items-center space-x-1 text-slate-400">
                <FolderGit2 className="w-3.5 h-3.5 text-slate-500" />
                <span>Repository unavailable</span>
              </span>
            )}
            <span className="flex items-center space-x-1">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              <span>Created: {new Date(investigation.created_at).toLocaleDateString()}</span>
            </span>
            <span className="flex items-center space-x-1">
              <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
              <span>{evidence.length} Evidence Artifacts</span>
            </span>
          </div>

          {investigation.description && (
            <p className="text-xs text-slate-400 leading-relaxed max-w-3xl pt-1">
              {investigation.description}
            </p>
          )}
        </div>

        <div className="flex items-center space-x-2 shrink-0">
          {/* Run / Re-run Engine Button */}
          {(isReady || isCompleted) && (
            <button
              onClick={handleRunAnalysis}
              disabled={isAnalyzingStatus}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-mono bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-600 text-white transition-colors cursor-pointer disabled:cursor-not-allowed shadow-sm"
              title={isCompleted ? "Re-run investigation analysis" : "Run investigation analysis"}
            >
              {isAnalyzingStatus ? (
                <>
                  <span className="inline-block w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" />
                  <span>Analyzing...</span>
                </>
              ) : isCompleted ? (
                <>
                  <RotateCw className="w-3.5 h-3.5" />
                  <span>Re-run Analysis</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Run Analysis</span>
                </>
              )}
            </button>
          )}

          {/* Status Toggle Button */}
          <button
            onClick={handleStatusToggle}
            disabled={isUpdatingStatus || isAnalyzingStatus}
            className={`inline-flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-mono transition-colors border cursor-pointer disabled:cursor-not-allowed ${
              isReady || isCompleted
                ? 'bg-slate-900 text-slate-300 border-slate-700 hover:bg-slate-800'
                : 'bg-emerald-950/80 text-emerald-300 border-emerald-800 hover:bg-emerald-900'
            }`}
            title={
              !isReady && !isCompleted && !isAllFourCovered
                ? 'All 4 evidence categories required to mark ready'
                : undefined
            }
          >
            {isUpdatingStatus ? (
              <span className="inline-block w-3 h-3 border border-current border-t-transparent rounded-full animate-spin" />
            ) : isReady || isCompleted ? (
              <>
                <FileEdit className="w-3.5 h-3.5 text-amber-400" />
                <span>Switch to Draft</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>Mark as Ready</span>
              </>
            )}
          </button>

          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-200 rounded hover:bg-slate-800 transition-colors cursor-pointer"
            title="Close detail view"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <div className="p-3 bg-red-950/40 border border-red-800/60 rounded text-xs text-red-200 flex items-start space-x-2">
          <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {statusMessage && (
        <div className="p-3 bg-emerald-950/40 border border-emerald-800/60 rounded text-xs text-emerald-200 flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{statusMessage}</span>
        </div>
      )}

      {/* 4-Category Evidence Readiness Checklist */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold font-mono text-slate-200 uppercase tracking-wide">
            Failure Evidence Readiness Checklist
          </span>
          <span className="text-xs font-mono text-slate-400">
            {coveredTypes.size} / 4 Categories Attached
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          {REQUIRED_CATEGORIES.map(({ type, label, icon: Icon }) => {
            const hasType = coveredTypes.has(type);
            return (
              <div
                key={type}
                className={`p-2.5 rounded border flex items-center justify-between text-xs font-mono ${
                  hasType
                    ? 'bg-emerald-950/20 border-emerald-800/40 text-emerald-300'
                    : 'bg-slate-950/40 border-slate-800 text-slate-400'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <Icon className={`w-3.5 h-3.5 ${hasType ? 'text-emerald-400' : 'text-slate-400'}`} />
                  <span>{label}</span>
                </div>
                {hasType ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <button
                    onClick={() => handleOpenEditor(type)}
                    className="text-[10px] text-indigo-400 hover:text-indigo-300 hover:underline cursor-pointer"
                  >
                    + Add
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Editor or Open Editor Button */}
      {showEditor ? (
        <EvidenceEditor
          investigationId={investigationId}
          defaultType={editorDefaultType}
          onEvidenceAdded={handleAddEvidence}
          onCancel={() => setShowEditor(false)}
        />
      ) : (
        <div className="flex justify-end">
          <button
            onClick={() => handleOpenEditor('bug_report')}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-mono bg-indigo-600 hover:bg-indigo-500 text-white transition-colors cursor-pointer"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>Attach Evidence Item</span>
          </button>
        </div>
      )}

      {/* Evidence Panels by Type */}
      <EvidencePanel
        evidence={evidence}
        onDeleteEvidence={handleDeleteEvidence}
        onAddClick={handleOpenEditor}
      />

      {/* Investigation Analysis Section */}
      {isAnalyzingStatus ? (
        <div className="bg-slate-900/60 border border-indigo-500/30 rounded-lg p-8 text-center space-y-3">
          <span className="inline-block w-8 h-8 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
          <h4 className="text-sm font-semibold text-indigo-300 font-mono">
            Running Investigation Analysis
          </h4>
          <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed font-mono">
            Performing multi-source correlation: parsing stack traces, correlating failing test outputs, matching error log tokens, scoring commit recency, and ranking suspect files.
          </p>
        </div>
      ) : analysis ? (
        <div className="border-t border-slate-800 pt-6">
          <AnalysisReportView
            analysis={analysis}
            onReanalyze={handleRunAnalysis}
            isAnalyzing={isAnalyzingStatus}
          />
        </div>
      ) : isReady ? (
        <div className="bg-gradient-to-r from-indigo-950/40 via-slate-900 to-indigo-950/40 border border-indigo-800/50 rounded-lg p-5 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="space-y-1 text-left">
            <span className="inline-flex items-center gap-1.5 text-xs font-mono font-semibold text-indigo-400 uppercase tracking-wide">
              <Cpu className="w-4 h-4" /> Ready for Investigation Analysis
            </span>
            <p className="text-xs text-slate-300">
              All 4 failure evidence categories are attached. Run investigation analysis to localize suspect defect files and synthesize a step-by-step causal failure chain.
            </p>
          </div>
          <button
            onClick={handleRunAnalysis}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-mono font-semibold transition shrink-0 shadow-md cursor-pointer"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Run Investigation Analysis</span>
          </button>
        </div>
      ) : (
        <div className="bg-slate-900/40 border border-slate-800/80 rounded-lg p-4 flex items-start space-x-3 text-xs text-slate-400">
          <div className="p-2 bg-indigo-500/10 border border-indigo-500/20 rounded text-indigo-400 shrink-0">
            <Cpu className="w-4 h-4" />
          </div>
          <div className="space-y-1">
            <span className="font-semibold font-mono text-slate-200 uppercase tracking-wide">
              Investigation Analysis
            </span>
            <p className="leading-relaxed text-slate-400">
              To run investigation analysis, attach evidence for all 4 required categories (bug report, runtime logs, stack traces, and test output) and switch the case status to <strong className="text-emerald-400">Ready</strong>.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
