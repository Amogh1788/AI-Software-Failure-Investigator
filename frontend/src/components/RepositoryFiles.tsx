import React, { useState, useMemo } from 'react';
import {
  Folder,
  FolderOpen,
  FileCode,
  FileText,
  ChevronRight,
  ChevronDown,
  Search,
  CheckCircle2,
  ShieldCheck,
  Hash,
  Binary,
} from 'lucide-react';
import type { RepositoryFile, FileTreeNode } from '../types';

interface RepositoryFilesProps {
  files: RepositoryFile[];
}

/**
 * Builds a hierarchical tree from a flat list of file paths.
 */
function buildFileTree(files: RepositoryFile[]): FileTreeNode[] {
  const root: FileTreeNode = { name: '', path: '', isDirectory: true, children: [] };

  for (const file of files) {
    const parts = file.path.split('/');
    let current = root;

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isFile = i === parts.length - 1;
      const currentPath = parts.slice(0, i + 1).join('/');

      if (!current.children) {
        current.children = [];
      }

      let nextNode = current.children.find((c) => c.name === part);

      if (!nextNode) {
        nextNode = {
          name: part,
          path: currentPath,
          isDirectory: !isFile,
          children: isFile ? undefined : [],
          file: isFile ? file : undefined,
        };
        current.children.push(nextNode);
      }

      current = nextNode;
    }
  }

  // Sort folders first, then files alphabetically
  function sortNodes(nodes?: FileTreeNode[]) {
    if (!nodes) return;
    nodes.sort((a, b) => {
      if (a.isDirectory && !b.isDirectory) return -1;
      if (!a.isDirectory && b.isDirectory) return 1;
      return a.name.localeCompare(b.name);
    });
    for (const node of nodes) {
      if (node.children) sortNodes(node.children);
    }
  }

  sortNodes(root.children);
  return root.children || [];
}

interface TreeNodeItemProps {
  node: FileTreeNode;
  depth: number;
  selectedPath: string | null;
  onSelectFile: (file: RepositoryFile) => void;
  expandedDirs: Set<string>;
  toggleDir: (path: string) => void;
}

