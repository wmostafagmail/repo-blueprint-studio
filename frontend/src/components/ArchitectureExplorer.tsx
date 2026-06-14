import React, { useMemo, useState } from 'react';
import {
  Folder, FolderOpen, File, ChevronRight, Home,
  Code2, FileText, Settings, Database, Globe, Box,
  ArrowLeft, BarChart2, Hash, HardDrive, Layers
} from 'lucide-react';

// ── Types ────────────────────────────────────────────────────────────────────

interface InventoryFile {
  path: string;
  extension: string;
  size_bytes: number;
  is_source_like?: boolean;
  is_manifest_like?: boolean;
}

interface TreeNode {
  name: string;
  fullPath: string;
  isDir: boolean;
  children: Record<string, TreeNode>;
  files: InventoryFile[];           // direct files at this level
  totalFiles: number;               // recursive count
  totalSize: number;                // recursive bytes
  topExtensions: [string, number][]; // [ext, count] sorted
}

interface ArchitectureExplorerProps {
  inventory: {
    repo_name?: string;
    files: InventoryFile[];
    summary?: { extension_counts?: Record<string, number> };
  };
}

// ── Helpers ──────────────────────────────────────────────────────────────────

const EXT_LABELS: Record<string, string> = {
  '.py': 'Python', '.ts': 'TypeScript', '.tsx': 'TSX', '.js': 'JavaScript',
  '.jsx': 'JSX', '.go': 'Go', '.rs': 'Rust', '.java': 'Java', '.kt': 'Kotlin',
  '.swift': 'Swift', '.rb': 'Ruby', '.cs': 'C#', '.cpp': 'C++', '.c': 'C',
  '.md': 'Markdown', '.json': 'JSON', '.yaml': 'YAML', '.yml': 'YAML',
  '.toml': 'TOML', '.sql': 'SQL', '.html': 'HTML', '.css': 'CSS',
  '.sh': 'Shell', '.php': 'PHP', '.scala': 'Scala', '.ex': 'Elixir',
  '.jl': 'Julia', '.r': 'R', '.m': 'MATLAB', '.lua': 'Lua', '.dart': 'Dart',
};

const EXT_COLORS: Record<string, string> = {
  '.py': 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  '.ts': 'bg-sky-500/20 text-sky-300 border-sky-500/30',
  '.tsx': 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
  '.js': 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
  '.go': 'bg-teal-500/20 text-teal-300 border-teal-500/30',
  '.rs': 'bg-orange-500/20 text-orange-300 border-orange-500/30',
  '.java': 'bg-red-500/20 text-red-300 border-red-500/30',
  '.kt': 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  '.rb': 'bg-rose-500/20 text-rose-300 border-rose-500/30',
  '.cs': 'bg-violet-500/20 text-violet-300 border-violet-500/30',
  '.md': 'bg-slate-500/20 text-slate-300 border-slate-500/30',
  '.json': 'bg-green-500/20 text-green-300 border-green-500/30',
  '.sql': 'bg-amber-500/20 text-amber-300 border-amber-500/30',
  '.html': 'bg-orange-500/20 text-orange-300 border-orange-500/30',
  '.css': 'bg-pink-500/20 text-pink-300 border-pink-500/30',
};

const getExtColor = (ext: string) =>
  EXT_COLORS[ext] || 'bg-slate-600/20 text-slate-400 border-slate-600/30';

const getExtLabel = (ext: string) => EXT_LABELS[ext] || ext.replace('.', '').toUpperCase() || '—';

const formatSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const FOLDER_ICONS: Record<string, React.ReactNode> = {
  src: <Code2 className="h-5 w-5" />,
  lib: <Layers className="h-5 w-5" />,
  app: <Globe className="h-5 w-5" />,
  api: <Globe className="h-5 w-5" />,
  db: <Database className="h-5 w-5" />,
  database: <Database className="h-5 w-5" />,
  config: <Settings className="h-5 w-5" />,
  configs: <Settings className="h-5 w-5" />,
  test: <Box className="h-5 w-5" />,
  tests: <Box className="h-5 w-5" />,
  docs: <FileText className="h-5 w-5" />,
  components: <Layers className="h-5 w-5" />,
  models: <Database className="h-5 w-5" />,
  services: <Globe className="h-5 w-5" />,
  utils: <Hash className="h-5 w-5" />,
  scripts: <Code2 className="h-5 w-5" />,
};

