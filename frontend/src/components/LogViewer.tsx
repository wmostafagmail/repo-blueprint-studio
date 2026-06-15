import React, { useEffect, useRef, useState } from 'react';
import { Terminal, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react';
import { JobLog } from '../api';

interface LogViewerProps {
  logs: JobLog[];
  onRefresh?: () => void;
  isLoading?: boolean;
}

export const LogViewer: React.FC<LogViewerProps> = ({ logs, onRefresh, isLoading = false }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs, autoScroll, isOpen]);

  return (
    <div className="glass-dark mt-6 overflow-hidden rounded-[28px] text-slate-100">
      {/* Header */}
      <div 
        className="flex cursor-pointer items-center justify-between border-b border-slate-700/70 bg-white/5 px-4 py-3"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-center space-x-2">
          <Terminal className="h-4 w-4 text-indigo-400" />
          <span className="font-semibold text-sm">Execution Logs</span>
            <span className="rounded-full border border-slate-700 bg-slate-800/80 px-2 py-0.5 font-mono text-xs text-slate-400">
            {logs.length} entries
          </span>
        </div>
        <div className="flex items-center space-x-4">
          {onRefresh && (
            <button 
              onClick={(e) => {
                e.stopPropagation();
                onRefresh();
              }}
              disabled={isLoading}
              className="text-slate-400 hover:text-white transition-colors"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          )}
          {isOpen ? (
            <ChevronUp className="h-4 w-4 text-slate-400" />
          ) : (
            <ChevronDown className="h-4 w-4 text-slate-400" />
          )}
        </div>
      </div>

      {/* Body */}
      {isOpen && (
        <div className="bg-slate-950/70 p-4 font-mono text-xs">
          <div className="mb-2 flex items-center justify-between border-b border-slate-800 pb-2 text-slate-400">
            <label className="flex items-center space-x-2 cursor-pointer">
              <input 
                type="checkbox" 
                checked={autoScroll} 
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="rounded text-indigo-600 bg-slate-800 border-slate-700" 
              />
              <span>Auto-scroll to bottom</span>
            </label>
          </div>

          <div 
            ref={containerRef}
            className="h-72 space-y-1.5 overflow-y-auto pr-2"
          >
            {logs.length === 0 ? (
              <div className="text-slate-500 italic py-8 text-center">No logs generated yet...</div>
            ) : (
              logs.map((log) => {
                const logTime = new Date(log.created_at).toLocaleTimeString();
                let levelColor = 'text-slate-400';
                if (log.level === 'WARNING') levelColor = 'text-amber-400';
                if (log.level === 'ERROR') levelColor = 'text-rose-500 font-bold';
                
                return (
                  <div key={log.id} className="flex items-start space-x-2 hover:bg-slate-900 py-0.5 px-1 rounded transition-colors">
                    <span className="text-slate-600 select-none">{logTime}</span>
                    <span className={`w-14 font-semibold select-none ${levelColor}`}>[{log.level}]</span>
                    <span className="text-slate-300 break-words flex-1">{log.message}</span>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
};
