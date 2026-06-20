export interface Setting {
  provider: string;
  api_key?: string;
  api_keys?: Record<string, string>;
  base_url?: string;
  model?: string;
  temperature?: number;
  max_output_tokens?: number;
  chunk_size?: number;
  max_repo_size_mb?: number;
  max_file_size_kb?: number;
  github_token?: string;
  output_dir?: string;
  keep_cloned_repos?: boolean;
  analysis_strategy?: 'direct' | 'hierarchical';
  map_batch_size?: number;
  generate_chunk_size?: number;
}

export interface Job {
  id: string;
  parent_job_id?: string | null;
  job_kind?: string | null;
  stage_name?: string | null;
  sort_index?: number | null;
  repo_url: string;
  repo_name: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  current_step: string;
  provider?: string;
  model?: string;
  output_path?: string;
  error_message?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  duration_seconds?: number;
  download_url?: string;
}

export interface JobLog {
  id: number;
  job_id: string;
  level: 'INFO' | 'WARNING' | 'ERROR' | 'DEBUG';
  message: string;
  created_at: string;
}

export interface TestConnectionResponse {
  success: boolean;
  message: string;
  latency_ms?: number;
  latency_score?: string;
  verified_model?: string;
  response_preview?: string;
}

export interface ModelLimit {
  maxOutputTokens: number;
  chunkSize: number;
  max_output_tokens: number;
  chunk_size: number;
  source?: string;
  notes?: string;
}

export interface BlueprintPreviewResponse {
  repo_name: string;
  markdown: string;
}

export interface JobArtifact {
  path: string;
  label: string;
  category: string;
}

export interface JobArtifactContent extends JobArtifact {
  content: string;
}

export interface OpenJobFileResponse {
  message: string;
  path: string;
}

declare global {
  interface Window {
    repoBlueprintDesktop?: {
      apiBaseUrl?: string;
      isDesktop?: boolean;
      platform?: string;
      saveFile?: (options: { base64: string; defaultFileName: string }) => Promise<boolean>;
    };
    showSaveFilePicker?: (options?: any) => Promise<any>;
  }
}

export const API_BASE = window.repoBlueprintDesktop?.apiBaseUrl || '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers || {}),
    },
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `HTTP Error ${response.status}: ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  // Settings API
  getSettings: () => request<Setting & { id: number }>('/settings'),
  
  updateSettings: (settings: Setting) => request<Setting & { id: number }>('/settings', {
    method: 'PUT',
    body: JSON.stringify(settings),
  }),
  
  testConnection: (payload: {
    provider: string;
    api_key?: string;
    base_url?: string;
    model?: string;
    temperature?: number;
  }) => request<TestConnectionResponse>('/settings/test-connection', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),

  getProviderModels: (params: { provider: string; api_key?: string; base_url?: string }) => {
    // Filter out undefined values
    const cleanParams: Record<string, string> = {};
    if (params.provider) cleanParams.provider = params.provider;
    if (params.api_key) cleanParams.api_key = params.api_key;
    if (params.base_url) cleanParams.base_url = params.base_url;
    const query = new URLSearchParams(cleanParams).toString();
    return request<{ 
      models: string[]; 
      limits?: Record<string, ModelLimit>;
    }>(`/settings/models?${query}`);
  },

  // Jobs API
  getJobs: () => request<Job[]>('/jobs'),
  
  getJob: (jobId: string) => request<Job>(`/jobs/${jobId}`),
  
  createJob: (payload: {
    github_url: string;
    github_token?: string;
    provider_override?: string;
    model_override?: string;
    source_job_id?: string;
    resume_from_stage?: string;
  }) => request<Job>('/jobs', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  
  cancelJob: (jobId: string) => request<{ message: string }>(`/jobs/${jobId}/cancel`, {
    method: 'POST',
  }),
  
  getJobLogs: (jobId: string) => request<JobLog[]>(`/jobs/${jobId}/logs`),
  getJobChildren: (jobId: string) => request<Job[]>(`/jobs/${jobId}/children`),
  
  getBlueprintPreview: (jobId: string) => request<BlueprintPreviewResponse>(`/jobs/${jobId}/preview`),
  getJobInventory: (jobId: string) => request<any>(`/jobs/${jobId}/inventory`),
  getJobArtifacts: (jobId: string) => request<JobArtifact[]>(`/jobs/${jobId}/artifacts`),
  getJobArtifactContent: (jobId: string, path: string) =>
    request<JobArtifactContent>(`/jobs/${jobId}/artifacts/content?path=${encodeURIComponent(path)}`),
  openJobFile: (jobId: string, path: string) =>
    request<OpenJobFileResponse>(`/jobs/${jobId}/open-file?path=${encodeURIComponent(path)}`, {
      method: 'POST',
    }),
};
