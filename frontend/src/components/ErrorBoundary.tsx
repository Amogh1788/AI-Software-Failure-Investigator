import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertOctagon, RotateCw, RefreshCcw, ChevronDown, ChevronUp } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  showDetails: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    showDetails: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, showDetails: false };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught React component error:', error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null, showDetails: false });
  };

  private handleReload = () => {
    window.location.reload();
  };

  private toggleDetails = () => {
    this.setState((prev) => ({ showDetails: !prev.showDetails }));
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div data-testid="error-boundary-ui" className="min-h-screen bg-[#0b0f19] text-slate-100 flex items-center justify-center p-4">
          <div className="max-w-lg w-full bg-[#0f172a] border border-red-900/60 rounded-xl p-6 sm:p-8 shadow-2xl space-y-6">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400">
                <AlertOctagon className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-base font-bold text-slate-100">
                  AI Software Failure Investigator
                </h1>
                <p className="text-xs text-red-400 font-mono">
                  Something went wrong in the user interface.
                </p>
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              An unexpected client-side rendering exception occurred. You can attempt to reset the application state or reload the page.
            </p>

            <div className="flex items-center space-x-3">
              <button
                onClick={this.handleReset}
                className="inline-flex items-center space-x-2 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-mono font-medium transition-colors cursor-pointer"
              >
                <RotateCw className="w-3.5 h-3.5" />
                <span>Retry</span>
              </button>

              <button
                onClick={this.handleReload}
                className="inline-flex items-center space-x-2 px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-xs font-mono font-medium transition-colors cursor-pointer"
              >
                <RefreshCcw className="w-3.5 h-3.5" />
                <span>Reload Page</span>
              </button>

              <button
                onClick={this.toggleDetails}
                className="inline-flex items-center space-x-1.5 px-3 py-2 text-xs font-mono text-slate-400 hover:text-slate-200 transition-colors ml-auto cursor-pointer"
              >
                <span>Diagnostics</span>
                {this.state.showDetails ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>
            </div>

            {this.state.showDetails && this.state.error && (
              <div className="bg-black/60 border border-slate-800 rounded p-3 text-[11px] font-mono text-slate-400 overflow-x-auto max-h-48">
                <p className="font-semibold text-red-300 mb-1">
                  {this.state.error.name}: {this.state.error.message}
                </p>
                <pre className="text-slate-500 text-[10px] whitespace-pre-wrap">
                  {this.state.error.stack || 'No client stack trace available.'}
                </pre>
              </div>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
