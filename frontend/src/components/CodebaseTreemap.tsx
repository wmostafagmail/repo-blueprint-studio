import React, { useState, useMemo, useCallback } from 'react';
import { Search, FolderOpen, ArrowLeft, Info, HardDrive, FileText, Code2, Hash } from 'lucide-react';

// ── Types ────────────────────────────────────────────────────────────────────

interface FileEntry {
  path: string;
  extension?: string;
  size_bytes: number;
}

interface TreeNode {
  name: string;
  path: string;
  value: number;
  children?: TreeNode[];
  isDir: boolean;
  ext?: string;
}

interface TreemapProps {
  inventory: {
    files: FileEntry[];
    repo_name?: string;
    summary?: any;
  };
}

interface Rect {
  x: number; y: number; w: number; h: number;
  node: TreeNode;
  fill: string;
  fillHover: string;
  stroke: string;
  textColor: string;
  labelBg: string;
  depth: number;
  dominantExt?: string;
}

// ── Color System ─────────────────────────────────────────────────────────────
// Each language/extension gets a vibrant hue. Directories inherit the dominant
// language color of their children (slightly desaturated).

const EXT_PALETTE: Record<string, { fill: string; fillHover: string; stroke: string; text: string; label: string; name: string }> = {
  // Languages – rich, distinguishable hues
  py:     { fill: '#1d4ed8', fillHover: '#2563eb', stroke: '#3b82f6', text: '#bfdbfe', label: '#1e40af', name: 'Python' },
  ts:     { fill: '#0e7490', fillHover: '#0891b2', stroke: '#22d3ee', text: '#cffafe', label: '#0c4a6e', name: 'TypeScript' },
  tsx:    { fill: '#0369a1', fillHover: '#0284c7', stroke: '#38bdf8', text: '#e0f2fe', label: '#082f49', name: 'TSX' },
  js:     { fill: '#854d0e', fillHover: '#a16207', stroke: '#fbbf24', text: '#fef08a', label: '#713f12', name: 'JavaScript' },
  jsx:    { fill: '#7c3aed', fillHover: '#6d28d9', stroke: '#a78bfa', text: '#ede9fe', label: '#4c1d95', name: 'JSX' },
  go:     { fill: '#0f766e', fillHover: '#0d9488', stroke: '#2dd4bf', text: '#ccfbf1', label: '#134e4a', name: 'Go' },
  rs:     { fill: '#c2410c', fillHover: '#ea580c', stroke: '#fb923c', text: '#ffedd5', label: '#7c2d12', name: 'Rust' },
  java:   { fill: '#b45309', fillHover: '#d97706', stroke: '#fbbf24', text: '#fef3c7', label: '#78350f', name: 'Java' },
  kt:     { fill: '#6d28d9', fillHover: '#7c3aed', stroke: '#a78bfa', text: '#ede9fe', label: '#3b0764', name: 'Kotlin' },
  swift:  { fill: '#dc2626', fillHover: '#ef4444', stroke: '#f87171', text: '#fee2e2', label: '#991b1b', name: 'Swift' },
  rb:     { fill: '#be185d', fillHover: '#db2777', stroke: '#f472b6', text: '#fce7f3', label: '#831843', name: 'Ruby' },
  cs:     { fill: '#4338ca', fillHover: '#4f46e5', stroke: '#818cf8', text: '#e0e7ff', label: '#312e81', name: 'C#' },
  cpp:    { fill: '#1e40af', fillHover: '#2563eb', stroke: '#60a5fa', text: '#dbeafe', label: '#1e3a8a', name: 'C++' },
  c:      { fill: '#1e3a8a', fillHover: '#1d4ed8', stroke: '#93c5fd', text: '#dbeafe', label: '#172554', name: 'C' },
  php:    { fill: '#5b21b6', fillHover: '#6d28d9', stroke: '#c4b5fd', text: '#ede9fe', label: '#3b0764', name: 'PHP' },
  scala:  { fill: '#991b1b', fillHover: '#b91c1c', stroke: '#f87171', text: '#fee2e2', label: '#7f1d1d', name: 'Scala' },
  ex:     { fill: '#4338ca', fillHover: '#4f46e5', stroke: '#a5b4fc', text: '#e0e7ff', label: '#1e1b4b', name: 'Elixir' },
  jl:     { fill: '#1d4ed8', fillHover: '#2563eb', stroke: '#93c5fd', text: '#dbeafe', label: '#1e3a8a', name: 'Julia' },
  r:      { fill: '#1d4ed8', fillHover: '#2563eb', stroke: '#7dd3fc', text: '#e0f2fe', label: '#0c4a6e', name: 'R' },
  lua:    { fill: '#1e40af', fillHover: '#1d4ed8', stroke: '#60a5fa', text: '#dbeafe', label: '#172554', name: 'Lua' },
  dart:   { fill: '#0369a1', fillHover: '#0284c7', stroke: '#38bdf8', text: '#e0f2fe', label: '#082f49', name: 'Dart' },
  sh:     { fill: '#065f46', fillHover: '#047857', stroke: '#34d399', text: '#d1fae5', label: '#022c22', name: 'Shell' },
  bash:   { fill: '#065f46', fillHover: '#047857', stroke: '#34d399', text: '#d1fae5', label: '#022c22', name: 'Bash' },
  ps1:    { fill: '#1e3a8a', fillHover: '#1d4ed8', stroke: '#60a5fa', text: '#dbeafe', label: '#172554', name: 'PowerShell' },
  // Data / Config
  json:   { fill: '#166534', fillHover: '#15803d', stroke: '#4ade80', text: '#dcfce7', label: '#14532d', name: 'JSON' },
  yaml:   { fill: '#b45309', fillHover: '#ca8a04', stroke: '#fde047', text: '#fef9c3', label: '#78350f', name: 'YAML' },
  yml:    { fill: '#b45309', fillHover: '#ca8a04', stroke: '#fde047', text: '#fef9c3', label: '#78350f', name: 'YAML' },
  toml:   { fill: '#78350f', fillHover: '#92400e', stroke: '#fdba74', text: '#ffedd5', label: '#431407', name: 'TOML' },
  xml:    { fill: '#4338ca', fillHover: '#4f46e5', stroke: '#a5b4fc', text: '#e0e7ff', label: '#1e1b4b', name: 'XML' },
  sql:    { fill: '#854d0e', fillHover: '#a16207', stroke: '#fcd34d', text: '#fef3c7', label: '#451a03', name: 'SQL' },
  csv:    { fill: '#166534', fillHover: '#15803d', stroke: '#86efac', text: '#dcfce7', label: '#14532d', name: 'CSV' },
  // Markup / Docs
  md:     { fill: '#374151', fillHover: '#4b5563', stroke: '#9ca3af', text: '#f3f4f6', label: '#1f2937', name: 'Markdown' },
  html:   { fill: '#9a3412', fillHover: '#c2410c', stroke: '#fb923c', text: '#ffedd5', label: '#7c2d12', name: 'HTML' },
  css:    { fill: '#0c4a6e', fillHover: '#075985', stroke: '#38bdf8', text: '#e0f2fe', label: '#082f49', name: 'CSS' },
  scss:   { fill: '#831843', fillHover: '#9d174d', stroke: '#f9a8d4', text: '#fce7f3', label: '#500724', name: 'SCSS' },
  svg:    { fill: '#713f12', fillHover: '#854d0e', stroke: '#fde68a', text: '#fef3c7', label: '#451a03', name: 'SVG' },
  // Build / Config
  gradle: { fill: '#064e3b', fillHover: '#065f46', stroke: '#6ee7b7', text: '#d1fae5', label: '#022c22', name: 'Gradle' },
  dockerfile: { fill: '#1e3a8a', fillHover: '#1d4ed8', stroke: '#93c5fd', text: '#dbeafe', label: '#172554', name: 'Docker' },
};

