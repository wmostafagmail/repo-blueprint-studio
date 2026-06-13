import React, { useState, useEffect } from 'react';
import { Play, ShieldAlert, History, Key, RefreshCw } from 'lucide-react';
import { api, Job } from '../api';
import { StatusBadge } from '../components/StatusBadge';
import { ErrorPanel } from '../components/ErrorPanel';

interface HomeProps {
  onNavigateToJob: (jobId: string) => void;
  onNavigateToHistory: () => void;
}

export const Home: React.FC<HomeProps> = ({ onNavigateToJob, onNavigateToHistory }) => {
  const [url, setUrl] = useState('');
  const [token, setToken] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recentJobs, setRecentJobs] = useState<Job[]>([]);
  const [loadingRecent, setLoadingRecent] = useState(true);

  // Fetch recent jobs
  useEffect(() => {
    api.getJobs()
      .then((data) => {
        setRecentJobs(data.slice(0, 5));
        setLoadingRecent(false);
      })
      .catch(() => {
        setLoadingRecent(false);
      });
  }, []);

  const handleStartAnalysis = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    
    const cleanUrl = url.trim();
    if (!cleanUrl) {
      setError('Please enter a GitHub repository URL');
      return;
    }

    setSubmitting(true);
    try {
      const job = await api.createJob({
        github_url: cleanUrl,
        github_token: token.trim() || undefined
      });
      onNavigateToJob(job.id);
    } catch (err: any) {
      setError(err.message || 'Failed to trigger repository analysis');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Hero Header */}
      <div className="text-center py-6">
        <h1 className="text-4xl font-extrabold text-slate-800 tracking-tight font-sans">
          Repo Blueprint Studio
        </h1>
        <p className="text-slate-500 mt-2.5 text-base max-w-2xl mx-auto">
          Reverse-engineer any GitHub repository into a self-contained, clean-room rebuild blueprint using advanced LLM reasoning.
        </p>
      </div>

      {/* Main Form */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 md:p-8">
        <form onSubmit={handleStartAnalysis} className="space-y-5">
          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
              GitHub Repository URL
            </label>
            <div className="relative rounded-lg shadow-sm">
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://github.com/username/repository-name"
                disabled={submitting}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 p-4 text-slate-800 text-sm focus:border-indigo-500 focus:bg-white outline-none pl-4 transition-all"
              />
            </div>
            <p className="text-xs text-slate-400 mt-2">
              Supports public HTTPS and private repositories.
            </p>
          </div>

          <div className="pt-2">
            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
              <Key className="h-3.5 w-3.5 text-slate-400" />
              <span>Personal Access Token (Optional)</span>
            </label>
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="github_pat_... (Leave blank to use default settings token)"
              disabled={submitting}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 p-3.5 text-slate-800 text-sm focus:border-indigo-500 focus:bg-white outline-none transition-all"
            />
          </div>

          {/* Security warning */}
          <div className="bg-amber-50 border border-amber-100 rounded-xl p-4 flex items-start space-x-3 text-amber-800 text-xs">
            <ShieldAlert className="h-4.5 w-4.5 text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold block mb-0.5">Sensitive Repository Warning</span>
              <span>For commercial or sensitive code, configure local providers (like Ollama or LM Studio) in **Settings** to keep repository contents offline.</span>
            </div>
          </div>

          <ErrorPanel error={error} title="Failed to launch analysis" />

          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl p-4 text-sm transition-all flex items-center justify-center space-x-2.5 shadow-sm disabled:opacity-50"
          >
            {submitting ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" />
                <span>Initializing Workspace...</span>
              </>
            ) : (
              <>
                <Play className="h-4.5 w-4.5 fill-current" />
                <span>Start Repository Analysis</span>
              </>
            )}
          </button>
        </form>
      </div>

      {/* Recent Runs */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
        <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-4">
          <h3 className="text-sm font-bold text-slate-800 flex items-center space-x-2">
            <History className="h-4 w-4 text-slate-500" />
            <span>Recent Analysis Runs</span>
          </h3>
          <button
            onClick={onNavigateToHistory}
            className="text-xs font-semibold text-indigo-600 hover:text-indigo-700 transition-colors"
          >
            View all history
          </button>
        </div>

        {loadingRecent ? (
          <div className="py-8 text-center text-slate-400 text-xs">Loading history...</div>
        ) : recentJobs.length === 0 ? (
          <div className="py-8 text-center text-slate-400 text-xs italic">No analysis runs recorded yet. Get started by entering a URL!</div>
        ) : (
          <div className="divide-y divide-slate-100">
            {recentJobs.map((job) => (
              <div 
                key={job.id} 
                className="py-3 flex items-center justify-between hover:bg-slate-50 px-2 rounded-lg cursor-pointer transition-colors"
                onClick={() => onNavigateToJob(job.id)}
              >
                <div>
                  <h4 className="text-sm font-bold text-slate-700">{job.repo_name}</h4>
                  <p className="text-xs text-slate-400 mt-0.5 truncate max-w-sm md:max-w-md font-mono">{job.repo_url}</p>
                </div>
                <div className="flex items-center space-x-4">
                  <span className="text-[10px] text-slate-400 hidden sm:inline">
                    {new Date(job.created_at).toLocaleDateString()}
                  </span>
                  <StatusBadge status={job.status} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