const getFolderIcon = (name: string) =>
  FOLDER_ICONS[name.toLowerCase()] || <Folder className="h-5 w-5" />;

// ── Tree Builder ─────────────────────────────────────────────────────────────

function buildTree(files: InventoryFile[]): TreeNode {
  const root: TreeNode = {
    name: 'root', fullPath: '', isDir: true,
    children: {}, files: [], totalFiles: 0, totalSize: 0, topExtensions: [],
  };

  for (const file of files) {
    const parts = file.path.split('/');
    let node = root;
    // Walk/create the path
    for (let i = 0; i < parts.length - 1; i++) {
      const part = parts[i];
      if (!node.children[part]) {
        node.children[part] = {
          name: part,
          fullPath: parts.slice(0, i + 1).join('/'),
          isDir: true,
          children: {}, files: [], totalFiles: 0, totalSize: 0, topExtensions: [],
        };
      }
      node = node.children[part];
    }
    // Add the file to its parent
    node.files.push(file);
  }

  // Compute recursive stats bottom-up
  const computeStats = (node: TreeNode) => {
    let total = node.files.length;
    let size = node.files.reduce((s, f) => s + f.size_bytes, 0);
    const extCounts: Record<string, number> = {};
    for (const f of node.files) {
      if (f.extension) extCounts[f.extension] = (extCounts[f.extension] || 0) + 1;
    }
    for (const child of Object.values(node.children)) {
      computeStats(child);
      total += child.totalFiles;
      size += child.totalSize;
      for (const [ext, count] of child.topExtensions) {
        extCounts[ext] = (extCounts[ext] || 0) + count;
      }
    }
    node.totalFiles = total;
    node.totalSize = size;
    node.topExtensions = Object.entries(extCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 4);
  };

  computeStats(root);
  return root;
}

function getNodeAtPath(root: TreeNode, path: string[]): TreeNode {
  let node = root;
  for (const part of path) {
    if (node.children[part]) node = node.children[part];
    else break;
  }
  return node;
}

// ── Node Card ────────────────────────────────────────────────────────────────

interface NodeCardProps {
  node: TreeNode;
  onClick?: () => void;
  isFile?: boolean;
}

