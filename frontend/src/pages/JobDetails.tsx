import React, { useState, useEffect } from 'react';
import { ArrowLeft, RefreshCw, ChevronLeft } from 'lucide-react';
import { api, Job, JobLog } from '../api';
import { JobProgressCard } from '../components/JobProgressCard';
import { LogViewer } from '../components/LogViewer';
import { MarkdownPreview } from '../components/MarkdownPreview';
import { MermaidRenderer } from '../components/MermaidRenderer';
import { CodebaseTreemap } from '../components/CodebaseTreemap';
import { ArchitectureExplorer } from '../components/ArchitectureExplorer';

interface JobDetailsProps {
  jobId: string;
  onBack: () => void;
  onNavigateToJob: (jobId: string) => void;
}

export const JobDetails: React.FC<JobDetailsProps> = ({ jobId, onBack, onNavigateToJob }) => {
  const [job, setJob] = useState<Job | null>(null);
  const [logs, setLogs] = useState<JobLog[]>([]);
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
      
      if (jobData.status === 'completed' && !markdown) {
        const preview = await api.getBlueprintPreview(jobId);
        setMarkdown(preview.markdown);
        // Fetch inventory data for treemap view
        const inventory = await api.getJobInventory(jobId);
        setInventoryData(inventory);
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
        
        if (jobData.status === 'completed') {
          const preview = await api.getBlueprintPreview(jobId);
          setMarkdown(preview.markdown);
          const inventory = await api.getJobInventory(jobId);
          setInventoryData(inventory);
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

  const handleManualLogsRefresh = async () => {
    setLogsLoading(true);
    try {
      const logData = await api.getJobLogs(jobId);
      setLogs(logData);
    } catch (err) {}
    setLogsLoading(false);
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
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Navigation breadcrumb */}
      <button
        onClick={onBack}
        className="flex items-center space-x-1.5 text-slate-450 hover:text-slate-805 text-sm font-semibold transition-colors"
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

      {/* Terminal logs console */}
      <LogViewer 
        logs={logs}
        onRefresh={handleManualLogsRefresh}
        isLoading={logsLoading}
      />

      {/* Blueprint Live Preview markdown component */}
      {job.status === 'completed' && (
        <>
          <div className="flex space-x-2 mb-4">
            <button
              onClick={() => setActiveTab('spec')}
              disabled={job?.status !== 'completed'}
              className={`px-3 py-1 rounded ${activeTab === 'spec' ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-700'}`}
            >
              Blueprint
            </button>
            <button
              onClick={() => setActiveTab('architecture')}
              disabled={job?.status !== 'completed'}
              className={`px-3 py-1 rounded ${activeTab === 'architecture' ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-700'}`}
            >
              Architecture
            </button>
            <button
              onClick={() => setActiveTab('treemap')}
              disabled={job?.status !== 'completed'}
              className={`px-3 py-1 rounded ${activeTab === 'treemap' ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-700'}`}
            >
              Treemap
            </button>
          </div>
          {activeTab === 'spec' && markdown && <MarkdownPreview markdown={markdown} />}
          {activeTab === 'architecture' && (
            <div className="space-y-3">
              {/* Sub-tab toggle */}
              <div className="flex space-x-1 bg-slate-900/60 border border-slate-800 rounded-lg p-1 w-fit">
                <button
                  onClick={() => setArchSubTab('explorer')}
                  className={`px-3 py-1 rounded-md text-xs font-semibold transition-colors ${
                    archSubTab === 'explorer'
                      ? 'bg-indigo-600 text-white shadow'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  🏗️ Explorer
                </button>
                <button
                  onClick={() => setArchSubTab('diagrams')}
                  className={`px-3 py-1 rounded-md text-xs font-semibold transition-colors ${
                    archSubTab === 'diagrams'
                      ? 'bg-indigo-600 text-white shadow'
                      : 'text-slate-400 hover:text-slate-200'
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