const DIR_PALETTE = { fill: '#1e293b', fillHover: '#334155', stroke: '#475569', text: '#94a3b8', label: '#0f172a', name: 'Directory' };
const UNKNOWN_PALETTE = { fill: '#1a1a2e', fillHover: '#16213e', stroke: '#334155', text: '#64748b', label: '#0f0f1a', name: 'Other' };

const getExt = (filename: string): string =>
  filename.includes('.') ? filename.split('.').pop()!.toLowerCase() : '';

const getPalette = (node: TreeNode, dominantExt?: string) => {
  if (node.isDir) {
    // Directories: blend towards their dominant child language color (darker)
    if (dominantExt && EXT_PALETTE[dominantExt]) {
      const p = EXT_PALETTE[dominantExt];
      return { ...DIR_PALETTE, fill: p.label, stroke: p.stroke + '80', fillHover: p.fill };
    }
    return DIR_PALETTE;
  }
  const ext = node.ext || getExt(node.name);
  return EXT_PALETTE[ext] || UNKNOWN_PALETTE;
};

const formatSize = (bytes: number): string => {
  if (!bytes) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
};

// ── Tree Builder ─────────────────────────────────────────────────────────────

function buildFileTree(files: FileEntry[]): TreeNode {
  const root: TreeNode = { name: 'root', path: '', value: 0, children: [], isDir: true };

  for (const f of files) {
    const parts = f.path.split('/');
    let cur = root;
    let curPath = '';
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      curPath = curPath ? `${curPath}/${part}` : part;
      if (i === parts.length - 1) {
        cur.children!.push({ name: part, path: curPath, value: Math.max(f.size_bytes, 100), isDir: false, ext: f.extension?.replace('.', '') || getExt(part) });
      } else {
        let dir = cur.children!.find(c => c.name === part && c.isDir);
        if (!dir) { dir = { name: part, path: curPath, value: 0, children: [], isDir: true }; cur.children!.push(dir); }
        cur = dir;
      }
    }
  }

  const calcSizes = (node: TreeNode): number => {
    if (node.children?.length) {
      node.value = node.children.reduce((s, c) => s + calcSizes(c), 0);
    }
    return node.value;
  };
  calcSizes(root);
  return root;
}

