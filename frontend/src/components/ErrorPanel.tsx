import React from 'react';
import { AlertCircle } from 'lucide-react';

interface ErrorPanelProps {
  error: string | null;
  title?: string;
}

export const ErrorPanel: React.FC<ErrorPanelProps> = ({ error, title = "An error occurred" }) => {
  if (!error) return null;

  return (
    <div className="rounded-lg bg-rose-50 border border-rose-100 p-4 my-4 flex items-start space-x-3 text-rose-800">
      <AlertCircle className="h-5 w-5 text-rose-600 flex-shrink-0 mt-0.5" />
      <div>
        <h3 className="font-semibold text-sm leading-5">{title}</h3>
        <p className="mt-1 text-xs text-rose-700 leading-normal font-mono break-all">{error}</p>
      </div>
    </div>
  );
};
