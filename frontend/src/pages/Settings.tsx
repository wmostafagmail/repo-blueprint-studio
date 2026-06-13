import React from 'react';
import { SettingsForm } from '../components/SettingsForm';

export const Settings: React.FC = () => {
  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-800">Studio Settings</h1>
        <p className="text-xs text-slate-400 mt-1">Configure LLM providers, model specifications, parameters, and workspace limits.</p>
      </div>

      <SettingsForm />
    </div>
  );
};
