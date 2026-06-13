import React from 'react';

interface StatusBadgeProps {
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const styles = {
    queued: 'bg-slate-100 text-slate-700 border-slate-200',
    running: 'bg-blue-50 text-blue-700 border-blue-200 animate-pulse',
    completed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    failed: 'bg-rose-50 text-rose-700 border-rose-200',
    cancelled: 'bg-amber-50 text-amber-700 border-amber-200',
  };

  const label = {
    queued: 'Queued',
    running: 'Analyzing...',
    completed: 'Success',
    failed: 'Failed',
    cancelled: 'Cancelled',
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${styles[status] || styles.queued}`}>
      {label[status] || status}
    </span>
  );
};
