import React, { useState, useEffect } from 'react';
import { Download, RefreshCw, Calendar } from 'lucide-react';
import { api, Job } from '../api';
import { StatusBadge } from '../components/StatusBadge';
import { downloadBlueprintFile } from '../utils/download';

interface JobsProps {
  onNavigateToJob: (jobId: string) => void;
}

export const Jobs: React.FC<JobsProps> = ({ onNavigateToJob }) => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloadingJobId, setDownloadingJobId] = useState<string | null>(null);

  const fetchJobs = () => {
    setLoading(true);
    api.getJobs()
      .then((data) => {
        setJobs(data);
        setError(null);
      })
      .catch((err) => {
        setError(err.message || 'Failed to fetch job history');
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const handleRetryJob = async (job: Job) => {
    try {
      const newJob = await api.createJob({
        github_url: job.repo_url,
        provider_override: job.provider,
        model_override: job.model,
      });
      onNavigateToJob(newJob.id);
    } catch (err: any) {
      alert(`Failed to retry: ${err.message}`);
    }
  };

  const handleResumeJob = async (job: Job) => {
    try {
      const newJob = await api.createJob({
        github_url: job.repo_url,
        provider_override: job.provider,
        model_override: job.model,
      });
      onNavigateToJob(newJob.id);
    } catch (err: any) {
      alert(`Failed to resume: ${err.message}`);
    }
  };

  const handleDownloadJob = async (job: Job) => {
    if (!job.download_url || downloadingJobId) return;
    try {
      setDownloadingJobId(job.id);
      await downloadBlueprintFile(job.download_url, `${job.repo_name}_REBUILD_BLUEPRINT.md`);
    } catch (err: any) {
      if (err?.message !== 'Save was cancelled') {
        alert(`Failed to download blueprint: ${err.message}`);
      }
    } finally {
      setDownloadingJobId(null);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  const renderHistoryProgress = (job: Job) => {
    const isActive = job.status === 'queued' || job.status === 'running';
    if (!isActive) {
      return null;
    }

    const progressValue = Math.max(0, Math.min(100, job.progress || 0));
    const progressTone = job.status === 'queued' ? 'bg-sky-500' : 'bg-indigo-600';

    return (
      <div className="glass-panel-soft mt-3 rounded-[20px] px-3 py-3">
        <div className="mb-1.5 flex items-center justify-between gap-3">
          <span className="truncate text-[11px] font-semibold text-slate-700">
            {job.current_step || (job.status === 'queued' ? 'Waiting to start' : 'In progress')}
          </span>
          <span className="shrink-0 font-mono text-[11px] font-bold text-indigo-700">
            {progressValue}%
          </span>
        </div>
        <div className="h-2.5 w-full overflow-hidden rounded-full bg-white/80 shadow-[inset_0_2px_6px_rgba(148,163,184,0.2)]">
          <div
            className={`h-full rounded-full transition-all duration-500 ${progressTone}`}
            style={{ width: `${progressValue}%` }}
          />
        </div>
      </div>
    );
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="section-card flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">Job Execution History</h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">Review, monitor progress, rerun analyses, and download generated blueprints.</p>
        </div>
        <button
          onClick={fetchJobs}
          disabled={loading}
          className="secondary-button self-start p-3 text-slate-500 hover:text-slate-800 disabled:opacity-50"
        >
          <RefreshCw className={`h-4.5 w-4.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {error && (
        <div className="glass-panel-soft rounded-2xl p-4 text-sm text-rose-800">
          {error}
        </div>
      )}

      {loading && jobs.length === 0 ? (
        <div className="section-card flex items-center justify-center p-12">
          <RefreshCw className="h-6 w-6 animate-spin text-indigo-600" />
          <span className="ml-3 text-slate-500 text-sm">Retrieving job history...</span>
        </div>
      ) : jobs.length === 0 ? (
        <div className="section-card p-16 text-center italic text-slate-500">
          No analysis job records found. Create one from the home screen!
        </div>
      ) : (
        <div className="space-y-4">
            {jobs.map((job) => {
              const createdDate = new Date(job.created_at).toLocaleString();

              let durationStr = '--';
              if (job.started_at && job.completed_at) {
                const diff = new Date(job.completed_at).getTime() - new Date(job.started_at).getTime();
                const seconds = Math.floor(diff / 1000);
                const minutes = Math.floor(seconds / 60);
                durationStr = minutes > 0 ? `${minutes}m ${seconds % 60}s` : `${seconds}s`;
              } else if (job.status === 'running') {
                durationStr = 'running';
              }

              return (
                <div
                  key={job.id}
                  className="section-card cursor-pointer p-5 transition-all duration-200 hover:-translate-y-0.5 hover:bg-white/80"
                  onClick={() => onNavigateToJob(job.id)}
                >
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div className="min-w-0 flex-1 space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <div className="font-bold text-slate-800 break-words">{job.repo_name}</div>
                        <StatusBadge status={job.status} />
                      </div>

                      <div className="text-xs text-slate-500 font-mono break-all">
                        {job.repo_url}
                      </div>

                      {(job.provider || job.model) && (
                        <div className="flex flex-wrap items-center gap-1.5 text-[10px] text-slate-400">
                          <span>
                            Provider: <span className="font-semibold text-slate-500 capitalize">{job.provider}</span>
                          </span>
                          <span className="text-slate-300">•</span>
                          <span>
                            Model: <span className="font-mono text-slate-500 break-all">{job.model}</span>
                          </span>
                        </div>
                      )}

                      <div className="grid grid-cols-1 gap-2 text-xs text-slate-550 sm:grid-cols-2 xl:grid-cols-3">
                        <div className="flex min-w-0 items-center gap-1.5">
                          <Calendar className="h-3.5 w-3.5 shrink-0 text-slate-500" />
                          <span className="truncate">Started: {createdDate}</span>
                        </div>
                        <div className="font-mono">Duration: {durationStr}</div>
                        <div className="font-mono truncate">Job ID: {job.id}</div>
                      </div>

                      {renderHistoryProgress(job)}
                    </div>

                    <div
                      className="flex flex-wrap items-center gap-2 lg:justify-end"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button
                        onClick={() => onNavigateToJob(job.id)}
                        className="secondary-button px-3 py-2 text-xs"
                      >
                        Details
                      </button>

                      {(job.status === 'failed' || job.status === 'completed') && (
                        <button
                          onClick={() => handleRetryJob(job)}
                          className="secondary-button px-3 py-2 text-xs"
                          title={job.status === 'completed' ? 'Run Analysis Again' : 'Retry Analysis'}
                        >
                          <RefreshCw className="h-3.5 w-3.5" />
                          <span>{job.status === 'completed' ? 'Run Again' : 'Retry'}</span>
                        </button>
                      )}

                      {job.status === 'cancelled' && (
                        <button
                          onClick={() => handleResumeJob(job)}
                          className="inline-flex items-center space-x-1 rounded-2xl border border-amber-200/70 bg-amber-50/85 px-3 py-2 text-xs font-semibold text-amber-800 shadow-[0_10px_24px_rgba(251,191,36,0.18)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-amber-100/90"
                          title="Resume Analysis"
                        >
                          <RefreshCw className="h-3.5 w-3.5" />
                          <span>Resume</span>
                        </button>
                      )}

                      {job.status === 'completed' && job.download_url && (
                        <button
                          onClick={() => handleDownloadJob(job)}
                          disabled={downloadingJobId === job.id}
                          className="inline-flex rounded-2xl border border-blue-200/70 bg-blue-50/90 p-2 text-xs text-blue-700 shadow-[0_10px_24px_rgba(59,130,246,0.16)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-blue-100"
                          title="Download Markdown Blueprint"
                        >
                          <Download className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
        </div>
      )}
    </div>
  );
};
