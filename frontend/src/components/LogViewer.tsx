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
    <div className="border border-slate-200 rounded-lg overflow-hidden shadow-sm bg-slate-900 text-slate-100 mt-6">
      {/* Header */}
      <div 
        className="flex items-center justify-between px-4 py-3 bg-slate-850 border-b border-slate-800 cursor-pointer"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-center space-x-2">
          <Terminal className="h-4 w-4 text-indigo-400" />
          <span className="font-semibold text-sm">Execution Logs</span>
          <span className="text-xs bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full font-mono">
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
        <div className="p-4 bg-slate-950 font-mono text-xs">
          <div className="flex items-center justify-between mb-2 text-slate-400 border-b border-slate-800 pb-2">
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
            className="h-64 overflow-y-auto space-y-1.5 pr-2 scrollbar-thin scrollbar-thumb-slate-850"
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
