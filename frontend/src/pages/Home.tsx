import React, { useState, useEffect } from 'react';
import { Play, ShieldAlert, History, Key, RefreshCw, Sparkles, Lock, Cpu } from 'lucide-react';
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
      setError('Add a GitHub repository URL to start the analysis.');
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
    <div className="mx-auto max-w-6xl space-y-8">
      <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="section-card relative overflow-hidden">
          <div className="absolute inset-x-0 top-0 h-28 bg-gradient-to-r from-blue-500/18 via-sky-300/18 to-cyan-200/10 blur-2xl" />
          <div className="relative space-y-6">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/70 bg-white/70 px-3 py-1.5 text-[11px] font-bold uppercase tracking-[0.18em] text-slate-600 shadow-[0_10px_25px_rgba(148,163,184,0.14)]">
              <Sparkles className="h-3.5 w-3.5 text-blue-600" />
              Blueprint-grade repository analysis
            </div>
            <div className="space-y-3">
              <h1 className="page-hero-title max-w-3xl">
                Turn any repository into an Apple-polished, clean-room rebuild spec.
              </h1>
              <p className="page-hero-copy max-w-2xl">
                Generate architecture-aware blueprints, implementation plans, and execution-ready documentation with a quality-first pipeline that scales across cloud and local models.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <div className="metric-tile">
                <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-2xl bg-blue-500/12 text-blue-700">
                  <Lock className="h-5 w-5" />
                </div>
                <div className="text-sm font-bold text-slate-800">Private-by-choice</div>
                <div className="mt-1 text-xs leading-6 text-slate-500">Run with local providers when repos need to stay on your machine.</div>
              </div>
              <div className="metric-tile">
                <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-2xl bg-violet-500/12 text-violet-700">
                  <Cpu className="h-5 w-5" />
                </div>
                <div className="text-sm font-bold text-slate-800">Model-flexible</div>
                <div className="mt-1 text-xs leading-6 text-slate-500">Capacity-aware settings help keep output quality consistent across providers.</div>
              </div>
              <div className="metric-tile">
                <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-2xl bg-emerald-500/12 text-emerald-700">
                  <History className="h-5 w-5" />
                </div>
                <div className="text-sm font-bold text-slate-800">Traceable runs</div>
                <div className="mt-1 text-xs leading-6 text-slate-500">Every analysis keeps detailed progress, logs, and downloadable blueprint artifacts.</div>
              </div>
            </div>
          </div>
        </div>

        <div className="section-card">
          <div className="mb-5">
            <div className="text-sm font-bold uppercase tracking-[0.18em] text-slate-500">Start New Analysis</div>
            <div className="mt-2 text-2xl font-extrabold tracking-tight text-slate-900">Launch a repository job</div>
            <p className="mt-2 text-sm leading-6 text-slate-500">
              Point the studio at a repository and we’ll create a fresh analysis run with the currently configured provider settings.
            </p>
          </div>

          <form onSubmit={handleStartAnalysis} className="space-y-5">
            <div>
              <label className="field-label">GitHub Repository URL</label>
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://github.com/username/repository-name"
                disabled={submitting}
                autoFocus
                className="input-surface"
              />
              <p className="mt-2 text-xs text-slate-500">
                Supports public HTTPS and private repositories.
              </p>
            </div>

            <div className="pt-1">
              <label className="field-label flex items-center gap-2">
                <Key className="h-3.5 w-3.5 text-slate-400" />
                Personal Access Token (Optional)
              </label>
              <input
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="github_pat_... (Leave blank to use default settings token)"
                disabled={submitting}
                className="input-surface"
              />
            </div>

            <div className="glass-panel-soft rounded-[24px] border border-amber-200/60 bg-gradient-to-br from-amber-50/90 to-white/70 p-4 text-xs text-amber-900">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-2xl bg-amber-100/90 text-amber-700">
                  <ShieldAlert className="h-4.5 w-4.5" />
                </div>
                <div>
                  <span className="mb-1 block text-sm font-bold text-amber-950">Sensitive Repository Warning</span>
                  <span className="leading-6">For commercial or sensitive code, configure local providers in Settings to keep repository contents offline.</span>
                </div>
              </div>
            </div>

            <ErrorPanel error={error} title="Analysis couldn’t start yet" />

            <button
              type="submit"
              disabled={submitting}
              className="primary-button w-full"
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
      </div>

      <div className="section-card">
        <div className="mb-5 flex flex-col gap-3 border-b border-white/50 pb-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="flex items-center gap-2 text-base font-bold text-slate-900">
              <History className="h-4 w-4 text-slate-500" />
              <span>Recent Analysis Runs</span>
            </h3>
            <p className="mt-1 text-xs text-slate-500">Jump back into your latest jobs or open the full execution history.</p>
          </div>
          <button
            onClick={onNavigateToHistory}
            className="secondary-button text-xs"
          >
            View all history
          </button>
        </div>

        {loadingRecent ? (
          <div className="glass-panel-soft py-10 text-center text-xs text-slate-500">Loading history...</div>
        ) : recentJobs.length === 0 ? (
          <div className="glass-panel-soft py-10 text-center text-xs italic text-slate-500">No analysis runs recorded yet. Get started by entering a URL.</div>
        ) : (
          <div className="space-y-3">
            {recentJobs.map((job) => (
              <div
                key={job.id}
                className="glass-panel-soft cursor-pointer rounded-[24px] px-4 py-4 transition-all duration-200 hover:-translate-y-0.5 hover:bg-white"
                onClick={() => onNavigateToJob(job.id)}
              >
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <h4 className="text-sm font-bold text-slate-800">{job.repo_name}</h4>
                    <p className="mt-1 truncate font-mono text-xs text-slate-500">{job.repo_url}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="hidden text-[11px] font-medium text-slate-500 sm:inline">
                      {new Date(job.created_at).toLocaleDateString()}
                    </span>
                    <StatusBadge status={job.status} />
                  </div>
                </div>

                {(job.status === 'queued' || job.status === 'running') && (
                  <div className="mt-3 rounded-[20px] bg-white/70 px-3 py-3 shadow-[inset_0_2px_6px_rgba(148,163,184,0.16)]">
                    <div className="mb-1.5 flex items-center justify-between gap-3">
                      <span className="truncate text-[11px] font-semibold text-slate-700">
                        {job.current_step || (job.status === 'queued' ? 'Waiting to start' : 'In progress')}
                      </span>
                      <span className="shrink-0 font-mono text-[11px] font-bold text-indigo-700">
                        {Math.max(0, Math.min(100, job.progress || 0))}%
                      </span>
                    </div>
                    <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-200/60">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          job.status === 'queued' ? 'bg-sky-500' : 'bg-indigo-600'
                        }`}
                        style={{ width: `${Math.max(0, Math.min(100, job.progress || 0))}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
