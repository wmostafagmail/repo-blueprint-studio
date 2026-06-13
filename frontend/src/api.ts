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
}

export interface BlueprintPreviewResponse {
  repo_name: string;
  markdown: string;
}

const API_BASE = '/api';

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
      limits?: Record<string, { maxOutputTokens: number; chunkSize: number; max_output_tokens: number; chunk_size: number }>;
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
  }) => request<Job>('/jobs', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  
  cancelJob: (jobId: string) => request<{ message: string }>(`/jobs/${jobId}/cancel`, {
    method: 'POST',
  }),
  
  getJobLogs: (jobId: string) => request<JobLog[]>(`/jobs/${jobId}/logs`),
  
  getBlueprintPreview: (jobId: string) => request<BlueprintPreviewResponse>(`/jobs/${jobId}/preview`),
  getJobInventory: (jobId: string) => request<any>(`/jobs/${jobId}/inventory`),
};
