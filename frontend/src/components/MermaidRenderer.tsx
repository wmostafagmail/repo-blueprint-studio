import React, { useEffect, useRef, useState } from 'react';
import { ZoomIn, ZoomOut, Maximize2, Move, AlertTriangle, RefreshCw } from 'lucide-react';

interface MermaidRendererProps {
  markdown: string;
  inventory?: any; // raw inventory JSON, used to auto-generate diagrams if markdown has none
}

interface DiagramEntry {
  title: string;
  chart: string;
}

// ─── Extract Mermaid fences from blueprint markdown ──────────────────────────
const extractMermaidCharts = (md: string): DiagramEntry[] => {
  const regex = /```mermaid([\s\S]*?)```/g;
  const results: DiagramEntry[] = [];
  let match;
  let index = 1;
  while ((match = regex.exec(md)) !== null) {
    const chart = match[1].trim();
    let title = `Diagram ${index++}`;
    const lines = chart.split('\n');
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith('%%') && trimmed.replace('%%', '').trim().length > 3) {
        title = trimmed.replace('%%', '').trim();
        break;
      }
    }
    results.push({ title, chart });
  }
  return results;
};

// ─── Build diagrams from inventory data ─────────────────────────────────────
const buildInventoryDiagrams = (inventory: any): DiagramEntry[] => {
  if (!inventory || !inventory.files) return [];

  const files: Array<{ path: string; extension: string; size_bytes: number }> = inventory.files;
  const repoName: string = inventory.repo_name || 'Repository';

  // 1️⃣  Group files by top-level directory (component)
  const componentMap: Record<string, { files: number; size: number; exts: Set<string> }> = {};
  const rootFiles: string[] = [];

  for (const f of files) {
    const parts = f.path.split('/');
    if (parts.length === 1) {
      rootFiles.push(f.path);
      const key = 'root';
      if (!componentMap[key]) componentMap[key] = { files: 0, size: 0, exts: new Set() };
      componentMap[key].files++;
      componentMap[key].size += f.size_bytes;
      if (f.extension) componentMap[key].exts.add(f.extension.replace('.', '').toUpperCase());
    } else {
      const key = parts[0];
      if (!componentMap[key]) componentMap[key] = { files: 0, size: 0, exts: new Set() };
      componentMap[key].files++;
      componentMap[key].size += f.size_bytes;
      if (f.extension) componentMap[key].exts.add(f.extension.replace('.', '').toUpperCase());
    }
  }

  // Sort components by file count descending, cap at 12 for legibility
  const sortedComponents = Object.entries(componentMap)
    .sort((a, b) => b[1].files - a[1].files)
    .slice(0, 12);

  // ── Diagram 1: Component Architecture ──────────────────────────────────────
  const sanitize = (s: string) => s.replace(/[^a-zA-Z0-9_]/g, '_').replace(/^_+/, '');
  const nodeId = (name: string) => `comp_${sanitize(name)}`;

  const componentLines: string[] = [
    `%% Component Architecture — ${repoName}`,
    'flowchart TD',
    `    REPO["🗂️ ${repoName}"]`,
  ];

  for (const [name, meta] of sortedComponents) {
    const id = nodeId(name);
    const label = name === 'root' ? 'Root Files' : name;
    const extList = Array.from(meta.exts).slice(0, 3).join(', ');
    const kb = Math.round(meta.size / 1024);
    const nodeLabel = extList
      ? `${label}\\n${meta.files} files · ${kb} KB\\n[${extList}]`
      : `${label}\\n${meta.files} files · ${kb} KB`;
    componentLines.push(`    ${id}["${nodeLabel}"]`);
    componentLines.push(`    REPO --> ${id}`);
  }

  // Add sub-directory relationships for top 5 components
  for (const [name] of sortedComponents.slice(0, 5)) {
    const subDirs: Record<string, number> = {};
    for (const f of files) {
      const parts = f.path.split('/');
      const top = parts.length === 1 ? 'root' : parts[0];
      if (top === name && parts.length >= 3) {
        const sub = parts[1];
        subDirs[sub] = (subDirs[sub] || 0) + 1;
      }
    }
    const topSubs = Object.entries(subDirs).sort((a, b) => b[1] - a[1]).slice(0, 3);
    for (const [sub, count] of topSubs) {
      const parentId = nodeId(name);
      const subId = `${nodeId(name)}_${sanitize(sub)}`;
      componentLines.push(`    ${subId}["${sub}\\n${count} files"]`);
      componentLines.push(`    ${parentId} --> ${subId}`);
    }
  }

  // ── Diagram 2: Language / Extension Breakdown ────────────────────────────
  const extCounts: Record<string, number> = inventory.summary?.extension_counts || {};
  const topExts = Object.entries(extCounts)
    .filter(([ext]) => ext && ext !== '[no extension]')
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  const langLines: string[] = [
    `%% Language Breakdown — ${repoName}`,
    'pie title File Types by Count',
  ];

  const EXT_LABELS: Record<string, string> = {
    '.py': 'Python', '.ts': 'TypeScript', '.js': 'JavaScript',
    '.go': 'Go', '.rs': 'Rust', '.java': 'Java', '.kt': 'Kotlin',
    '.swift': 'Swift', '.rb': 'Ruby', '.cs': 'C#', '.cpp': 'C++',
    '.c': 'C', '.md': 'Markdown', '.json': 'JSON', '.yaml': 'YAML',
    '.yml': 'YAML', '.toml': 'TOML', '.sql': 'SQL', '.html': 'HTML',
    '.css': 'CSS', '.sh': 'Shell', '.php': 'PHP', '.scala': 'Scala',
    '.ex': 'Elixir', '.jl': 'Julia',
  };

  for (const [ext, count] of topExts) {
    const label = EXT_LABELS[ext] || ext.replace('.', '').toUpperCase();
    langLines.push(`    "${label}" : ${count}`);
  }

  // ── Diagram 3: File Size Distribution by Component ───────────────────────
  const sizeLines: string[] = [
    `%% Code Volume by Component — ${repoName}`,
    'pie title Code Volume (KB) by Top Components',
  ];

  for (const [name, meta] of sortedComponents.slice(0, 8)) {
    const label = name === 'root' ? 'Root' : name;
    const kb = Math.round(meta.size / 1024);
    if (kb > 0) sizeLines.push(`    "${label}" : ${kb}`);
  }

  const diagrams: DiagramEntry[] = [
    { title: '🏗️ Component Architecture', chart: componentLines.join('\n') },
  ];
  if (topExts.length > 0) {
    diagrams.push({ title: '📊 Language Breakdown', chart: langLines.join('\n') });
  }
  if (sortedComponents.length > 0) {
    diagrams.push({ title: '📦 Code Volume by Component', chart: sizeLines.join('\n') });
  }

  return diagrams;
};

