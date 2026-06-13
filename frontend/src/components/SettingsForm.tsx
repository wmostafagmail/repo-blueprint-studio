import React, { useState, useEffect } from 'react';
import { Save, RefreshCw, CheckCircle, XCircle } from 'lucide-react';
import { api, Setting } from '../api';

interface ModelLimits {
  maxOutputTokens: number;
  chunkSize: number;
}

const getModelLimits = (modelName: string): ModelLimits => {
  const model = modelName.toLowerCase();
  
  // Gemini Pro (huge context)
  if (model.includes('gemini-1.5-pro') || model.includes('gemini-2.0-pro') || model.includes('gemini-2.5-pro')) {
    return { maxOutputTokens: 8192, chunkSize: 500000 };
  }
  // Gemini Flash / Standard (large context)
  if (model.includes('gemini-1.5') || model.includes('gemini-2.5') || model.includes('gemini-2.0') || model.includes('gemini-')) {
    return { maxOutputTokens: 8192, chunkSize: 200000 };
  }
  // GPT-4o Mini / o1 / o3 Mini (large output, medium context)
  if (model.includes('gpt-4o-mini') || model.includes('o1-mini') || model.includes('o3-mini')) {
    return { maxOutputTokens: 16384, chunkSize: 60000 };
  }
  // GPT-4 / GPT-4o / Claude (medium output, medium context)
  if (model.includes('gpt-4') || model.includes('claude-3') || model.includes('claude-3.5') || model.includes('gpt-4o')) {
    return { maxOutputTokens: 4096, chunkSize: 60000 };
  }
  // Local models / Ollama / LM Studio (small context)
  if (model.includes('llama-3') || model.includes('mistral') || model.includes('gemma') || model.includes('phi')) {
    return { maxOutputTokens: 4096, chunkSize: 15000 };
  }
  
  return { maxOutputTokens: 4000, chunkSize: 10000 }; // default mock/generic fallback
};

