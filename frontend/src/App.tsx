import { useState } from 'react';
import { Home as HomeIcon, History as HistoryIcon, Settings as SettingsIcon } from 'lucide-react';
import { Home } from './pages/Home';
import { Jobs } from './pages/Jobs';
import { JobDetails } from './pages/JobDetails';
import { Settings } from './pages/Settings';

type Page = 'home' | 'history' | 'settings' | 'job-details';

export default function App() {
  const [currentPage, setCurrentPage] = useState<Page>('home');
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  const handleNavigateToJob = (jobId: string) => {
    setActiveJobId(jobId);
    setCurrentPage('job-details');
  };

  const renderPage = () => {
    switch (currentPage) {
      case 'home':
        return (
          <Home 
            onNavigateToJob={handleNavigateToJob}
            onNavigateToHistory={() => setCurrentPage('history')}
          />
        );
      case 'history':
        return <Jobs onNavigateToJob={handleNavigateToJob} />;
      case 'job-details':
        return activeJobId ? (
          <JobDetails 
            jobId={activeJobId} 
            onBack={() => setCurrentPage('history')}
            onNavigateToJob={handleNavigateToJob}
          />
        ) : (
          <Home 
            onNavigateToJob={handleNavigateToJob}
            onNavigateToHistory={() => setCurrentPage('history')}
          />
        );
      case 'settings':
        return <Settings />;
      default:
        return <Home onNavigateToJob={handleNavigateToJob} onNavigateToHistory={() => setCurrentPage('history')} />;
    }
  };

  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-[-8rem] top-[-6rem] h-72 w-72 rounded-full bg-sky-300/25 blur-3xl" />
        <div className="absolute right-[-10rem] top-24 h-80 w-80 rounded-full bg-fuchsia-300/20 blur-3xl" />
        <div className="absolute bottom-[-8rem] left-1/3 h-96 w-96 rounded-full bg-teal-300/20 blur-3xl" />
      </div>

      <header className="sticky top-0 z-40 px-3 py-3 sm:px-5 lg:px-8">
        <div className="glass-panel mx-auto flex max-w-7xl items-center justify-between gap-4 rounded-[28px] px-4 py-3 sm:px-5">
          <div
            className="flex min-w-0 cursor-pointer items-center gap-3"
            onClick={() => setCurrentPage('home')}
          >
            <div className="h-11 w-11 overflow-hidden rounded-2xl border border-white/70 bg-white/80 shadow-[0_14px_30px_rgba(148,163,184,0.22)]">
              <img src="/logo.jpg" alt="Logo" className="h-full w-full object-cover" />
            </div>
            <div className="min-w-0">
              <div className="truncate text-[15px] font-extrabold tracking-tight text-slate-900 sm:text-lg">
                Repo Blueprint Studio
              </div>
              <div className="hidden text-[11px] font-medium tracking-[0.18em] text-slate-500 sm:block">
                CLEAN-ROOM ANALYSIS WORKSPACE
              </div>
            </div>
          </div>

          <nav className="glass-panel-soft flex flex-wrap gap-1 rounded-[22px] p-1.5">
            {[
              { key: 'home', label: 'New Analysis', shortLabel: 'New', icon: HomeIcon },
              { key: 'history', label: 'History', shortLabel: 'History', icon: HistoryIcon },
              { key: 'settings', label: 'Settings', shortLabel: 'Settings', icon: SettingsIcon },
            ].map(({ key, label, shortLabel, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setCurrentPage(key as Page)}
                className={`pill-tab ${
                  currentPage === key || (key === 'history' && currentPage === 'job-details')
                    ? 'bg-white text-blue-700 shadow-[0_14px_30px_rgba(148,163,184,0.24)]'
                    : 'text-slate-500 hover:bg-white/60 hover:text-slate-800'
                }`}
              >
                <Icon className="h-4 w-4" />
                <span className="hidden sm:inline">{label}</span>
                <span className="sm:hidden">{shortLabel}</span>
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="relative z-10 mx-auto flex-grow w-full max-w-7xl px-4 pb-10 pt-4 sm:px-6 lg:px-8">
        {renderPage()}
      </main>

      <footer className="relative z-10 mt-8 px-4 pb-6 sm:px-6 lg:px-8">
        <div className="glass-panel-soft mx-auto max-w-7xl rounded-[24px] px-5 py-4 text-center text-xs text-slate-500">
          <p>© {new Date().getFullYear()} Repo Blueprint Studio. Built for clean-room reverse-engineering specifications.</p>
        </div>
      </footer>
    </div>
  );
}
