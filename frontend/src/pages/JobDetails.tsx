import React, { useState, useEffect } from 'react';
import { ArrowLeft, RefreshCw, ChevronLeft } from 'lucide-react';
import { api, Job, JobArtifact, JobLog } from '../api';
import { JobProgressCard } from '../components/JobProgressCard';
import { LogViewer } from '../components/LogViewer';
import { MarkdownPreview } from '../components/MarkdownPreview';
import { MermaidRenderer } from '../components/MermaidRenderer';
import { CodebaseTreemap } from '../components/CodebaseTreemap';
import { ArchitectureExplorer } from '../components/ArchitectureExplorer';
import { StatusBadge } from '../components/StatusBadge';

interface JobDetailsProps {
  jobId: string;
  onBack: () => void;
  onNavigateToJob: (jobId: string) => void;
}

export const JobDetails: React.FC<JobDetailsProps> = ({ jobId, onBack, onNavigateToJob }) => {
  const [job, setJob] = useState<Job | null>(null);
  const [logs, setLogs] = useState<JobLog[]>([]);
  const [childJobs, setChildJobs] = useState<Job[]>([]);
  const [artifacts, setArtifacts] = useState<JobArtifact[]>([]);
  const [selectedArtifactPath, setSelectedArtifactPath] = useState<string | null>(null);
  const [selectedArtifactContent, setSelectedArtifactContent] = useState<string>('');
  const [markdown, setMarkdown] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [logsLoading, setLogsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'spec' | 'architecture' | 'treemap'>('spec');
  const [archSubTab, setArchSubTab] = useState<'explorer' | 'diagrams'>('explorer');
  const [inventoryData, setInventoryData] = useState<any>(null);

  const fetchJobData = async (showLoading = false) => {
    if (showLoading) setLoading(true);
    try {
      const jobData = await api.getJob(jobId);
      setJob(jobData);
      
      const logData = await api.getJobLogs(jobId);
      setLogs(logData);
      const childJobData = await api.getJobChildren(jobId);
      setChildJobs(childJobData);
      
      if (jobData.status === 'completed' && !markdown) {
        const preview = await api.getBlueprintPreview(jobId);
        setMarkdown(preview.markdown);
        // Fetch inventory data for treemap view
        const inventory = await api.getJobInventory(jobId);
        setInventoryData(inventory);
        const artifactData = await api.getJobArtifacts(jobId);
        setArtifacts(artifactData);
        if (artifactData.length > 0) {
          const preferredArtifact = artifactData.find((artifact) => artifact.category === 'compiled') || artifactData[0];
          setSelectedArtifactPath(preferredArtifact.path);
          const artifactContent = await api.getJobArtifactContent(jobId, preferredArtifact.path);
          setSelectedArtifactContent(artifactContent.content);
        }
      }
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch job data');
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  useEffect(() => {
    // Initial fetch
    fetchJobData(true);

    // Poll if job is not completed/failed/cancelled
    let interval: any = null;
    
    const checkAndPoll = async () => {
      try {
        const jobData = await api.getJob(jobId);
        setJob(jobData);
        
        const logData = await api.getJobLogs(jobId);
        setLogs(logData);
        const childJobData = await api.getJobChildren(jobId);
        setChildJobs(childJobData);
        
        if (jobData.status === 'completed') {
          const preview = await api.getBlueprintPreview(jobId);
          setMarkdown(preview.markdown);
          const inventory = await api.getJobInventory(jobId);
          setInventoryData(inventory);
          const artifactData = await api.getJobArtifacts(jobId);
          setArtifacts(artifactData);
          if (!selectedArtifactPath && artifactData.length > 0) {
            const preferredArtifact = artifactData.find((artifact) => artifact.category === 'compiled') || artifactData[0];
            setSelectedArtifactPath(preferredArtifact.path);
            const artifactContent = await api.getJobArtifactContent(jobId, preferredArtifact.path);
            setSelectedArtifactContent(artifactContent.content);
          } else if (selectedArtifactPath) {
            const artifactContent = await api.getJobArtifactContent(jobId, selectedArtifactPath);
            setSelectedArtifactContent(artifactContent.content);
          }
          if (interval) clearInterval(interval);
        } else if (jobData.status === 'failed' || jobData.status === 'cancelled') {
          if (interval) clearInterval(interval);
        }
      } catch (err) {
        // Suppress background polling errors to keep UI smooth
      }
    };

    interval = setInterval(checkAndPoll, 1500);

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [jobId]);

  const handleCancel = async () => {
    if (!job) return;
    try {
      await api.cancelJob(job.id);
      fetchJobData();
    } catch (err: any) {
      alert(`Failed to cancel: ${err.message}`);
    }
  };

  const handleRetry = async () => {
    if (!job) return;
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

  const handleResume = async () => {
    if (!job) return;
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

  const handleStructuredAnalysisRetry = async () => {
    if (!job) return;
    try {
      const newJob = await api.createJob({
        github_url: job.repo_url,
        provider_override: job.provider,
        model_override: job.model,
        source_job_id: job.id,
        resume_from_stage: 'analysis_state',
      });
      onNavigateToJob(newJob.id);
    } catch (err: any) {
      alert(`Failed to retry from Structured Analysis State: ${err.message}`);
    }
  };

  const handleManualLogsRefresh = async () => {
    setLogsLoading(true);
    try {
      const logData = await api.getJobLogs(jobId);
      setLogs(logData);
    } catch (err) {}
    setLogsLoading(false);
  };

  const handleSelectArtifact = async (artifactPath: string) => {
    setSelectedArtifactPath(artifactPath);
    try {
      const artifact = await api.getJobArtifactContent(jobId, artifactPath);
      setSelectedArtifactContent(artifact.content);
    } catch (err) {
      setSelectedArtifactContent('');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-20">
        <RefreshCw className="h-6 w-6 animate-spin text-indigo-600" />
        <span className="ml-3 text-slate-500 text-sm">Loading job details...</span>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="space-y-4 max-w-lg mx-auto py-12 text-center">
        <div className="bg-rose-50 text-rose-800 border border-rose-100 p-4 rounded-xl text-sm font-medium">
          {error || 'Job not found'}
        </div>
        <button
          onClick={onBack}
          className="inline-flex items-center space-x-2 text-indigo-655 hover:text-indigo-700 font-semibold"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Home</span>
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <button
        onClick={onBack}
        className="secondary-button text-sm"
      >
        <ChevronLeft className="h-4.5 w-4.5" />
        <span>Back</span>
      </button>

      {/* Main progress panel */}
      <JobProgressCard 
        job={job}
        onCancel={handleCancel}
        onPreview={fetchJobData}
        onRetry={handleRetry}
        onResume={handleResume}
      />

      {childJobs.length > 0 && (
        <div className="section-card">
          <h3 className="mb-4 text-base font-bold text-slate-900">Pipeline Stages</h3>
          <div className="space-y-3">
            {childJobs.map((child) => (
              <div key={child.id} className="glass-panel-soft rounded-[22px] px-4 py-4">
                <div className="mb-2 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <div className="text-sm font-bold text-slate-800">{child.stage_name || child.repo_name}</div>
                    <div className="text-[11px] uppercase tracking-[0.2em] text-slate-400">{child.job_kind || 'stage'}</div>
                  </div>
                  <StatusBadge status={child.status} />
                </div>
                <div className="mb-2 flex items-center justify-between gap-3 text-xs">
                  <span className="truncate text-slate-600">{child.current_step}</span>
                  <span className="font-mono font-semibold text-indigo-700">{child.progress}%</span>
                </div>
                <div className="h-2.5 w-full overflow-hidden rounded-full bg-white/80 shadow-[inset_0_2px_6px_rgba(148,163,184,0.2)]">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      child.status === 'completed'
                        ? 'bg-emerald-500'
                        : child.status === 'failed'
                        ? 'bg-rose-500'
                        : child.status === 'cancelled'
                        ? 'bg-amber-500'
                        : 'bg-indigo-600'
                    }`}
                    style={{ width: `${Math.max(0, Math.min(100, child.progress || 0))}%` }}
                  />
                </div>
                {child.stage_name === 'Structured Analysis State' && job.status !== 'running' && job.status !== 'queued' && (
                  <div className="mt-3 flex justify-end">
                    <button
                      onClick={handleStructuredAnalysisRetry}
                      className="secondary-button px-4 py-2 text-xs"
                    >
                      <RefreshCw className="h-3.5 w-3.5" />
                      <span>Retry From This Stage</span>
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Terminal logs console */}
      <LogViewer 
        logs={logs}
        onRefresh={handleManualLogsRefresh}
        isLoading={logsLoading}
      />

      {/* Blueprint Live Preview markdown component */}
      {job.status === 'completed' && (
        <>
          {artifacts.length > 0 && (
            <div className="section-card">
              <h3 className="mb-4 text-base font-bold text-slate-900">Generated Blueprint Files</h3>
              <div className="mb-4 flex flex-wrap gap-2">
                {artifacts.map((artifact) => (
                  <button
                    key={artifact.path}
                    onClick={() => handleSelectArtifact(artifact.path)}
                    className={`pill-tab text-xs ${
                      selectedArtifactPath === artifact.path
                        ? 'bg-blue-600 text-white shadow-[0_12px_30px_rgba(37,99,235,0.26)]'
                        : 'bg-white/70 text-slate-700 hover:bg-white'
                    }`}
                  >
                    {artifact.label}
                  </button>
                ))}
              </div>
              {selectedArtifactContent && <MarkdownPreview markdown={selectedArtifactContent} />}
            </div>
          )}
          <div className="glass-panel-soft mb-4 flex flex-wrap gap-2 rounded-[24px] p-2">
            <button
              onClick={() => setActiveTab('spec')}
              disabled={job?.status !== 'completed'}
              className={`pill-tab ${activeTab === 'spec' ? 'bg-blue-600 text-white shadow-[0_12px_30px_rgba(37,99,235,0.26)]' : 'text-slate-700 hover:bg-white/70'}`}
            >
              Blueprint
            </button>
            <button
              onClick={() => setActiveTab('architecture')}
              disabled={job?.status !== 'completed'}
              className={`pill-tab ${activeTab === 'architecture' ? 'bg-blue-600 text-white shadow-[0_12px_30px_rgba(37,99,235,0.26)]' : 'text-slate-700 hover:bg-white/70'}`}
            >
              Architecture
            </button>
            <button
              onClick={() => setActiveTab('treemap')}
              disabled={job?.status !== 'completed'}
              className={`pill-tab ${activeTab === 'treemap' ? 'bg-blue-600 text-white shadow-[0_12px_30px_rgba(37,99,235,0.26)]' : 'text-slate-700 hover:bg-white/70'}`}
            >
              Treemap
            </button>
          </div>
          {activeTab === 'spec' && markdown && <MarkdownPreview markdown={markdown} />}
          {activeTab === 'architecture' && (
            <div className="space-y-3">
              <div className="glass-dark flex w-fit space-x-1 rounded-2xl p-1.5">
                <button
                  onClick={() => setArchSubTab('explorer')}
                  className={`pill-tab text-xs ${
                    archSubTab === 'explorer'
                      ? 'bg-blue-600 text-white shadow-[0_12px_30px_rgba(37,99,235,0.26)]'
                      : 'text-slate-400 hover:bg-white/10 hover:text-slate-200'
                  }`}
                >
                  🏗️ Explorer
                </button>
                <button
                  onClick={() => setArchSubTab('diagrams')}
                  className={`pill-tab text-xs ${
                    archSubTab === 'diagrams'
                      ? 'bg-blue-600 text-white shadow-[0_12px_30px_rgba(37,99,235,0.26)]'
                      : 'text-slate-400 hover:bg-white/10 hover:text-slate-200'
                  }`}
                >
                  📊 Diagrams
                </button>
              </div>
              {archSubTab === 'explorer' && inventoryData && (
                <ArchitectureExplorer inventory={inventoryData} />
              )}
              {archSubTab === 'diagrams' && markdown && (
                <MermaidRenderer markdown={markdown} inventory={inventoryData} />
              )}
            </div>
          )}
          {activeTab === 'treemap' && inventoryData && <CodebaseTreemap inventory={inventoryData} />}
        </>
      )}
    </div>
  );
};
