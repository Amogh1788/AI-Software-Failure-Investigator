import React, { useState } from 'react';
import {
  Bug,
  FileText,
  Terminal,
  Trash2,
  Copy,
  Check,
  PlusCircle,
  Clock,
  Layers,
  FileCode,
} from 'lucide-react';
import type { InvestigationEvidence, EvidenceType } from '../types';

interface EvidencePanelProps {
  evidence: InvestigationEvidence[];
  onDeleteEvidence: (evidenceId: string) => Promise<void>;
  onAddClick: (type: EvidenceType) => void;
}

const CATEGORIES: { type: EvidenceType; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { type: 'bug_report', label: 'Bug Report', icon: Bug },
  { type: 'application_log', label: 'Application Logs', icon: FileText },
  { type: 'stack_trace', label: 'Stack Trace', icon: Terminal },
  { type: 'test_output', label: 'Failing Test Output', icon: FileCode },
];

export const EvidencePanel: React.FC<EvidencePanelProps> = ({
  evidence,
  onDeleteEvidence,
  onAddClick,
}) => {
  const [activeTab, setActiveTab] = useState<EvidenceType>('bug_report');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const copyContent = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('Are you sure you want to remove this evidence item?')) return;
    setDeletingId(id);
    try {
      await onDeleteEvidence(id);
    } finally {
      setDeletingId(null);
    }
  };

  // Group evidence by type
  const itemsByType = evidence.filter((item) => item.evidence_type === activeTab);

  return (
    <div className="bg-[#0f172a] border border-slate-800 rounded-lg overflow-hidden space-y-0">
      {/* Category Tabs */}
      <div className="flex border-b border-slate-800/80 bg-slate-900/50 overflow-x-auto">
        {CATEGORIES.map(({ type, label, icon: Icon }) => {
          const count = evidence.filter((e) => e.evidence_type === type).length;
          const isSelected = activeTab === type;

          return (
            <button
              key={type}
              onClick={() => setActiveTab(type)}
              className={`flex items-center space-x-2 px-4 py-3 text-xs font-mono border-b-2 transition-colors whitespace-nowrap cursor-pointer ${
                isSelected
                  ? 'border-indigo-500 text-slate-100 bg-slate-800/60 font-semibold'
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/30'
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isSelected ? 'text-indigo-400' : 'text-slate-400'}`} />
              <span>{label}</span>
              <span
                className={`px-1.5 py-0.2 rounded text-[10px] ${
                  count > 0
                    ? 'bg-indigo-950 text-indigo-300 border border-indigo-800/50'
                    : 'bg-slate-800 text-slate-400'
                }`}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Category Content Area */}
      <div className="p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono text-slate-400">
              Showing {itemsByType.length} item{itemsByType.length === 1 ? '' : 's'} for{' '}
              <strong className="text-slate-200">{CATEGORIES.find((c) => c.type === activeTab)?.label}</strong>
            </span>
          </div>

          <button
            onClick={() => onAddClick(activeTab)}
            className="inline-flex items-center space-x-1 px-3 py-1.5 rounded text-xs font-mono text-indigo-300 bg-indigo-950/60 hover:bg-indigo-900/60 border border-indigo-800/60 transition-colors cursor-pointer"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>Add {CATEGORIES.find((c) => c.type === activeTab)?.label}</span>
          </button>
        </div>

        {itemsByType.length === 0 ? (
          <div className="p-8 border border-dashed border-slate-800 rounded-md text-center space-y-3 bg-slate-900/30">
            <Layers className="w-8 h-8 text-slate-600 mx-auto" />
            <div className="space-y-1">
              <p className="text-xs text-slate-300 font-mono">No evidence attached in this category yet.</p>
              <p className="text-[11px] text-slate-400">
                Provide ground-truth failure artifacts to prepare this case for investigation.
              </p>
            </div>
            <button
              onClick={() => onAddClick(activeTab)}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-mono bg-indigo-600 hover:bg-indigo-500 text-white transition-colors cursor-pointer"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              <span>Attach {CATEGORIES.find((c) => c.type === activeTab)?.label}</span>
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {itemsByType.map((item) => (
              <div
                key={item.id}
                className="bg-slate-950/70 border border-slate-800 rounded-lg p-4 space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-2.5">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-semibold text-slate-200 font-mono">
                      {item.title || item.evidence_type.replace('_', ' ').toUpperCase()}
                    </span>
                    {item.filename && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-mono text-slate-400 bg-slate-900 border border-slate-800">
                        {item.filename}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center space-x-3 text-xs font-mono text-slate-400">
                    <span className="text-slate-400">
                      {(item.byte_size / 1024).toFixed(1)} KB ({item.byte_size} bytes)
                    </span>
                    <span className="text-slate-400 inline-flex items-center">
                      <Clock className="w-3 h-3 mr-1" />
                      {new Date(item.created_at).toLocaleDateString()}
                    </span>

                    <button
                      onClick={() => copyContent(item.id, item.content)}
                      className="p-1 text-slate-400 hover:text-slate-200 rounded hover:bg-slate-800 transition-colors cursor-pointer"
                      title="Copy content"
                    >
                      {copiedId === item.id ? (
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>

                    <button
                      onClick={() => handleDelete(item.id)}
                      disabled={deletingId === item.id}
                      className="p-1 text-slate-400 hover:text-red-400 rounded hover:bg-slate-800 transition-colors cursor-pointer disabled:opacity-50"
                      title="Delete evidence"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Content View */}
                <div className="relative bg-[#0b0f19] border border-slate-800/90 rounded p-3 max-h-72 overflow-y-auto">
                  <pre
                    className={`text-xs text-slate-300 whitespace-pre-wrap break-all leading-relaxed ${
                      item.evidence_type === 'bug_report' ? 'font-sans' : 'font-mono text-[11px]'
                    }`}
                  >
                    {item.content}
                  </pre>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
