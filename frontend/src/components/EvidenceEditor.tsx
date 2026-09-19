import React, { useState, useMemo } from 'react';
import { ShieldAlert, AlertTriangle, UploadCloud, FileText, Terminal, Bug, CheckCircle2 } from 'lucide-react';
import type { EvidenceType, CreateEvidencePayload } from '../types';

interface EvidenceEditorProps {
  investigationId: string;
  onEvidenceAdded: (newEvidence: CreateEvidencePayload) => Promise<void>;
  onCancel?: () => void;
  defaultType?: EvidenceType;
}

const LIMITS: Record<EvidenceType, { maxBytes: number; label: string }> = {
  bug_report: { maxBytes: 51200, label: '50 KB' },
  application_log: { maxBytes: 512000, label: '500 KB' },
  stack_trace: { maxBytes: 204800, label: '200 KB' },
  test_output: { maxBytes: 204800, label: '200 KB' },
};

export const EvidenceEditor: React.FC<EvidenceEditorProps> = ({
  onEvidenceAdded,
  onCancel,
  defaultType = 'bug_report',
}) => {
  const [evidenceType, setEvidenceType] = useState<EvidenceType>(defaultType);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [filename, setFilename] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState(false);

  const byteSize = useMemo(() => {
    return new TextEncoder().encode(content).length;
  }, [content]);

  const maxLimit = LIMITS[evidenceType].maxBytes;
  const isOversized = byteSize > maxLimit;
  const percentage = Math.min(100, Math.round((byteSize / maxLimit) * 100));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) {
      setErrorMessage('Evidence content cannot be empty.');
      return;
    }

    if (isOversized) {
      setErrorMessage(
        `Payload (${(byteSize / 1024).toFixed(1)} KB) exceeds the maximum limit of ${LIMITS[evidenceType].label}.`
      );
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await onEvidenceAdded({
        evidence_type: evidenceType,
        title: title.trim() || undefined,
        content,
        filename: filename.trim() || undefined,
      });

      setSuccessNotice(true);
      setTimeout(() => {
        setContent('');
        setTitle('');
        setFilename('');
        setSuccessNotice(false);
      }, 1200);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to save evidence';
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const isMonospace = evidenceType !== 'bug_report';

  return (
    <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-5 space-y-5">
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
        <div className="flex items-center space-x-2">
          <UploadCloud className="w-4 h-4 text-indigo-400" />
          <h3 className="text-sm font-semibold font-mono text-slate-100 uppercase tracking-wide">
            Attach Failure Evidence
          </h3>
        </div>
        <span className="text-xs font-mono text-slate-400">
          Max Limit: <span className="text-slate-200 font-semibold">{LIMITS[evidenceType].label}</span>
        </span>
      </div>

      {/* Security Warning Banner */}
      <div className="bg-amber-950/20 border border-amber-800/40 rounded-md p-3 flex items-start space-x-2.5 text-xs text-amber-200">
        <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          <strong className="text-amber-300">Security Warning:</strong> Do not submit passwords, API keys, access tokens,
          or other confidential secrets in evidence payloads.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Evidence Category Selector */}
        <div>
          <label className="block text-xs font-mono text-slate-300 mb-1.5 uppercase tracking-wider">
            Evidence Category *
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {[
              { type: 'bug_report' as EvidenceType, label: 'Bug Report', icon: Bug },
              { type: 'application_log' as EvidenceType, label: 'App Logs', icon: FileText },
              { type: 'stack_trace' as EvidenceType, label: 'Stack Trace', icon: Terminal },
              { type: 'test_output' as EvidenceType, label: 'Test Output', icon: Terminal },
            ].map(({ type, label, icon: Icon }) => {
              const selected = evidenceType === type;
              return (
                <button
                  key={type}
                  type="button"
                  onClick={() => {
                    setEvidenceType(type);
                    setErrorMessage(null);
                  }}
                  className={`flex items-center justify-center space-x-1.5 px-3 py-2 rounded text-xs font-mono transition-colors border cursor-pointer ${
                    selected
                      ? 'bg-indigo-600/20 text-indigo-300 border-indigo-500 font-semibold'
                      : 'bg-slate-900/60 text-slate-400 border-slate-800 hover:text-slate-200 hover:border-slate-700'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Title & Filename Fields */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1">
              Title / Summary <span className="text-slate-500">(Optional)</span>
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={
                evidenceType === 'bug_report'
                  ? 'e.g. 504 Gateway Timeout during flash sale'
                  : 'e.g. production-auth-worker.log'
              }
              className="w-full bg-slate-900 border border-slate-700/80 rounded px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1">
              Source Filename / Tag <span className="text-slate-500">(Optional)</span>
            </label>
            <input
              type="text"
              value={filename}
              onChange={(e) => setFilename(e.target.value)}
              placeholder="e.g. app.log, pytest_run.txt, issue_402.md"
              className="w-full bg-slate-900 border border-slate-700/80 rounded px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
            />
          </div>
        </div>

        {/* Content Field with Monospace styling for code/logs */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-xs font-mono text-slate-300">
              {evidenceType === 'bug_report' ? 'Report Description & Steps *' : 'Evidence Payload *'}
            </label>
            <div className="flex items-center space-x-2 text-[11px] font-mono">
              <span className={isOversized ? 'text-red-400 font-semibold' : 'text-slate-400'}>
                {(byteSize / 1024).toFixed(1)} KB / {LIMITS[evidenceType].label} ({percentage}%)
              </span>
            </div>
          </div>

          <div className="relative">
            <textarea
              rows={8}
              value={content}
              onChange={(e) => {
                setContent(e.target.value);
                if (errorMessage) setErrorMessage(null);
              }}
              placeholder={
                evidenceType === 'bug_report'
                  ? 'Describe the failure, steps to reproduce, expected behavior, and observed error...'
                  : evidenceType === 'application_log'
                  ? 'Paste raw stdout/stderr application logs with timestamps...'
                  : evidenceType === 'stack_trace'
                  ? 'Paste exception stack frames, callpath, and tracebacks...'
                  : 'Paste failing test execution log, assertion errors, and failure diff...'
              }
              className={`w-full bg-slate-950 border rounded p-3 text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-indigo-500 leading-relaxed ${
                isMonospace ? 'font-mono text-[11px]' : 'font-sans'
              } ${isOversized ? 'border-red-500/80' : 'border-slate-800'}`}
            />
          </div>

          {/* Limit Bar */}
          <div className="w-full bg-slate-800 rounded-full h-1 mt-1.5 overflow-hidden">
            <div
              className={`h-full transition-all ${
                isOversized
                  ? 'bg-red-500'
                  : percentage > 85
                  ? 'bg-amber-500'
                  : 'bg-indigo-500'
              }`}
              style={{ width: `${percentage}%` }}
            />
          </div>
        </div>

        {/* Error Notification */}
        {errorMessage && (
          <div className="p-3 bg-red-950/40 border border-red-800/60 rounded text-xs text-red-200 flex items-start space-x-2">
            <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Success Confirmation */}
        {successNotice && (
          <div className="p-3 bg-emerald-950/40 border border-emerald-800/60 rounded text-xs text-emerald-200 flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>Evidence saved successfully to Supabase!</span>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center justify-end space-x-3 pt-2">
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="px-3 py-1.5 rounded text-xs font-mono text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors cursor-pointer"
            >
              Cancel
            </button>
          )}
          <button
            type="submit"
            disabled={isSubmitting || isOversized || !content.trim()}
            className="inline-flex items-center space-x-1.5 px-4 py-2 rounded text-xs font-semibold font-mono bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-500 text-white shadow-sm transition-colors cursor-pointer disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <span className="inline-block w-3 h-3 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                <span>Saving Evidence...</span>
              </>
            ) : (
              <>
                <UploadCloud className="w-3.5 h-3.5" />
                <span>Save Evidence Item</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