// ─── Component ───────────────────────────────────────────────────────────────
export const MermaidRenderer: React.FC<MermaidRendererProps> = ({ markdown, inventory }) => {
  const [diagrams, setDiagrams] = useState<DiagramEntry[]>([]);
  const [activeIndex, setActiveIndex] = useState<number>(0);
  const [zoom, setZoom] = useState<number>(1);
  const [isReady, setIsReady] = useState<boolean>(false);
  const [renderError, setRenderError] = useState<string | null>(null);
  const [source, setSource] = useState<'blueprint' | 'inventory' | 'none'>('none');

  const containerRef = useRef<HTMLDivElement>(null);

  // Decide diagram source
  useEffect(() => {
    const fromBlueprint = extractMermaidCharts(markdown);
    if (fromBlueprint.length > 0) {
      setDiagrams(fromBlueprint);
      setSource('blueprint');
    } else if (inventory) {
      const fromInventory = buildInventoryDiagrams(inventory);
      setDiagrams(fromInventory);
      setSource(fromInventory.length > 0 ? 'inventory' : 'none');
    } else {
      setDiagrams([]);
      setSource('none');
    }
    setActiveIndex(0);
    setZoom(1);
    setRenderError(null);
    setIsReady(false);
  }, [markdown, inventory]);

  // Load Mermaid.js from CDN once diagrams are ready
  useEffect(() => {
    if (diagrams.length === 0) return;

    const scriptId = 'mermaid-cdn-script';
    let script = document.getElementById(scriptId) as HTMLScriptElement;

    const initMermaid = () => {
      try {
        const m = (window as any).mermaid;
        m.initialize({
          startOnLoad: false,
          theme: 'dark',
          securityLevel: 'loose',
          flowchart: { useMaxWidth: false, htmlLabels: true, curve: 'basis' },
          pie: { textPosition: 0.5 },
          themeVariables: {
            background: '#0f172a',
            primaryColor: '#4f46e5',
            primaryTextColor: '#f8fafc',
            secondaryColor: '#1e293b',
            tertiaryColor: '#334155',
            lineColor: '#6366f1',
            edgeLabelBackground: '#1e293b',
            clusterBkg: '#1e293b',
            titleColor: '#c7d2fe',
            pie1: '#6366f1', pie2: '#8b5cf6', pie3: '#ec4899',
            pie4: '#06b6d4', pie5: '#10b981', pie6: '#f59e0b',
            pie7: '#ef4444', pie8: '#3b82f6', pie9: '#a855f7',
            pie10: '#14b8a6',
          }
        });
        setIsReady(true);
      } catch (err: any) {
        setRenderError(err.message || 'Mermaid initialization failed');
      }
    };

    if (!script) {
      script = document.createElement('script');
      script.id = scriptId;
      script.src = 'https://cdn.jsdelivr.net/npm/mermaid@10.9.0/dist/mermaid.min.js';
      script.async = true;
      script.onload = initMermaid;
      script.onerror = () => setRenderError('Failed to load Mermaid parser from CDN');
      document.body.appendChild(script);
    } else if ((window as any).mermaid) {
      initMermaid();
    } else {
      const interval = setInterval(() => {
        if ((window as any).mermaid) { initMermaid(); clearInterval(interval); }
      }, 100);
      return () => clearInterval(interval);
    }
  }, [diagrams]);

  // Re-render whenever active diagram or ready state changes
  useEffect(() => {
    if (!isReady || diagrams.length === 0) return;
    renderChart();
  }, [isReady, activeIndex, diagrams]);

  const renderChart = async () => {
    if (diagrams.length === 0 || !containerRef.current) return;
    setRenderError(null);

    const m = (window as any).mermaid;
    if (!m) return;

    const currentDiagram = diagrams[activeIndex];
    containerRef.current.innerHTML = '';

    const uniqueId = `mermaid-svg-${Date.now()}`;

    try {
      const { svg } = await m.render(uniqueId, currentDiagram.chart);
      if (containerRef.current) {
        containerRef.current.innerHTML = svg;
        const svgElement = containerRef.current.querySelector('svg');
        if (svgElement) {
          svgElement.setAttribute('style', 'max-width: 100%; height: auto; display: block; margin: auto;');
        }
      }
    } catch (err: any) {
      console.error('Mermaid render error:', err, '\nChart:\n', currentDiagram.chart);
      const badElement = document.getElementById(uniqueId);
      if (badElement) badElement.remove();
      setRenderError('Failed to render diagram. The chart syntax may be invalid for this Mermaid version.');
    }
  };

  const handleZoomIn = () => setZoom(z => Math.min(z + 0.2, 3));
  const handleZoomOut = () => setZoom(z => Math.max(z - 0.2, 0.4));
  const handleZoomReset = () => setZoom(1);

  if (diagrams.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12 bg-slate-900 border border-slate-800 rounded-2xl text-center space-y-3">
        <AlertTriangle className="h-8 w-8 text-amber-500" />
        <h3 className="text-slate-200 font-semibold">No Diagrams Found</h3>
        <p className="text-slate-400 text-sm max-w-sm">
          No architecture diagrams could be generated. Try re-running the analysis — the LLM will now be instructed to produce Mermaid diagrams.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-slate-950 border border-slate-800 rounded-2xl overflow-hidden flex flex-col h-[600px] shadow-2xl relative">
      {/* Header */}
      <div className="bg-slate-900 border-b border-slate-800 px-5 py-3 flex flex-col sm:flex-row justify-between items-center gap-3">
        <div className="flex items-center space-x-3">
          <Maximize2 className="h-4 w-4 text-indigo-400 shrink-0" />
          <div>
            <h3 className="text-slate-200 font-semibold text-sm leading-none">
              Architecture Viewer
            </h3>
            {source === 'inventory' && (
              <span className="text-[10px] text-indigo-400 font-medium mt-0.5 block">
                Auto-generated from repository inventory
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {/* Diagram Selector */}
          {diagrams.length > 1 && (
            <select
              value={activeIndex}
              onChange={(e) => { setActiveIndex(Number(e.target.value)); setZoom(1); }}
              className="bg-slate-800 text-slate-200 text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-700 focus:outline-none focus:border-indigo-500 max-w-[220px]"
            >
              {diagrams.map((d, idx) => (
                <option key={idx} value={idx}>{d.title}</option>
              ))}
            </select>
          )}

          {/* Zoom Controls */}
          <div className="flex items-center bg-slate-800 rounded-lg p-0.5 border border-slate-700">
            <button
              onClick={handleZoomOut}
              disabled={!!renderError}
              className="p-1.5 hover:bg-slate-700 rounded-md text-slate-400 hover:text-slate-200 disabled:opacity-40 transition-colors"
              title="Zoom Out"
            >
              <ZoomOut className="h-3.5 w-3.5" />
            </button>
            <span className="text-[10px] font-bold text-slate-400 px-2 select-none w-10 text-center">
              {Math.round(zoom * 100)}%
            </span>
            <button
              onClick={handleZoomIn}
              disabled={!!renderError}
              className="p-1.5 hover:bg-slate-700 rounded-md text-slate-400 hover:text-slate-200 disabled:opacity-40 transition-colors"
              title="Zoom In"
            >
              <ZoomIn className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={handleZoomReset}
              disabled={!!renderError}
              className="p-1 text-[10px] font-bold text-indigo-400 hover:text-indigo-300 px-2 border-l border-slate-700"
            >
              Reset
            </button>
          </div>
        </div>
      </div>

      {/* Diagram title strip */}
      <div className="bg-slate-900/60 border-b border-slate-800/60 px-5 py-2 flex items-center space-x-2">
        <span className="text-xs font-semibold text-indigo-300">{diagrams[activeIndex]?.title}</span>
        <span className="text-[10px] text-slate-500">· {diagrams.length} diagram{diagrams.length !== 1 ? 's' : ''} total</span>
      </div>

      {/* Render Area */}
      <div className="flex-1 overflow-auto relative p-6 bg-slate-950 flex items-center justify-center cursor-grab active:cursor-grabbing">
        {renderError ? (
          <div className="flex flex-col items-center max-w-md text-center p-6 bg-rose-950/20 border border-rose-900/40 rounded-xl space-y-3">
            <AlertTriangle className="h-8 w-8 text-rose-500" />
            <h4 className="text-rose-300 font-semibold text-sm">Render Error</h4>
            <p className="text-slate-400 text-xs leading-relaxed">{renderError}</p>
          </div>
        ) : !isReady ? (
          <div className="flex items-center space-x-3 text-slate-400 text-sm">
            <RefreshCw className="h-5 w-5 animate-spin text-indigo-500" />
            <span>Compiling diagram…</span>
          </div>
        ) : (
          <div
            ref={containerRef}
            style={{
              transform: `scale(${zoom})`,
              transformOrigin: 'center center',
              transition: 'transform 0.15s ease-out'
            }}
            className="w-full h-full flex items-center justify-center"
          />
        )}

        {!renderError && isReady && (
          <div className="absolute bottom-4 right-4 bg-slate-900/80 border border-slate-800/80 rounded-full px-3 py-1 flex items-center space-x-1.5 pointer-events-none backdrop-blur-sm select-none">
            <Move className="h-3.5 w-3.5 text-slate-500" />
            <span className="text-[10px] font-semibold text-slate-400">Scroll to zoom · Drag to pan</span>
          </div>
        )}
      </div>
    </div>
  );
};
