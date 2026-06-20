import { useEffect, useState } from 'react';
import type { Job } from '../api';

type JobTiming = Pick<Job, 'status' | 'started_at' | 'completed_at' | 'duration_seconds'>;

export function useJobTimer(enabled: boolean): number {
  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => {
    if (!enabled) {
      return;
    }

    setNowMs(Date.now());
    const timerId = window.setInterval(() => {
      setNowMs(Date.now());
    }, 1000);

    return () => window.clearInterval(timerId);
  }, [enabled]);

  return nowMs;
}

export function getJobDurationSeconds(job: JobTiming, nowMs = Date.now()): number | null {
  if (typeof job.duration_seconds === 'number' && job.duration_seconds >= 0) {
    return job.duration_seconds;
  }

  if (!job.started_at) {
    return null;
  }

  const startedMs = new Date(job.started_at).getTime();
  if (Number.isNaN(startedMs)) {
    return null;
  }

  const endMs = job.completed_at ? new Date(job.completed_at).getTime() : nowMs;
  if (Number.isNaN(endMs) || endMs < startedMs) {
    return null;
  }

  return Math.floor((endMs - startedMs) / 1000);
}

export function formatJobDuration(seconds: number | null, isActive = false): string {
  if (seconds === null) {
    return isActive ? 'Starting…' : '--';
  }

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = seconds % 60;

  if (hours > 0) {
    return `${hours}h ${minutes}m ${remainingSeconds}s`;
  }

  if (minutes > 0) {
    return `${minutes}m ${remainingSeconds}s`;
  }

  return `${remainingSeconds}s`;
}