// Compute dominant extension in a subtree
function dominantExt(node: TreeNode): string {
  const counts: Record<string, number> = {};
  const walk = (n: TreeNode) => {
    if (!n.isDir && n.ext) counts[n.ext] = (counts[n.ext] || 0) + n.value;
    n.children?.forEach(walk);
  };
  walk(node);
  return Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] || '';
}

// ── Squarified Treemap Layout ─────────────────────────────────────────────────
// Uses proper squarified algorithm for more rectangular proportions

function squarify(items: { node: TreeNode; dominantExt: string }[], x: number, y: number, w: number, h: number, rects: Rect[], depth: number) {
  if (!items.length || w < 1 || h < 1) return;

  const total = items.reduce((s, i) => s + i.node.value, 0);
  if (total === 0) return;

  // Slice-and-dice with alternating direction for squarer cells
  const vertical = w >= h;
  let pos = vertical ? x : y;

  for (const item of items) {
    const ratio = item.node.value / total;
    const cw = vertical ? w * ratio : w;
    const ch = vertical ? h : h * ratio;
    const cx = vertical ? pos : x;
    const cy = vertical ? y : pos;

    if (cw > 1 && ch > 1) {
      const p = getPalette(item.node, item.dominantExt);
      rects.push({
        x: cx, y: cy, w: cw, h: ch,
        node: item.node,
        fill: p.fill,
        fillHover: p.fillHover,
        stroke: p.stroke,
        textColor: p.text,
        labelBg: p.label,
        depth,
        dominantExt: item.dominantExt,
      });

      // Recurse into directories
      if (item.node.isDir && item.node.children?.length) {
        const pad = Math.min(2, Math.min(cw, ch) * 0.04);
        const childItems = item.node.children
          .filter(c => c.value > 0)
          .sort((a, b) => b.value - a.value)
          .map(c => ({ node: c, dominantExt: dominantExt(c) }));
        squarify(childItems, cx + pad, cy + pad, cw - pad * 2, ch - pad * 2, rects, depth + 1);
      }
    }

    if (vertical) pos += cw;
    else pos += ch;
  }
}

