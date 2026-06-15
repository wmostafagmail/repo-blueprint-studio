import React from 'react';
import { SettingsForm } from '../components/SettingsForm';

export const Settings: React.FC = () => {
  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="section-card">
        <div className="inline-flex rounded-full border border-white/70 bg-white/70 px-3 py-1.5 text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">
          Studio Controls
        </div>
        <h1 className="mt-4 text-3xl font-extrabold tracking-tight text-slate-900">Settings</h1>
        <p className="mt-2 max-w-2xl text-sm leading-7 text-slate-600">
          Configure providers, tune model limits, and shape how the analysis pipeline behaves without changing the core workflow.
        </p>
      </div>

      <SettingsForm />
    </div>
  );
};
