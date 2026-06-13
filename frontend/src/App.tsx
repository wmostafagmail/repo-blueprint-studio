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
    <div className="flex flex-col min-h-screen">
      {/* Navigation Header */}
      <header className="sticky top-0 z-40 bg-white/80 backdrop-blur-md border-b border-slate-200 shadow-xs">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            {/* Logo */}
            <div 
              className="flex items-center space-x-2.5 cursor-pointer"
              onClick={() => setCurrentPage('home')}
            >
              <div className="h-9 w-9 rounded-xl overflow-hidden flex items-center justify-center shadow-xs border border-slate-100 bg-white">
                <img src="/logo.jpg" alt="Logo" className="h-full w-full object-cover" />
              </div>
              <span className="font-bold text-lg text-slate-800 tracking-tight font-sans">
                Repo Blueprint Studio
              </span>
            </div>

            {/* Nav Tabs */}
            <nav className="flex space-x-1 sm:space-x-2 bg-slate-100 p-1 rounded-xl">
              <button
                onClick={() => setCurrentPage('home')}
                className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
                  currentPage === 'home' 
                    ? 'bg-white text-indigo-600 shadow-xs' 
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                <HomeIcon className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">New Analysis</span>
              </button>

              <button
                onClick={() => setCurrentPage('history')}
                className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
                  currentPage === 'history' || currentPage === 'job-details'
                    ? 'bg-white text-indigo-600 shadow-xs' 
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                <HistoryIcon className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">History</span>
              </button>

              <button
                onClick={() => setCurrentPage('settings')}
                className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
                  currentPage === 'settings' 
                    ? 'bg-white text-indigo-600 shadow-xs' 
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                <SettingsIcon className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Settings</span>
              </button>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-grow max-w-6xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {renderPage()}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-150 bg-white py-6 mt-12">
        <div className="max-w-6xl mx-auto px-4 text-center text-xs text-slate-400">
          <p>© {new Date().getFullYear()} Repo Blueprint Studio. Built for clean-room reverse-engineering specifications.</p>
        </div>
      </footer>
    </div>
  );
}