// ── Legend ────────────────────────────────────────────────────────────────────

const LegendDot: React.FC<{ ext: string; count?: number }> = ({ ext, count }) => {
  const p = EXT_PALETTE[ext] || UNKNOWN_PALETTE;
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: p.fill, border: `1px solid ${p.stroke}` }} />
      <span className="text-[10px] text-slate-300 font-medium">{p.name}</span>
      {count !== undefined && <span className="text-[10px] text-slate-500 ml-auto">{count}</span>}
    </div>
  );
};

// ── Main Component ─────────────────────────────────────────────────────────────

export const CodebaseTreemap: React.FC<TreemapProps> = ({ inventory }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [zoomedPath, setZoomedPath] = useState('');
  const [hoveredRect, setHoveredRect] = useState<Rect | null>(null);
  const [highlightExt, setHighlightExt] = useState<string | null>(null);

  const rootNode = useMemo(() => buildFileTree(inventory.files || []), [inventory.files]);

  // Navigate to zoomed node
  const activeNode = useMemo(() => {
    if (!zoomedPath) return rootNode;
    const parts = zoomedPath.split('/');
    let cur = rootNode;
    for (const part of parts) {
      const found = cur.children?.find(c => c.name === part && c.isDir);
      if (found) cur = found; else break;
    }
    return cur;
  }, [rootNode, zoomedPath]);

  const breadcrumbs = useMemo(() => {
    const list = [{ name: inventory.repo_name || 'Root', path: '' }];
    if (!zoomedPath) return list;
    const parts = zoomedPath.split('/');
    let running = '';
    for (const part of parts) {
      running = running ? `${running}/${part}` : part;
      list.push({ name: part, path: running });
    }
    return list;
  }, [zoomedPath, inventory.repo_name]);

  // Compute layout rects
  const W = 800, H = 440;
  const layoutRects = useMemo(() => {
    const rects: Rect[] = [];
    if (!activeNode.children?.length) return rects;
    const items = activeNode.children
      .filter(c => c.value > 0)
      .sort((a, b) => b.value - a.value)
      .map(c => ({ node: c, dominantExt: dominantExt(c) }));
    squarify(items, 0, 0, W, H, rects, 0);
    return rects;
  }, [activeNode]);

  // Search matching
  const matchedPaths = useMemo(() => {
    if (!searchQuery.trim()) return null;
    const lower = searchQuery.toLowerCase();
    return new Set(inventory.files.filter(f => f.path.toLowerCase().includes(lower)).map(f => f.path));
  }, [inventory.files, searchQuery]);

  // Extension legend derived from current view
  const legendExts = useMemo(() => {
    const exts: Record<string, number> = {};
    for (const r of layoutRects) {
      if (!r.node.isDir) {
        const ext = r.node.ext || getExt(r.node.name);
        if (ext) exts[ext] = (exts[ext] || 0) + 1;
      } else if (r.dominantExt) {
        exts[r.dominantExt] = (exts[r.dominantExt] || 0) + 1;
      }
    }
    return Object.entries(exts).sort((a, b) => b[1] - a[1]).slice(0, 12);
  }, [layoutRects]);

  const handleRectClick = (r: Rect) => {
    if (r.node.isDir) {
      setZoomedPath(r.node.path);
    }
  };

  const zoomOut = () => {
    const parts = zoomedPath.split('/');
    parts.pop();
    setZoomedPath(parts.join('/'));
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl flex flex-col gap-0">

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3 px-5 py-3 bg-slate-900 border-b border-slate-800">
        {/* Breadcrumb */}
        <div className="flex items-center gap-1 text-xs font-semibold flex-wrap">
          {breadcrumbs.map((b, idx) => (
            <React.Fragment key={b.path}>
              {idx > 0 && <span className="text-slate-600">/</span>}
              <button
                onClick={() => setZoomedPath(b.path)}
                className={`hover:text-indigo-300 transition-colors ${idx === breadcrumbs.length - 1 ? 'text-indigo-400' : 'text-slate-400'}`}
              >
                {b.name}
              </button>
            </React.Fragment>
          ))}
        </div>

        {zoomedPath && (
          <button
            onClick={zoomOut}
            className="flex items-center gap-1 text-[11px] font-bold text-slate-300 hover:text-slate-100 bg-slate-800 border border-slate-700 px-2.5 py-1 rounded-lg transition-all ml-auto"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Zoom Out
          </button>
        )}

        {/* Search */}
        <div className="relative ml-auto">
          <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-slate-500" />
          <input
            type="text"
            placeholder="Search files…"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 w-44 placeholder:text-slate-600"
          />
        </div>
      </div>

      {/* Main content row */}
      <div className="flex flex-col lg:flex-row">
        {/* SVG Treemap */}
        <div className="flex-1 relative bg-slate-950">
          <svg
            viewBox={`0 0 ${W} ${H}`}
            className="w-full h-auto select-none"
            onMouseLeave={() => setHoveredRect(null)}
          >
            {/* Background */}
            <rect width={W} height={H} fill="#020617" />

            {layoutRects.map((r, idx) => {
              const isSearching = !!matchedPaths;
              const isMatched = matchedPaths ? matchedPaths.has(r.node.path) : true;
              const isExtHL = highlightExt ? (r.node.ext === highlightExt || r.dominantExt === highlightExt) : true;
              const dimmed = (isSearching && !isMatched) || (!isExtHL);
              const isHovered = hoveredRect?.node.path === r.node.path;

              return (
                <g
                  key={idx}
                  onMouseEnter={() => setHoveredRect(r)}
                  onClick={() => handleRectClick(r)}
                  style={{ cursor: r.node.isDir ? 'pointer' : 'default', opacity: dimmed ? 0.15 : 1, transition: 'opacity 0.2s' }}
                >
                  <rect
                    x={r.x + 0.5}
                    y={r.y + 0.5}
                    width={Math.max(1, r.w - 1)}
                    height={Math.max(1, r.h - 1)}
                    rx={2}
                    fill={isHovered ? r.fillHover : r.fill}
                    stroke={r.stroke}
                    strokeWidth={isHovered ? 1.5 : 0.5}
                    strokeOpacity={isHovered ? 1 : 0.4}
                    style={{ transition: 'fill 0.12s, stroke-width 0.12s' }}
                  />

                  {/* Directory overlay gradient */}
                  {r.node.isDir && r.w > 30 && r.h > 16 && (
                    <rect
                      x={r.x + 0.5} y={r.y + 0.5}
                      width={Math.max(1, r.w - 1)}
                      height={Math.min(18, r.h * 0.35)}
                      rx={2}
                      fill={r.labelBg}
                      fillOpacity={0.7}
                    />
                  )}

                  {/* Label: directory name */}
                  {r.w > 28 && r.h > 14 && (
                    <text
                      x={r.x + 4}
                      y={r.y + 11}
                      fontSize={Math.min(10, Math.max(6, r.w / 10))}
                      fontWeight="700"
                      fill={r.textColor}
                      fillOpacity={0.95}
                      style={{ pointerEvents: 'none', userSelect: 'none' }}
                    >
                      {r.node.name.length > Math.floor(r.w / 7) ? r.node.name.slice(0, Math.floor(r.w / 7)) + '…' : r.node.name}
                    </text>
                  )}

                  {/* Size label */}
                  {r.w > 42 && r.h > 24 && (
                    <text
                      x={r.x + 4}
                      y={r.y + 21}
                      fontSize={Math.min(8, Math.max(5.5, r.w / 14))}
                      fill={r.textColor}
                      fillOpacity={0.6}
                      style={{ pointerEvents: 'none', userSelect: 'none' }}
                    >
                      {formatSize(r.node.value)}
                    </text>
                  )}

                  {/* Hover ring */}
                  {isHovered && (
                    <rect
                      x={r.x + 0.5} y={r.y + 0.5}
                      width={Math.max(1, r.w - 1)}
                      height={Math.max(1, r.h - 1)}
                      rx={2}
                      fill="none"
                      stroke="white"
                      strokeWidth={1}
                      strokeOpacity={0.25}
                      style={{ pointerEvents: 'none' }}
                    />
                  )}
                </g>
              );
            })}
          </svg>

          {/* Hover tooltip */}
          {hoveredRect && (
            <div className="absolute top-3 left-3 bg-slate-900/95 backdrop-blur-sm border border-slate-700 rounded-xl px-4 py-3 shadow-2xl pointer-events-none max-w-xs space-y-1.5">
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: hoveredRect.fill, border: `1px solid ${hoveredRect.stroke}` }} />
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                  {hoveredRect.node.isDir ? 'Directory' : (EXT_PALETTE[hoveredRect.node.ext || getExt(hoveredRect.node.name)]?.name || 'File')}
                </span>
              </div>
              <p className="text-slate-100 text-xs font-semibold break-all leading-snug">{hoveredRect.node.path || 'Root'}</p>
              <div className="flex gap-3 pt-0.5">
                <span className="flex items-center gap-1 text-[10px] text-slate-400">
                  <HardDrive className="h-3 w-3" />
                  {formatSize(hoveredRect.node.value)}
                </span>
                {hoveredRect.node.isDir && (
                  <span className="text-[10px] text-indigo-400 font-semibold">Click to zoom in →</span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="w-full lg:w-56 border-t lg:border-t-0 lg:border-l border-slate-800 bg-slate-900/50 flex flex-col">
          {/* Stats */}
          <div className="px-4 py-3 border-b border-slate-800 space-y-2">
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Current View</p>
            <div className="space-y-1.5">
              {[
                { icon: <FolderOpen className="h-3 w-3" />, label: 'Path', val: activeNode.path || (inventory.repo_name || 'Root') },
                { icon: <HardDrive className="h-3 w-3" />, label: 'Size', val: formatSize(activeNode.value) },
                { icon: <FileText className="h-3 w-3" />, label: 'Files', val: String(activeNode.children?.filter(c => !c.isDir).length || 0) },
                { icon: <Code2 className="h-3 w-3" />, label: 'Dirs', val: String(activeNode.children?.filter(c => c.isDir).length || 0) },
              ].map(s => (
                <div key={s.label} className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1 text-[10px] text-slate-500">{s.icon}{s.label}</span>
                  <span className="text-[10px] font-bold text-slate-200 truncate max-w-[90px] text-right">{s.val}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Color Legend */}
          <div className="px-4 py-3 flex-1 overflow-y-auto">
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2.5">
              Color Legend
              {highlightExt && (
                <button onClick={() => setHighlightExt(null)} className="ml-2 text-indigo-400 normal-case font-normal hover:text-indigo-300">
                  clear
                </button>
              )}
            </p>
            <div className="space-y-1.5">
              {legendExts.map(([ext, count]) => (
                <button
                  key={ext}
                  onClick={() => setHighlightExt(highlightExt === ext ? null : ext)}
                  className={`flex items-center gap-1.5 w-full text-left rounded px-1 py-0.5 transition-colors ${highlightExt === ext ? 'bg-slate-700/60' : 'hover:bg-slate-800/60'}`}
                >
                  <div
                    className="w-2.5 h-2.5 rounded-sm shrink-0"
                    style={{ background: (EXT_PALETTE[ext] || UNKNOWN_PALETTE).fill, border: `1px solid ${(EXT_PALETTE[ext] || UNKNOWN_PALETTE).stroke}` }}
                  />
                  <span className="text-[10px] text-slate-300 font-medium flex-1">
                    {(EXT_PALETTE[ext] || UNKNOWN_PALETTE).name}
                  </span>
                  <span className="text-[10px] text-slate-500">{count}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Tip */}
          <div className="px-4 py-3 border-t border-slate-800">
            <div className="flex items-start gap-1.5 text-[10px] text-slate-500">
              <Info className="h-3 w-3 mt-0.5 text-indigo-500/60 shrink-0" />
              <span>Click legend to highlight · Click dir blocks to zoom</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
