import { useState, useRef, useCallback } from 'react';
import { Header } from './components/Header';
import { DashboardPage } from './pages/DashboardPage';

export function App() {
  const [isProjectsRefreshing, setIsProjectsRefreshing] = useState<boolean>(false);
  const refreshProjectsRef = useRef<() => void>(() => {});

  const handleRegisterRefresh = useCallback((fn: () => void) => {
    refreshProjectsRef.current = fn;
  }, []);

  const handleHeaderRefresh = useCallback(() => {
    refreshProjectsRef.current();
  }, []);

  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col font-sans">
      <Header onRefresh={handleHeaderRefresh} isRefreshing={isProjectsRefreshing} />

      <main className="flex-1 max-w-7xl 2xl:max-w-[1600px] w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <DashboardPage
          registerRefresh={handleRegisterRefresh}
          onProjectsRefreshingChange={setIsProjectsRefreshing}
        />
      </main>

      <footer className="border-t border-slate-800/80 bg-[#0d1322]/40 py-4 text-center text-xs text-slate-400 font-mono">
        <div className="max-w-7xl 2xl:max-w-[1600px] mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>AI Software Failure Investigator &bull; Phase 1 Foundation</span>
          <span>FastAPI / Supabase PostgreSQL / React 19</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
