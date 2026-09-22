import React from 'react';
import { GitBranch, FileText, ScrollText, AlertTriangle, Cpu, ArrowDown, ShieldCheck, CheckCircle2 } from 'lucide-react';

export const FutureInvestigationArea: React.FC = () => {
  const inputs = [
    {
      title: 'Repository',
      desc: 'Git tree, commits, blame, code diffs',
      icon: GitBranch,
    },
    {
      title: 'Bug Report',
      desc: 'Issue description, repro steps, environment',
      icon: FileText,
    },
    {
      title: 'Application Logs',
      desc: 'Structured telemetry, stdout/stderr timestamps',
      icon: ScrollText,
    },
    {
      title: 'Stack Trace',
      desc: 'Exception hierarchies, stack frames, callpaths',
      icon: AlertTriangle,
    },
  ];

  return (
    <section data-testid="investigation-engine-architecture" className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold tracking-wide text-slate-200 uppercase font-mono flex items-center gap-2">
            <span>Investigation Intelligence Engine</span>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-emerald-950/70 text-emerald-400 border border-emerald-800/60 font-medium">
              <CheckCircle2 className="w-3 h-3 mr-1" /> Active
            </span>
          </h2>
          <p className="text-xs text-slate-400">
            Deterministic multi-source failure correlation engine architecture and pipeline.
          </p>
        </div>
        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-mono text-indigo-400 bg-indigo-950/60 border border-indigo-800/60">
          <ShieldCheck className="w-3.5 h-3.5 mr-1 text-indigo-400" />
          Explainable &bull; Zero-LLM
        </span>
      </div>

      <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-5 space-y-6">
        {/* Step 1: Input Evidence Sources */}
        <div>
          <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-2 font-semibold">
            1. Multi-Source Failure Ingestion
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {inputs.map((input) => {
              const Icon = input.icon;
              return (
                <div
                  key={input.title}
                  className="bg-slate-900/60 border border-slate-800 rounded-md p-3.5 space-y-2 relative"
                >
                  <div className="flex items-center space-x-2 text-indigo-400">
                    <Icon className="w-4 h-4" />
                    <span className="text-xs font-semibold uppercase tracking-wider font-mono text-slate-200">
                      {input.title}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    {input.desc}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Step 2: Causal Correlation Flow Pipeline */}
        <div className="bg-slate-900/80 border border-indigo-950/80 rounded-md p-4 space-y-3">
          <div className="flex items-center space-x-2 text-indigo-400 font-mono text-xs font-semibold uppercase tracking-wider">
            <Cpu className="w-4 h-4" />
            <span>2. Deterministic Pipeline Flow</span>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between gap-2 text-xs font-mono text-slate-300 py-1 overflow-x-auto">
            <div className="p-2 bg-slate-800/80 border border-slate-700 rounded text-center w-full sm:w-auto">
              Repository + 4 Evidence Feeds
            </div>
            <ArrowDown className="w-4 h-4 text-indigo-400 sm:-rotate-90 shrink-0" />
            <div className="p-2 bg-indigo-950/80 border border-indigo-800/80 rounded text-center w-full sm:w-auto text-indigo-300 font-semibold">
              Evidence Correlation (TF-IDF + Regex)
            </div>
            <ArrowDown className="w-4 h-4 text-indigo-400 sm:-rotate-90 shrink-0" />
            <div className="p-2 bg-slate-800/80 border border-slate-700 rounded text-center w-full sm:w-auto">
              Ranked Defect Candidates
            </div>
            <ArrowDown className="w-4 h-4 text-indigo-400 sm:-rotate-90 shrink-0" />
            <div className="p-2 bg-purple-950/80 border border-purple-800/80 rounded text-center w-full sm:w-auto text-purple-300 font-semibold">
              Failure Chain & Git Attribution
            </div>
          </div>

          <p className="text-xs text-slate-400 leading-relaxed pt-1">
            The Phase 4 engine evaluates candidate source files by calculating a weighted evidence score:
            <code className="text-[11px] text-indigo-300 bg-slate-950/80 px-1.5 py-0.5 rounded ml-1 border border-slate-800">
              0.35 &times; Stack + 0.25 &times; Test + 0.20 &times; Logs + 0.10 &times; Bug + 0.10 &times; Git
            </code>.
            Results are synthesized into an itemized causal failure chain and correlated Git commit history.
          </p>
        </div>
      </div>
    </section>
  );
};
