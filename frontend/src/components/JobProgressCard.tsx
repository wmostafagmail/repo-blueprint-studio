import React, { useState } from 'react';
import { Download, FileText, Check, Copy, AlertCircle, X, RefreshCw } from 'lucide-react';
import { Job } from '../api';
import { StatusBadge } from './StatusBadge';

interface JobProgressCardProps {
  job: Job;
  onCancel: () => void;
  onPreview: () => void;
  onRetry?: () => void;
  onResume?: () => void;
}

export const JobProgressCard: React.FC<JobProgressCardProps> = ({ job, onCancel, onPreview, onRetry, onResume }) => {
  const [copied, setCopied] = useState(false);

  const handleCopyPath = () => {
    if (job.output_path) {
      navigator.clipboard.writeText(job.output_path);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const isPending = job.status === 'queued' || job.status === 'running';

  return (
    <div className="section-card">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 border-b border-white/50 pb-4 md:flex-row md:items-center">
        <div>
          <div className="flex items-center space-x-3">
            <h2 className="text-lg font-bold text-slate-900">{job.repo_name}</h2>
            <StatusBadge status={job.status} />
          </div>
          <p className="mt-1 select-all break-all font-mono text-xs text-slate-500">{job.repo_url}</p>
          {(job.provider || job.model) && (
            <p className="mt-1.5 flex items-center gap-1.5 text-[10px] font-semibold text-blue-700">
              <span>Provider: <span className="rounded-full bg-blue-50 px-2 py-0.5 capitalize text-blue-700">{job.provider}</span></span>
              <span className="text-slate-300">•</span>
              <span>Model: <span className="rounded-full bg-blue-50 px-2 py-0.5 font-mono text-blue-700">{job.model}</span></span>
            </p>
          )}
        </div>

        {isPending && (
          <button
            onClick={onCancel}
            className="inline-flex items-center space-x-1.5 self-start rounded-2xl border border-rose-200/70 bg-rose-50/90 px-4 py-2.5 text-xs font-semibold text-rose-700 shadow-[0_12px_28px_rgba(244,63,94,0.16)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-rose-100 md:self-auto"
          >
            <X className="h-3.5 w-3.5" />
            <span>Cancel Analysis</span>
          </button>
        )}
      </div>

      {/* Progress body */}
      <div className="py-6">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-semibold text-slate-700">{job.current_step}</span>
          <span className="text-sm font-bold text-indigo-600 font-mono">{job.progress}%</span>
        </div>

        {/* Progress bar */}
        <div className="h-2.5 w-full overflow-hidden rounded-full bg-white/70 shadow-[inset_0_2px_6px_rgba(148,163,184,0.22)]">
          <div 
            className={`h-full rounded-full transition-all duration-550 ${
              job.status === 'failed' ? 'bg-rose-500' :
              job.status === 'cancelled' ? 'bg-amber-500' :
              job.status === 'completed' ? 'bg-emerald-500' :
              'bg-indigo-600'
            }`}
            style={{ width: `${job.progress}%` }}
          />
        </div>
      </div>

      {/* Error Details */}
      {job.status === 'failed' && job.error_message && (
        <div className="glass-panel-soft mb-6 flex items-start space-x-3 rounded-[22px] p-4 text-rose-800">
          <AlertCircle className="h-5 w-5 text-rose-500 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="font-bold text-sm">Analysis Execution Failed</h4>
            <p className="text-xs text-rose-700 mt-1 font-mono break-all">{job.error_message}</p>
          </div>
        </div>
      )}

      {/* Complete Actions */}
      {job.status === 'completed' && (
        <div className="flex flex-wrap items-center gap-3 pt-2">
          <a
            href={job.download_url}
            download
            className="primary-button px-4 py-2 text-xs"
          >
            <Download className="h-3.5 w-3.5" />
            <span>Download Blueprint</span>
          </a>

          <button
            onClick={onPreview}
            className="secondary-button px-4 py-2 text-xs"
          >
            <FileText className="h-3.5 w-3.5" />
            <span>Preview Blueprint</span>
          </button>

          {job.output_path && (
            <button
              onClick={handleCopyPath}
              className="secondary-button px-4 py-2 text-xs"
            >
              {copied ? (
                <>
                  <Check className="h-3.5 w-3.5 text-emerald-600" />
                  <span>Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5" />
                  <span>Copy File Path</span>
                </>
              )}
            </button>
          )}

          {onRetry && (
            <button
              onClick={onRetry}
              className="secondary-button px-4 py-2 text-xs"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Run Analysis Again</span>
            </button>
          )}
        </div>
      )}

      {job.status === 'failed' && onRetry && (
        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={onRetry}
          className="primary-button px-4 py-2 text-xs"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Retry Analysis</span>
          </button>
        </div>
      )}

      {job.status === 'cancelled' && onResume && (
        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={onResume}
          className="inline-flex items-center space-x-2 rounded-2xl bg-gradient-to-b from-amber-500 to-amber-600 px-4 py-2 text-xs font-semibold text-white shadow-[0_16px_36px_rgba(217,119,6,0.28)] transition-all duration-200 hover:-translate-y-0.5"
        >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Resume Analysis</span>
          </button>
        </div>
      )}
    </div>
  );
};
