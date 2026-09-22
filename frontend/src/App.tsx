import { useState, useRef, useCallback } from 'react';
import { Loader2 } from 'lucide-react';
import { Header } from './components/Header';
import { DashboardPage } from './pages/DashboardPage';
import { AuthView } from './components/AuthView';
import { ErrorBoundary } from './components/ErrorBoundary';
import { AuthProvider, useAuth } from './context/AuthContext';

function AppContent() {
  const { user, loading } = useAuth();
  const [isProjectsRefreshing, setIsProjectsRefreshing] = useState<boolean>(false);
  const refreshProjectsRef = useRef<() => void>(() => {});

  const handleRegisterRefresh = useCallback((fn: () => void) => {
    refreshProjectsRef.current = fn;
  }, []);

  const handleHeaderRefresh = useCallback(() => {
    refreshProjectsRef.current();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col items-center justify-center font-sans space-y-3">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
        <p className="text-xs font-mono text-slate-400">Verifying session with Supabase Auth...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col font-sans">
      <Header onRefresh={handleHeaderRefresh} isRefreshing={isProjectsRefreshing} />

      <main className="flex-1 max-w-7xl 2xl:max-w-[1600px] w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {user ? (
          <DashboardPage
            registerRefresh={handleRegisterRefresh}
            onProjectsRefreshingChange={setIsProjectsRefreshing}
          />
        ) : (
          <AuthView />
        )}
      </main>

      <footer className="border-t border-slate-800/80 bg-[#0d1322]/40 py-4 text-center text-xs text-slate-400 font-mono">
        <div className="max-w-7xl 2xl:max-w-[1600px] mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>AI Software Failure Investigator &bull; Production MVP v1.0.0</span>
          <span>FastAPI / Supabase PostgreSQL / React 19</span>
        </div>
      </footer>
    </div>
  );
}

export function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
