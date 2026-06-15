import React from 'react';

interface StatusBadgeProps {
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const styles = {
    queued: 'bg-white/70 text-slate-700 border-white/80',
    running: 'bg-blue-50/90 text-blue-700 border-blue-200/70',
    completed: 'bg-emerald-50/90 text-emerald-700 border-emerald-200/70',
    failed: 'bg-rose-50/90 text-rose-700 border-rose-200/70',
    cancelled: 'bg-amber-50/90 text-amber-700 border-amber-200/70',
  };

  const label = {
    queued: 'Queued',
    running: 'Analyzing...',
    completed: 'Success',
    failed: 'Failed',
    cancelled: 'Cancelled',
  };

  return (
    <span className={`inline-flex items-center rounded-full border px-3 py-1 text-[11px] font-semibold shadow-[0_8px_20px_rgba(148,163,184,0.16)] ${styles[status] || styles.queued} ${status === 'running' ? 'animate-pulse' : ''}`}>
      {label[status] || status}
    </span>
  );
};