export const SettingsForm: React.FC = () => {
  const [settings, setSettings] = useState<Setting>({
    provider: 'mock',
    api_key: '',
    api_keys: {},
    base_url: '',
    model: '',
    temperature: 0.2,
    max_output_tokens: 4000,
    chunk_size: 10000,
    max_repo_size_mb: 100,
    max_file_size_kb: 200,
    github_token: '',
    output_dir: '',
    keep_cloned_repos: false,
    analysis_strategy: 'direct',
    map_batch_size: 5,
    generate_chunk_size: 5,
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [saveStatus, setSaveStatus] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  const [testStatus, setTestStatus] = useState<{ type: 'success' | 'error', message: string } | null>(null);

  // Models listing states
  const [models, setModels] = useState<string[]>([]);
  const [modelsLimits, setModelsLimits] = useState<Record<string, ModelLimits>>({});
  const [loadingModels, setLoadingModels] = useState(false);
  const [modelsError, setModelsError] = useState<string | null>(null);

  const fetchModelsList = async (prov = settings.provider, key = settings.api_key, url = settings.base_url) => {
    if (prov === 'mock') {
      setModels(['mock-model-v1', 'mock-model-v2']);
      setModelsLimits({
        'mock-model-v1': { maxOutputTokens: 4000, chunkSize: 10000 },
        'mock-model-v2': { maxOutputTokens: 4000, chunkSize: 10000 },
      });
      setModelsError(null);
      return;
    }

    setLoadingModels(true);
    setModelsError(null);
    try {
      const data = await api.getProviderModels({
        provider: prov,
        api_key: key || undefined,
        base_url: url || undefined
      });
      setModels(data.models || []);
      
      const limitsMap: Record<string, ModelLimits> = {};
      if (data.limits) {
        Object.entries(data.limits).forEach(([mName, l]) => {
          limitsMap[mName] = {
            maxOutputTokens: l.maxOutputTokens ?? l.max_output_tokens ?? 4000,
            chunkSize: l.chunkSize ?? l.chunk_size ?? 10000
          };
        });
      }
      setModelsLimits(limitsMap);
    } catch (err: any) {
      setModels([]);
      setModelsLimits({});
      setModelsError(err.message || 'Failed to fetch models');
    } finally {
      setLoadingModels(false);
    }
  };

  useEffect(() => {
    // Load existing settings
    api.getSettings()
      .then((data) => {
        setSettings(data);
        setLoading(false);
        // Fetch models list once settings load
        fetchModelsList(data.provider, data.api_key, data.base_url);
      })
      .catch((err) => {
        setSaveStatus({ type: 'error', message: `Failed to load settings: ${err.message}` });
        setLoading(false);
      });
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    let finalValue: any = value;
    
    if (type === 'checkbox') {
      finalValue = (e.target as HTMLInputElement).checked;
    } else if (type === 'number') {
      finalValue = value === '' ? 0 : Number(value);
    }

    const updatedSettings = {
      ...settings,
      [name]: finalValue
    };

    if (name === 'api_key') {
      updatedSettings.api_keys = {
        ...(updatedSettings.api_keys || {}),
        [settings.provider]: finalValue
      };
    }

    // Auto-update base url defaults based on provider selection
    if (name === 'provider') {
      if (value === 'ollama') updatedSettings.base_url = 'http://localhost:11434';
      else if (value === 'lmstudio') updatedSettings.base_url = 'http://localhost:1234/v1';
      else if (value === 'openrouter') updatedSettings.base_url = 'https://openrouter.ai/api/v1';
      else if (value === 'openai') updatedSettings.base_url = '';
      
      const existingKey = (updatedSettings.api_keys || {})[value] || '';
      updatedSettings.api_key = existingKey;
      
      // Auto trigger model fetch for the new provider
      fetchModelsList(value, existingKey, updatedSettings.base_url);
    }

    // Auto-adjust token limits and context chunk size when the model is selected
    if (name === 'model') {
      const limits = modelsLimits[value] || getModelLimits(value);
      updatedSettings.max_output_tokens = limits.maxOutputTokens;
      updatedSettings.chunk_size = limits.chunkSize;
    }

    setSettings(updatedSettings);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaveStatus(null);
    try {
      await api.updateSettings(settings);
      setSaveStatus({ type: 'success', message: 'Settings saved successfully!' });
      setTimeout(() => setSaveStatus(null), 3000);
    } catch (err: any) {
      setSaveStatus({ type: 'error', message: `Failed to save: ${err.message}` });
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestStatus(null);
    try {
      const res = await api.testConnection({
        provider: settings.provider,
        api_key: settings.api_key,
        base_url: settings.base_url,
        model: settings.model,
        temperature: settings.temperature,
      });

      if (res.success) {
        setTestStatus({ type: 'success', message: res.message });
      } else {
        setTestStatus({ type: 'error', message: res.message });
      }
    } catch (err: any) {
      setTestStatus({ type: 'error', message: err.message || 'Connection test failed.' });
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <RefreshCw className="h-6 w-6 animate-spin text-indigo-600" />
        <span className="ml-3 text-slate-600 text-sm">Loading configurations...</span>
      </div>
    );
  }

  return (
    <form onSubmit={handleSave} className="space-y-6">
      {/* Provider Details Card */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <h3 className="text-base font-bold text-slate-800 mb-4">LLM API Provider Settings</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Provider</label>
            <select
              name="provider"
              value={settings.provider}
              onChange={handleChange}
              className="w-full rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:border-indigo-500 focus:bg-white outline-none"
            >
              <option value="mock">Mock LLM Provider (No API keys needed)</option>
              <option value="openai">OpenAI / GPT</option>
              <option value="gemini">Google Gemini</option>
              <option value="openrouter">OpenRouter</option>
              <option value="ollama">Ollama Local</option>
              <option value="lmstudio">LM Studio Local</option>
              <option value="openai_compatible">Generic OpenAI-Compatible Gateway</option>
            </select>
          </div>

          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider">Model Name</label>
              <button
                type="button"
                onClick={() => fetchModelsList()}
                disabled={loadingModels}
                className="text-[10px] text-indigo-650 hover:text-indigo-800 font-semibold flex items-center space-x-1 disabled:opacity-50"
                title="Fetch models list from provider"
              >
                <RefreshCw className={`h-3 w-3 ${loadingModels ? 'animate-spin' : ''}`} />
                <span>Fetch Models</span>
              </button>
            </div>
            
            {models.length > 0 ? (
              <select
                name="model"
                value={settings.model}
                onChange={handleChange}
                className="w-full rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:border-indigo-500 focus:bg-white outline-none"
              >
                <option value="">-- Select a Model --</option>
                {models.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            ) : (
              <div className="relative">
                <input
                  type="text"
                  name="model"
                  value={settings.model}
                  onChange={handleChange}
                  placeholder="e.g. gpt-4o, gemini-1.5-flash, llama3"
                  className="w-full rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:border-indigo-500 focus:bg-white outline-none"
                />
                {loadingModels && (
                  <div className="absolute right-3 top-3">
                    <RefreshCw className="h-4 w-4 animate-spin text-slate-400" />
                  </div>
                )}
              </div>
            )}
            
            {modelsError && settings.provider !== 'mock' && (
              <p className="text-[10px] text-slate-400 mt-1 italic">
                Note: Could not list models ({modelsError}). Enter name manually.
              </p>
            )}
          </div>

          {settings.provider !== 'mock' && settings.provider !== 'ollama' && (
            <div className="md:col-span-2">
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">API Key</label>
              <input
                type="password"
                name="api_key"
                value={settings.api_key}
                onChange={handleChange}
                placeholder={settings.provider === 'lmstudio' ? 'Optional (default is lm-studio)' : 'Enter your provider API Key'}
                className="w-full rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:border-indigo-500 focus:bg-white outline-none"
              />
            </div>
          )}

          {settings.provider !== 'mock' && settings.provider !== 'gemini' && (
            <div className="md:col-span-2">
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Base URL</label>
              <input
                type="text"
                name="base_url"
                value={settings.base_url}
                onChange={handleChange}
                placeholder={
                  settings.provider === 'ollama' ? 'http://localhost:11434' :
                  settings.provider === 'lmstudio' ? 'http://localhost:1234/v1' :
                  settings.provider === 'openrouter' ? 'https://openrouter.ai/api/v1' :
                  settings.provider === 'openai' ? 'https://api.openai.com/v1 (Optional)' :
                  'https://api.your-endpoint.com/v1'
                }
                className="w-full rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:border-indigo-500 focus:bg-white outline-none"
              />
            </div>
          )}
        </div>

        {/* Connection Test Panel */}
        {settings.provider !== 'mock' && (
          <div className="mt-6 border-t border-slate-100 pt-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={testing}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium rounded-lg text-xs transition-colors flex items-center space-x-2 border border-slate-200 disabled:opacity-50"
            >
              {testing ? (
                <>
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  <span>Testing connection...</span>
                </>
              ) : (
                <span>Test Connection</span>
              )}
            </button>

            {testStatus && (
              <div className={`flex items-center space-x-2 text-xs py-1 px-3 rounded-lg border ${
                testStatus.type === 'success' 
                  ? 'bg-emerald-50 text-emerald-800 border-emerald-100' 
                  : 'bg-rose-50 text-rose-800 border-rose-100'
              }`}>
                {testStatus.type === 'success' ? (
                  <CheckCircle className="h-4 w-4 text-emerald-600 flex-shrink-0" />
                ) : (
                  <XCircle className="h-4 w-4 text-rose-600 flex-shrink-0" />
                )}
                <span className="font-medium">{testStatus.message}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Analysis Strategy Card */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <h3 className="text-base font-bold text-slate-800 mb-2">Analysis Strategy</h3>
        <p className="text-xs text-slate-500 mb-4">
          Choose between Direct analysis (single prompt, suited for large LLMs) or Hierarchical Map-Reduce (incremental analysis, highly recommended for smaller LLMs or larger projects).
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Strategy</label>
            <select
              name="analysis_strategy"
              value={settings.analysis_strategy || 'direct'}
              onChange={handleChange}
              className="w-full rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:border-indigo-500 focus:bg-white outline-none"
            >
              <option value="direct">Direct (Single Prompt - Large Models)</option>
              <option value="hierarchical">Hierarchical (Map-Reduce - Local/Small Models)</option>
            </select>
          </div>

          {settings.analysis_strategy === 'hierarchical' && (
            <>
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Parallel Mapping Workers</label>
                <input
                  type="number"
                  name="map_batch_size"
                  min="1"
                  max="20"
                  value={settings.map_batch_size || 5}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:border-indigo-500 focus:bg-white outline-none"
                  title="Number of files to map in parallel. Keep lower for local models (e.g. 2-5)."
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Generation Chunk Size</label>
                <input
                  type="number"
                  name="generate_chunk_size"
                  min="1"
                  max="10"
                  value={settings.generate_chunk_size || 5}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:border-indigo-500 focus:bg-white outline-none"
                  title="Number of sections to generate in a single incremental LLM request."
                />
              </div>
            </>
          )}
        </div>
      </div>

      {/* Extraction & Size Settings */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <h3 className="text-base font-bold text-slate-800 mb-4">Pipeline limits & Extraction settings</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Max Repo Size (MB)</label>
            <input
              type="number"
              name="max_repo_size_mb"
              value={settings.max_repo_size_mb}
              onChange={handleChange}
              className="w-full rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:border-indigo-500 focus:bg-white outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Max File Size (KB)</label>
            <input
              type="number"
              name="max_file_size_kb"
              value={settings.max_file_size_kb}
              onChange={handleChange}
              className="w-full rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:border-indigo-500 focus:bg-white outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">LLM Temperature</label>
            <input
              type="number"
              name="temperature"
              min="0"
              max="2"
              step="0.1"
              value={settings.temperature}
              onChange={handleChange}
              className="w-full rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:border-indigo-500 focus:bg-white outline-none"
            />
          </div>

          <div className="md:col-span-3">
            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Output Directory</label>
            <input
              type="text"
              name="output_dir"
              value={settings.output_dir}
              onChange={handleChange}
              placeholder="Path to save blueprint files"
              className="w-full rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:border-indigo-500 focus:bg-white outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Max Output Tokens</label>
            <input
              type="number"
              name="max_output_tokens"
              value={settings.max_output_tokens}
              onChange={handleChange}
              className="w-full rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:border-indigo-500 focus:bg-white outline-none"
            />
          </div>

          <div className="md:col-span-2">
            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Context Window / Chunk Size (chars)</label>
            <input
              type="number"
              name="chunk_size"
              value={settings.chunk_size}
              onChange={handleChange}
              className="w-full rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:border-indigo-500 focus:bg-white outline-none"
              title="Limits total repository files content character size sent to the model to avoid exceeding the context limit."
            />
          </div>
        </div>

        <div className="mt-6 border-t border-slate-100 pt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Default GitHub Token (Optional)</label>
            <input
              type="password"
              name="github_token"
              value={settings.github_token}
              onChange={handleChange}
              placeholder="Use for private repositories"
              className="w-full rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:border-indigo-500 focus:bg-white outline-none"
            />
          </div>

          <div className="flex items-center mt-6">
            <label className="flex items-center space-x-3 cursor-pointer">
              <input
                type="checkbox"
                name="keep_cloned_repos"
                checked={settings.keep_cloned_repos}
                onChange={handleChange}
                className="h-4.5 w-4.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              />
              <div>
                <span className="block text-sm font-semibold text-slate-700">Keep cloned workspace repositories</span>
                <span className="block text-xs text-slate-400">If unchecked, repo clones are deleted immediately after blueprints are written.</span>
              </div>
            </label>
          </div>
        </div>
      </div>

      {/* Save Status & Action */}
      <div className="flex items-center justify-between border-t border-slate-100 pt-6">
        <div>
          {saveStatus && (
            <div className={`text-sm font-medium ${saveStatus.type === 'success' ? 'text-emerald-600' : 'text-rose-600'}`}>
              {saveStatus.message}
            </div>
          )}
        </div>
        
        <button
          type="submit"
          disabled={saving}
          className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-lg text-sm transition-colors flex items-center space-x-2 shadow-sm disabled:opacity-50"
        >
          {saving ? (
            <RefreshCw className="h-4 w-4 animate-spin" />
          ) : (
            <Save className="h-4 w-4" />
          )}
          <span>Save Settings</span>
        </button>
      </div>
    </form>
  );
};
