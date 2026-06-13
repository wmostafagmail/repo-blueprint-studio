import React, { useState } from 'react';
import { Download, FileText, Check, Copy, AlertCircle, X, RefreshCw } from 'lucide-react';
import { Job } from '../api';
import { StatusBadge } from './StatusBadge';

interface JobProgressCardProps {
  job: Job;
  onCancel: () => void;
  onPreview: () => void;
  onRetry?: () => void;
}

export const JobProgressCard: React.FC<JobProgressCardProps> = ({ job, onCancel, onPreview, onRetry }) => {
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
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-100">
        <div>
          <div className="flex items-center space-x-3">
            <h2 className="text-lg font-bold text-slate-800">{job.repo_name}</h2>
            <StatusBadge status={job.status} />
          </div>
          <p className="text-xs text-slate-400 mt-1 select-all font-mono break-all">{job.repo_url}</p>
          {(job.provider || job.model) && (
            <p className="text-[10px] font-semibold text-indigo-650 mt-1.5 flex items-center gap-1.5">
              <span>Provider: <span className="bg-indigo-50 px-1.5 py-0.5 rounded text-indigo-700 capitalize">{job.provider}</span></span>
              <span className="text-slate-300">•</span>
              <span>Model: <span className="bg-indigo-50 px-1.5 py-0.5 rounded text-indigo-700 font-mono">{job.model}</span></span>
            </p>
          )}
        </div>

        {isPending && (
          <button
            onClick={onCancel}
            className="px-3 py-1.5 border border-rose-200 text-rose-700 bg-rose-50 hover:bg-rose-100 font-semibold rounded-lg text-xs transition-colors flex items-center space-x-1.5 self-start md:self-auto"
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
        <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
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
        <div className="bg-rose-50 border border-rose-100 text-rose-800 p-4 rounded-lg flex items-start space-x-3 mb-6">
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
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-750 text-white font-semibold rounded-lg text-xs transition-colors flex items-center space-x-2 shadow-sm"
          >
            <Download className="h-3.5 w-3.5" />
            <span>Download Blueprint</span>
          </a>

          <button
            onClick={onPreview}
            className="px-4 py-2 border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 font-semibold rounded-lg text-xs transition-colors flex items-center space-x-2"
          >
            <FileText className="h-3.5 w-3.5" />
            <span>Preview Blueprint</span>
          </button>

          {job.output_path && (
            <button
              onClick={handleCopyPath}
              className="px-4 py-2 border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 font-semibold rounded-lg text-xs transition-colors flex items-center space-x-2"
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
        </div>
      )}

      {(job.status === 'failed' || job.status === 'cancelled') && onRetry && (
        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={onRetry}
            className="px-4 py-2 bg-indigo-650 hover:bg-indigo-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center space-x-2 shadow-sm"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Retry Analysis</span>
          </button>
        </div>
      )}
    </div>
  );
};
