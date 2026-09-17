import React from 'react';
import { GitBranch, FileText, ScrollText, AlertTriangle, Cpu, ArrowRight, Lock } from 'lucide-react';

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
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold tracking-wide text-slate-200 uppercase font-mono">
            Investigation Engine Pipeline
          </h2>
          <p className="text-xs text-slate-400">
            Preview of multi-modal failure correlation engine scheduled for future phases.
          </p>
        </div>
        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono text-slate-400 bg-slate-800/80 border border-slate-700/60">
          <Lock className="w-3 h-3 mr-1" />
          Scheduled for Phase 2+
        </span>
      </div>

      <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-5 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
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

        <div className="flex items-center justify-center space-x-3 text-slate-400 font-mono text-xs py-1">
          <span className="hidden sm:inline">Repository</span>
          <span className="text-slate-400">+</span>
          <span className="hidden sm:inline">Bug Report</span>
          <span className="text-slate-400">+</span>
          <span className="hidden sm:inline">Logs</span>
          <span className="text-slate-400">+</span>
          <span className="hidden sm:inline">Stack Trace</span>
          <ArrowRight className="w-4 h-4 text-indigo-400" />
          <span className="text-slate-200 font-semibold">Investigation Engine</span>
        </div>

        <div className="bg-slate-900/80 border border-indigo-950 rounded-md p-4 flex items-start space-x-3.5">
          <div className="p-2 bg-indigo-500/10 border border-indigo-500/20 rounded text-indigo-400 mt-0.5">
            <Cpu className="w-4 h-4" />
          </div>
          <div className="space-y-1">
            <h3 className="text-xs font-semibold font-mono text-slate-200 uppercase tracking-wide">
              Future Investigation Engine Specification
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              <strong className="text-slate-300">Repository + Bug Report + Logs + Stack Trace</strong> will eventually be analyzed by the investigation engine. 
              In subsequent phases, correlation graphs and root-cause localization algorithms will ingest these multi-source telemetry feeds to pinpoint faulty commits, isolate line regressions, and formulate automated remediation plans.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};
