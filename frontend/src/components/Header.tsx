import React from 'react';
import { Terminal, RefreshCw, Layers, LogOut, User as UserIcon } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface HeaderProps {
  onRefresh: () => void;
  isRefreshing: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onRefresh, isRefreshing }) => {
  const { user, signOut } = useAuth();

  return (
    <header className="border-b border-slate-800 bg-[#0d1322]/80 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl 2xl:max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-indigo-500/10 border border-indigo-500/20 rounded-md text-indigo-400 shrink-0">
            <Terminal className="w-5 h-5" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center space-x-2">
              <h1 className="text-base font-semibold tracking-tight text-slate-100 whitespace-nowrap">
                AI Software Failure Investigator
              </h1>
              <span
                data-testid="header-phase-badge"
                className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono uppercase font-semibold bg-indigo-950/80 text-indigo-400 border border-indigo-800/60 whitespace-nowrap"
              >
                PRODUCTION MVP • v1.0.0
              </span>
            </div>
            <p className="text-xs text-slate-400 truncate">
              AI-assisted software failure investigation and root-cause analysis.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3 shrink-0">
          <div className="hidden lg:flex items-center space-x-2 text-xs text-slate-400 font-mono bg-slate-900/60 border border-slate-800 px-2.5 py-1.5 rounded whitespace-nowrap">
            <Layers className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <span>Stack: React &bull; FastAPI &bull; Supabase</span>
          </div>

          {user && (
            <div className="flex items-center space-x-2 bg-slate-900/80 border border-slate-800 px-2.5 py-1 rounded text-xs font-mono text-slate-300">
              <UserIcon className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
              <span className="hidden sm:inline max-w-[160px] truncate">{user.email}</span>
              <button
                onClick={() => signOut()}
                className="ml-1 text-slate-400 hover:text-red-400 transition-colors cursor-pointer"
                title="Sign out"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer select-none"
            title="Refresh projects"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-indigo-400' : ''}`} />
            <span>{isRefreshing ? 'Refreshing...' : 'Refresh'}</span>
          </button>
        </div>
      </div>
    </header>
  );
};