const NodeCard: React.FC<NodeCardProps> = ({ node, onClick, isFile }) => {
  const canDrillDown = node.isDir && (Object.keys(node.children).length > 0 || node.files.length > 0);

  return (
    <button
      onClick={onClick}
      disabled={!canDrillDown && !isFile}
      className={`
        group relative w-full text-left rounded-xl border transition-all duration-200
        ${canDrillDown
          ? 'bg-slate-900 border-slate-700 hover:border-indigo-500 hover:bg-slate-800/80 hover:shadow-lg hover:shadow-indigo-900/20 cursor-pointer'
          : 'bg-slate-900/50 border-slate-800 cursor-default opacity-70'}
        p-4 flex flex-col gap-3
      `}
    >
      {/* Icon + Name row */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className={`shrink-0 p-1.5 rounded-lg ${canDrillDown ? 'bg-indigo-500/10 text-indigo-400 group-hover:bg-indigo-500/20' : 'bg-slate-700/50 text-slate-500'}`}>
            {node.isDir ? getFolderIcon(node.name) : <File className="h-5 w-5" />}
          </div>
          <span className="font-semibold text-sm text-slate-100 truncate leading-tight">
            {node.name}
          </span>
        </div>
        {canDrillDown && (
          <ChevronRight className="h-4 w-4 text-slate-500 group-hover:text-indigo-400 shrink-0 mt-0.5 transition-colors" />
        )}
      </div>

      {/* Stats row */}
      <div className="flex items-center gap-3 text-xs text-slate-400">
        {node.isDir && (
          <>
            <span className="flex items-center gap-1">
              <BarChart2 className="h-3 w-3" />
              {node.totalFiles} file{node.totalFiles !== 1 ? 's' : ''}
            </span>
            {Object.keys(node.children).length > 0 && (
              <span className="flex items-center gap-1">
                <FolderOpen className="h-3 w-3" />
                {Object.keys(node.children).length} dir{Object.keys(node.children).length !== 1 ? 's' : ''}
              </span>
            )}
          </>
        )}
        <span className="flex items-center gap-1 ml-auto">
          <HardDrive className="h-3 w-3" />
          {formatSize(node.totalSize)}
        </span>
      </div>

      {/* Extension pills */}
      {node.topExtensions.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {node.topExtensions.slice(0, 3).map(([ext, count]) => (
            <span
              key={ext}
              className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[10px] font-semibold ${getExtColor(ext)}`}
            >
              {getExtLabel(ext)}
              <span className="opacity-70">·{count}</span>
            </span>
          ))}
        </div>
      )}

      {/* Drill-in indicator */}
      {canDrillDown && (
        <div className="absolute inset-0 rounded-xl ring-1 ring-inset ring-indigo-500/0 group-hover:ring-indigo-500/40 transition-all pointer-events-none" />
      )}
    </button>
  );
};

// ── File Row ─────────────────────────────────────────────────────────────────

const FileRow: React.FC<{ file: InventoryFile }> = ({ file }) => {
  const name = file.path.split('/').pop() || file.path;
  return (
    <div className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-800/50 transition-colors group">
      <div className="p-1 rounded bg-slate-800 text-slate-500">
        <File className="h-3.5 w-3.5" />
      </div>
      <span className="text-sm text-slate-300 truncate flex-1">{name}</span>
      {file.extension && (
        <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border shrink-0 ${getExtColor(file.extension)}`}>
          {getExtLabel(file.extension)}
        </span>
      )}
      <span className="text-[11px] text-slate-500 shrink-0 w-16 text-right">
        {formatSize(file.size_bytes)}
      </span>
    </div>
  );
};

// ── Main Component ────────────────────────────────────────────────────────────

export const ArchitectureExplorer: React.FC<ArchitectureExplorerProps> = ({ inventory }) => {
  const [path, setPath] = useState<string[]>([]);
  const [animDir, setAnimDir] = useState<'in' | 'out'>('in');
  const [animKey, setAnimKey] = useState(0);

  const tree = useMemo(() => buildTree(inventory.files || []), [inventory.files]);
  const currentNode = useMemo(() => getNodeAtPath(tree, path), [tree, path]);
  const repoName = inventory.repo_name || 'Repository';

  const navigate = (into: string) => {
    setAnimDir('in');
    setAnimKey(k => k + 1);
    setPath(prev => [...prev, into]);
  };

  const navigateTo = (depth: number) => {
    setAnimDir('out');
    setAnimKey(k => k + 1);
    setPath(prev => prev.slice(0, depth));
  };

  const sortedDirs = Object.values(currentNode.children)
    .sort((a, b) => b.totalFiles - a.totalFiles);
  const directFiles = currentNode.files
    .sort((a, b) => b.size_bytes - a.size_bytes);

  return (
    <div className="bg-slate-950 border border-slate-800 rounded-2xl overflow-hidden flex flex-col shadow-2xl" style={{ height: '600px' }}>

      {/* Header */}
      <div className="bg-slate-900 border-b border-slate-800 px-5 py-3 flex items-center gap-3 shrink-0">
        <div className="p-1.5 rounded-lg bg-indigo-500/10">
          <Layers className="h-4 w-4 text-indigo-400" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-slate-100 leading-none">Architecture Explorer</h3>
          <p className="text-[10px] text-slate-500 mt-0.5">Click any component to explore its contents</p>
        </div>

        {/* Stats summary */}
        <div className="ml-auto flex items-center gap-4 text-xs text-slate-400">
          <span className="flex items-center gap-1">
            <BarChart2 className="h-3 w-3 text-indigo-400" />
            {currentNode.totalFiles} files
          </span>
          <span className="flex items-center gap-1">
            <HardDrive className="h-3 w-3 text-indigo-400" />
            {formatSize(currentNode.totalSize)}
          </span>
          <span className="flex items-center gap-1">
            <FolderOpen className="h-3 w-3 text-indigo-400" />
            {Object.keys(currentNode.children).length} dirs
          </span>
        </div>
      </div>

      {/* Breadcrumb */}
      <div className="bg-slate-900/50 border-b border-slate-800/60 px-5 py-2.5 flex items-center gap-1 shrink-0 overflow-x-auto">
        <button
          onClick={() => navigateTo(0)}
          className="flex items-center gap-1.5 text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition-colors shrink-0"
        >
          <Home className="h-3.5 w-3.5" />
          <span>{repoName}</span>
        </button>
        {path.map((segment, idx) => (
          <React.Fragment key={idx}>
            <ChevronRight className="h-3.5 w-3.5 text-slate-600 shrink-0" />
            <button
              onClick={() => navigateTo(idx + 1)}
              className={`text-xs font-semibold shrink-0 transition-colors ${
                idx === path.length - 1
                  ? 'text-slate-200 cursor-default'
                  : 'text-indigo-400 hover:text-indigo-300'
              }`}
            >
              {segment}
            </button>
          </React.Fragment>
        ))}
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto p-5">
        {/* Back button (when drilled in) */}
        {path.length > 0 && (
          <button
            onClick={() => navigateTo(path.length - 1)}
            className="flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-slate-200 mb-4 transition-colors group"
          >
            <ArrowLeft className="h-3.5 w-3.5 group-hover:-translate-x-0.5 transition-transform" />
            Back to {path.length === 1 ? repoName : path[path.length - 2]}
          </button>
        )}

        {/* Subdirectory grid */}
        {sortedDirs.length > 0 && (
          <div>
            {sortedDirs.length > 0 && (
              <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-3">
                Directories ({sortedDirs.length})
              </p>
            )}
            <div
              key={`dirs-${animKey}`}
              className="grid gap-3"
              style={{
                gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
                animation: `${animDir === 'in' ? 'slideInRight' : 'slideInLeft'} 0.22s ease-out`
              }}
            >
              {sortedDirs.map(child => (
                <NodeCard
                  key={child.name}
                  node={child}
                  onClick={() => navigate(child.name)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Divider */}
        {sortedDirs.length > 0 && directFiles.length > 0 && (
          <div className="border-t border-slate-800/60 my-5" />
        )}

        {/* Direct files list */}
        {directFiles.length > 0 && (
          <div>
            <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-3">
              Files ({directFiles.length})
            </p>
            <div
              key={`files-${animKey}`}
              className="flex flex-col gap-0.5 bg-slate-900/40 rounded-xl border border-slate-800/60 p-2"
              style={{ animation: 'fadeIn 0.25s ease-out' }}
            >
              {directFiles.map((file, i) => (
                <FileRow key={i} file={file} />
              ))}
            </div>
          </div>
        )}

        {/* Empty state */}
        {sortedDirs.length === 0 && directFiles.length === 0 && (
          <div className="flex flex-col items-center justify-center h-40 text-slate-500 space-y-2">
            <Folder className="h-8 w-8 opacity-30" />
            <span className="text-sm">Empty directory</span>
          </div>
        )}
      </div>

      {/* CSS animations injected globally once */}
      <style>{`
        @keyframes slideInRight {
          from { opacity: 0; transform: translateX(18px); }
          to   { opacity: 1; transform: translateX(0); }
        }
        @keyframes slideInLeft {
          from { opacity: 0; transform: translateX(-18px); }
          to   { opacity: 1; transform: translateX(0); }
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(6px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
};
