import React, { useState, useEffect } from 'react';
import { Download, RefreshCw, Calendar } from 'lucide-react';
import { api, Job } from '../api';
import { StatusBadge } from '../components/StatusBadge';

interface JobsProps {
  onNavigateToJob: (jobId: string) => void;
}

export const Jobs: React.FC<JobsProps> = ({ onNavigateToJob }) => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  useEffect(() => {
    fetchJobs();
  }, []);

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-800">Job Execution History</h1>
          <p className="text-xs text-slate-400 mt-1">Review, monitor progress, and download generated blueprints.</p>
        </div>
        <button
          onClick={fetchJobs}
          disabled={loading}
          className="p-2 border border-slate-200 hover:bg-slate-50 rounded-lg bg-white shadow-sm transition-colors text-slate-500 hover:text-slate-800 disabled:opacity-50"
        >
          <RefreshCw className={`h-4.5 w-4.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 text-rose-800 border border-rose-100 rounded-lg text-sm">
          {error}
        </div>
      )}

      {loading && jobs.length === 0 ? (
        <div className="flex items-center justify-center p-12 bg-white rounded-xl border border-slate-200">
          <RefreshCw className="h-6 w-6 animate-spin text-indigo-600" />
          <span className="ml-3 text-slate-500 text-sm">Retrieving job history...</span>
        </div>
      ) : jobs.length === 0 ? (
        <div className="text-center p-16 bg-white rounded-xl border border-slate-200 text-slate-500 italic">
          No analysis job records found. Create one from the home screen!
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="divide-y divide-slate-100">
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
                  className="p-5 hover:bg-slate-50 transition-colors cursor-pointer"
                  onClick={() => onNavigateToJob(job.id)}
                >
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div className="min-w-0 flex-1 space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <div className="font-bold text-slate-800 break-words">{job.repo_name}</div>
                        <StatusBadge status={job.status} />
                      </div>

                      <div className="text-xs text-slate-400 font-mono break-all">
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
                        <div className="flex items-center gap-1.5 min-w-0">
                          <Calendar className="h-3.5 w-3.5 text-slate-450 shrink-0" />
                          <span className="truncate">Started: {createdDate}</span>
                        </div>
                        <div className="font-mono">Duration: {durationStr}</div>
                        <div className="font-mono truncate">Job ID: {job.id}</div>
                      </div>
                    </div>

                    <div
                      className="flex flex-wrap items-center gap-2 lg:justify-end"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button
                        onClick={() => onNavigateToJob(job.id)}
                        className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-50 border border-slate-200 hover:bg-slate-100 rounded-lg transition-colors"
                      >
                        Details
                      </button>

                      {job.status === 'failed' && (
                        <button
                          onClick={() => handleRetryJob(job)}
                          className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-50 border border-slate-200 hover:bg-slate-100 rounded-lg transition-colors flex items-center space-x-1"
                          title="Retry Analysis"
                        >
                          <RefreshCw className="h-3.5 w-3.5" />
                          <span>Retry</span>
                        </button>
                      )}

                      {job.status === 'cancelled' && (
                        <button
                          onClick={() => handleResumeJob(job)}
                          className="px-3 py-1.5 text-xs font-semibold text-amber-800 bg-amber-50 border border-amber-200 hover:bg-amber-100 rounded-lg transition-colors flex items-center space-x-1"
                          title="Resume Analysis"
                        >
                          <RefreshCw className="h-3.5 w-3.5" />
                          <span>Resume</span>
                        </button>
                      )}

                      {job.status === 'completed' && job.download_url && (
                        <a
                          href={job.download_url}
                          download
                          className="p-1.5 text-xs bg-indigo-50 hover:bg-indigo-100 text-indigo-750 border border-indigo-100 rounded-lg transition-colors"
                          title="Download Markdown Blueprint"
                        >
                          <Download className="h-4 w-4" />
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