const TreeNodeItem: React.FC<TreeNodeItemProps> = ({
  node,
  depth,
  selectedPath,
  onSelectFile,
  expandedDirs,
  toggleDir,
}) => {
  if (node.isDirectory) {
    const isExpanded = expandedDirs.has(node.path);
    return (
      <div>
        <button
          onClick={() => toggleDir(node.path)}
          style={{ paddingLeft: `${depth * 14 + 6}px` }}
          className="w-full text-left flex items-center space-x-1.5 py-1 px-2 hover:bg-slate-800/60 rounded text-xs font-mono text-slate-300 transition-colors cursor-pointer"
        >
          {isExpanded ? (
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          )}
          {isExpanded ? (
            <FolderOpen className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
          ) : (
            <Folder className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
          )}
          <span className="truncate">{node.name}</span>
        </button>

        {isExpanded && node.children && (
          <div>
            {node.children.map((child) => (
              <TreeNodeItem
                key={child.path}
                node={child}
                depth={depth + 1}
                selectedPath={selectedPath}
                onSelectFile={onSelectFile}
                expandedDirs={expandedDirs}
                toggleDir={toggleDir}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  const isSelected = selectedPath === node.path;
  const isSource = node.file?.is_source_file;

  return (
    <button
      onClick={() => node.file && onSelectFile(node.file)}
      style={{ paddingLeft: `${depth * 14 + 18}px` }}
      className={`w-full text-left flex items-center space-x-2 py-1 px-2 rounded text-xs font-mono transition-colors cursor-pointer truncate ${
        isSelected
          ? 'bg-indigo-950/80 text-indigo-200 border-l-2 border-indigo-500'
          : 'text-slate-300 hover:bg-slate-800/50'
      }`}
    >
      {isSource ? (
        <FileCode className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
      ) : (
        <FileText className="w-3.5 h-3.5 text-slate-500 shrink-0" />
      )}
      <span className="truncate">{node.name}</span>
    </button>
  );
};

export const RepositoryFiles: React.FC<RepositoryFilesProps> = ({ files }) => {
  const [search, setSearch] = useState('');
  const [selectedFile, setSelectedFile] = useState<RepositoryFile | null>(files[0] || null);

  // Initialize expanded directories with first-level folders
  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(() => {
    const initial = new Set<string>();
    for (const f of files) {
      const parts = f.path.split('/');
      if (parts.length > 1) {
        initial.add(parts[0]);
      }
    }
    return initial;
  });

  const toggleDir = (dirPath: string) => {
    setExpandedDirs((prev) => {
      const next = new Set(prev);
      if (next.has(dirPath)) {
        next.delete(dirPath);
      } else {
        next.add(dirPath);
      }
      return next;
    });
  };

  const filteredFiles = useMemo(() => {
    if (!search.trim()) return files;
    const q = search.toLowerCase();
    return files.filter((f) => f.path.toLowerCase().includes(q));
  }, [files, search]);

  const tree = useMemo(() => buildFileTree(filteredFiles), [filteredFiles]);

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-5 space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800/80">
        <div>
          <h3 className="text-sm font-semibold tracking-wide text-slate-200 uppercase font-mono">
            Repository File Tree ({files.length})
          </h3>
          <p className="text-xs text-slate-400">
            Static structure inspection. Select a file to inspect metadata.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2" />
            <input
              type="text"
              placeholder="Search file path..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-slate-900/90 border border-slate-800 focus:border-indigo-500 rounded pl-8 pr-2.5 py-1 text-xs text-slate-200 font-mono placeholder:text-slate-500 outline-none w-48 sm:w-60"
            />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left column: Hierarchical File Tree */}
        <div className="lg:col-span-5 bg-slate-900/60 border border-slate-800/80 rounded-md p-2 h-96 overflow-y-auto font-mono text-xs">
          {tree.length === 0 ? (
            <div className="text-center py-8 text-slate-500">No matching files found.</div>
          ) : (
            tree.map((node) => (
              <TreeNodeItem
                key={node.path}
                node={node}
                depth={0}
                selectedPath={selectedFile?.path || null}
                onSelectFile={setSelectedFile}
                expandedDirs={expandedDirs}
                toggleDir={toggleDir}
              />
            ))
          )}
        </div>

        {/* Right column: Selected File Metadata Inspector */}
        <div className="lg:col-span-7 bg-slate-900/60 border border-slate-800/80 rounded-md p-4 flex flex-col justify-between">
          {selectedFile ? (
            <div className="space-y-4">
              <div className="flex items-start justify-between gap-2 border-b border-slate-800/80 pb-3">
                <div className="min-w-0">
                  <div className="flex items-center space-x-2">
                    <FileCode className="w-4 h-4 text-indigo-400 shrink-0" />
                    <h4 className="text-sm font-semibold font-mono text-slate-200 truncate" title={selectedFile.path}>
                      {selectedFile.path}
                    </h4>
                  </div>
                  <p className="text-xs text-slate-400 mt-1 font-mono">
                    Extension: <span className="text-slate-300">{selectedFile.extension || 'None'}</span>
                  </p>
                </div>

                {selectedFile.is_source_file ? (
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono bg-indigo-950/80 text-indigo-300 border border-indigo-800/60 whitespace-nowrap shrink-0">
                    <CheckCircle2 className="w-3 h-3 mr-1" />
                    Source File
                  </span>
                ) : (
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800 text-slate-400 border border-slate-700 whitespace-nowrap shrink-0">
                    Resource / Data
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 font-mono text-xs">
                <div className="bg-slate-900/80 border border-slate-800 rounded p-3 space-y-1">
                  <span className="text-slate-500 uppercase text-[10px]">Detected Language</span>
                  <div className="text-sm font-semibold text-slate-200">
                    {selectedFile.language || 'Unknown'}
                  </div>
                </div>

                <div className="bg-slate-900/80 border border-slate-800 rounded p-3 space-y-1">
                  <span className="text-slate-500 uppercase text-[10px]">File Size</span>
                  <div className="text-sm font-semibold text-slate-200 flex items-center space-x-1">
                    <Binary className="w-3.5 h-3.5 text-indigo-400" />
                    <span>{formatFileSize(selectedFile.file_size)}</span>
                  </div>
                </div>

                <div className="bg-slate-900/80 border border-slate-800 rounded p-3 space-y-1">
                  <span className="text-slate-500 uppercase text-[10px]">Lines of Code</span>
                  <div className="text-sm font-semibold text-slate-200 flex items-center space-x-1">
                    <Hash className="w-3.5 h-3.5 text-indigo-400" />
                    <span>{selectedFile.lines_of_code.toLocaleString()}</span>
                  </div>
                </div>
              </div>

              <div className="bg-slate-950/60 border border-indigo-950/80 rounded p-3 text-xs text-slate-400 space-y-1">
                <div className="flex items-center space-x-1.5 text-indigo-400 font-mono font-medium">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>Static Analysis Security Policy</span>
                </div>
                <p className="leading-relaxed text-[11px]">
                  Repository files are analyzed purely statically. Source code execution, build commands, and script evaluation are strictly disabled.
                </p>
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-slate-500 text-xs font-mono">
              Select a file from the tree to view its static metadata.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
