import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import type {
  GeneratedFile,
  GenerateStatusResponse,
  FileContentResponse,
} from '../types/project';
import {
  FolderCode,
  Download,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Copy,
  Check,
  FileText,
  Search,
  Code2,
  Layers,
  Sparkles,
} from 'lucide-react';

interface ProjectWorkspaceProps {
  projectId: string;
  projectName: string;
}

export const ProjectWorkspace: React.FC<ProjectWorkspaceProps> = ({
  projectId,
  projectName,
}) => {
  const [status, setStatus] = useState<GenerateStatusResponse | null>(null);
  const [files, setFiles] = useState<GeneratedFile[]>([]);
  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<FileContentResponse | null>(null);
  const [isLoadingContent, setIsLoadingContent] = useState(false);

  const [templateType, setTemplateType] = useState<'fastapi' | 'react' | 'fullstack'>('fullstack');
  const [forceRegenerate, setForceRegenerate] = useState(false);
  const [isStartingGeneration, setIsStartingGeneration] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [copied, setCopied] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Fetch status and files
  const loadWorkspace = useCallback(async () => {
    try {
      const [statusRes, filesRes] = await Promise.allSettled([
        api.getCodeGenerationStatus(projectId),
        api.getGeneratedFiles(projectId),
      ]);

      if (statusRes.status === 'fulfilled') {
        setStatus(statusRes.value);
        if (statusRes.value.template_type) {
          setTemplateType(statusRes.value.template_type as 'fastapi' | 'react' | 'fullstack');
        }
      }

      if (filesRes.status === 'fulfilled') {
        setFiles(filesRes.value);
        // Default select the first file or an entrypoint if none selected
        if (filesRes.value.length > 0 && !selectedFilePath) {
          const entry = filesRes.value.find((f) => f.file_path.includes('main.') || f.file_path.includes('App.'));
          setSelectedFilePath(entry ? entry.file_path : filesRes.value[0].file_path);
        }
      }
    } catch (err) {
      console.error('Error loading workspace:', err);
    }
  }, [projectId, selectedFilePath]);

  // Initial load
  useEffect(() => {
    loadWorkspace();
  }, [loadWorkspace]);

  // Polling during generation
  useEffect(() => {
    if (status?.status === 'generating' || status?.status === 'pending') {
      const timer = setInterval(() => {
        loadWorkspace();
      }, 2000);
      return () => clearInterval(timer);
    }
  }, [status?.status, loadWorkspace]);

  // Load content whenever selected file changes
  useEffect(() => {
    if (!selectedFilePath) {
      setFileContent(null);
      return;
    }

    let isCurrent = true;
    setIsLoadingContent(true);
    api
      .getFileContent(projectId, selectedFilePath)
      .then((content) => {
        if (isCurrent) setFileContent(content);
      })
      .catch((err) => {
        if (isCurrent) {
          console.error('Failed to load file content:', err);
          setFileContent(null);
        }
      })
      .finally(() => {
        if (isCurrent) setIsLoadingContent(false);
      });

    return () => {
      isCurrent = false;
    };
  }, [projectId, selectedFilePath]);

  // Start or retry code generation
  const handleStartGeneration = async () => {
    setIsStartingGeneration(true);
    setErrorMessage(null);
    try {
      const res = await api.startCodeGeneration(projectId, {
        template_type: templateType,
        force_regenerate: forceRegenerate,
      });
      setStatus(res);
      await loadWorkspace();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to start code generation.';
      setErrorMessage(msg);
    } finally {
      setIsStartingGeneration(false);
    }
  };

  const handleCopyCode = () => {
    if (!fileContent?.content) return;
    navigator.clipboard.writeText(fileContent.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadZip = () => {
    window.location.href = api.getProjectDownloadUrl(projectId);
  };

  const filteredFiles = files.filter((f) =>
    f.file_path.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    return `${(bytes / 1024).toFixed(1)} KB`;
  };

  const isGenerating = status?.status === 'generating' || status?.status === 'pending';

  return (
    <div className="space-y-4">
      {/* Workspace Control Bar */}
      <div className="p-4 rounded-xl bg-[#070b14] border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <FolderCode className="w-5 h-5 text-emerald-400" />
            <h3 className="text-sm font-semibold text-slate-100 font-mono">
              PROJECT WORKSPACE
            </h3>
          </div>

          {/* Status Badge */}
          {status && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium border">
              {status.status === 'completed' && (
                <span className="flex items-center gap-1 text-emerald-400 bg-emerald-950/40 border-emerald-500/30 px-2 py-0.5 rounded-full">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Completed ({files.length} files)
                </span>
              )}
              {isGenerating && (
                <span className="flex items-center gap-1 text-cyan-400 bg-cyan-950/40 border-cyan-500/30 px-2 py-0.5 rounded-full animate-pulse">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Generating ({status.generated_files_count}/{status.total_files || '?'})
                </span>
              )}
              {status.status === 'failed' && (
                <span className="flex items-center gap-1 text-rose-400 bg-rose-950/40 border-rose-500/30 px-2 py-0.5 rounded-full">
                  <AlertCircle className="w-3.5 h-3.5" />
                  Generation Failed
                </span>
              )}
            </div>
          )}
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Template Selector */}
          {!isGenerating && (
            <select
              value={templateType}
              onChange={(e) => setTemplateType(e.target.value as 'fastapi' | 'react' | 'fullstack')}
              className="px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-300 font-mono focus:outline-none focus:border-emerald-500"
            >
              <option value="fullstack">Fullstack (FastAPI + React)</option>
              <option value="fastapi">FastAPI Backend</option>
              <option value="react">React + Vite Frontend</option>
            </select>
          )}

          {/* Force Regenerate Checkbox */}
          {!isGenerating && files.length > 0 && (
            <label className="flex items-center gap-1.5 text-xs text-slate-400 select-none cursor-pointer">
              <input
                type="checkbox"
                checked={forceRegenerate}
                onChange={(e) => setForceRegenerate(e.target.checked)}
                className="rounded bg-slate-900 border-slate-700 text-emerald-500 focus:ring-0 focus:ring-offset-0 cursor-pointer"
              />
              <span>Overwrite edits</span>
            </label>
          )}

          {/* Generate / Regenerate Button */}
          <button
            onClick={handleStartGeneration}
            disabled={isGenerating || isStartingGeneration}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 disabled:bg-slate-800 disabled:text-slate-500 text-slate-950 text-xs font-semibold font-mono transition-colors cursor-pointer"
          >
            {isGenerating ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Generating...
              </>
            ) : files.length > 0 ? (
              <>
                <RotateCcw className="w-3.5 h-3.5" />
                Regenerate
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5" />
                Generate Code
              </>
            )}
          </button>

          {/* Download ZIP Button */}
          <button
            onClick={handleDownloadZip}
            disabled={files.length === 0}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 text-xs font-medium font-mono transition-colors cursor-pointer"
            title="Download complete project workspace as ZIP"
          >
            <Download className="w-3.5 h-3.5 text-emerald-400" />
            <span>Download ZIP</span>
          </button>
        </div>
      </div>

      {/* Progress Bar during generation */}
      {isGenerating && status && (
        <div className="p-3 rounded-lg bg-[#070b14] border border-cyan-900/40 space-y-1.5">
          <div className="flex justify-between text-xs font-mono text-cyan-300">
            <span>Generating files into dedicated workspace...</span>
            <span>
              {status.generated_files_count} / {status.total_files} files ({status.percent_complete}%)
            </span>
          </div>
          <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden">
            <div
              className="bg-gradient-to-r from-emerald-500 to-cyan-500 h-full transition-all duration-300"
              style={{ width: `${Math.max(status.percent_complete, 5)}%` }}
            />
          </div>
        </div>
      )}

      {/* Error Alert with Retry */}
      {(errorMessage || (status?.status === 'failed' && status.error_message)) && (
        <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-500/30 flex items-start justify-between gap-3 text-xs text-rose-200">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Code Generation Issue</p>
              <p className="text-rose-300/90 mt-0.5">
                {errorMessage || status?.error_message}
              </p>
            </div>
          </div>
          <button
            onClick={handleStartGeneration}
            className="px-2.5 py-1 rounded bg-rose-900/60 hover:bg-rose-800 text-rose-100 font-mono text-xs cursor-pointer shrink-0"
          >
            Retry
          </button>
        </div>
      )}

      {/* Main Workspace Explorer & Viewer */}
      {files.length === 0 && !isGenerating ? (
        <div className="p-10 rounded-xl bg-[#070b14] border border-slate-800 text-center space-y-3">
          <div className="w-12 h-12 rounded-xl bg-slate-900 border border-slate-800 mx-auto flex items-center justify-center text-emerald-400">
            <Layers className="w-6 h-6" />
          </div>
          <h4 className="text-base font-semibold text-slate-200">
            Ready to Generate Project Files
          </h4>
          <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
            CodePilot will plan a complete file manifest and generate modular,
            production-ready source code for <span className="text-emerald-400 font-mono">{projectName}</span>.
          </p>
          <div className="pt-2">
            <button
              onClick={handleStartGeneration}
              disabled={isStartingGeneration}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold font-mono text-xs transition-colors cursor-pointer"
            >
              <Sparkles className="w-4 h-4" />
              Start Code Generation ({templateType.toUpperCase()})
            </button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3 min-h-[440px]">
          {/* File Explorer (Left Pane) */}
          <div className="md:col-span-4 rounded-xl bg-[#070b14] border border-slate-800 flex flex-col overflow-hidden">
            <div className="p-3 border-b border-slate-800/80 bg-[#090e17]">
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-500" />
                <input
                  type="text"
                  placeholder="Filter files..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-700/60 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500 font-mono"
                />
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {filteredFiles.map((f) => {
                const isSelected = f.file_path === selectedFilePath;
                return (
                  <button
                    key={f.id}
                    onClick={() => setSelectedFilePath(f.file_path)}
                    className={`w-full text-left px-2.5 py-2 rounded-lg text-xs font-mono transition-colors flex items-center justify-between group cursor-pointer ${
                      isSelected
                        ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                        : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate mr-2">
                      <Code2
                        className={`w-3.5 h-3.5 shrink-0 ${
                          isSelected ? 'text-emerald-400' : 'text-slate-500 group-hover:text-slate-300'
                        }`}
                      />
                      <span className="truncate">{f.file_path}</span>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0 text-[10px] text-slate-500">
                      {f.file_path.includes('main.') && (
                        <span className="px-1 py-0.2 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/40 text-[9px]">
                          entry
                        </span>
                      )}
                      <span>{formatBytes(f.file_size_bytes)}</span>
                    </div>
                  </button>
                );
              })}

              {filteredFiles.length === 0 && (
                <div className="p-4 text-center text-xs text-slate-500 font-mono">
                  No files match search.
                </div>
              )}
            </div>

            <div className="p-2.5 border-t border-slate-800/80 bg-[#090e17] text-[11px] font-mono text-slate-500 flex justify-between">
              <span>{files.length} project files</span>
              <span>Template: {status?.template_type || templateType}</span>
            </div>
          </div>

          {/* Read-Only Source Code Viewer (Right Pane) */}
          <div className="md:col-span-8 rounded-xl bg-[#070b14] border border-slate-800 flex flex-col overflow-hidden">
            {selectedFilePath ? (
              <>
                {/* File Header */}
                <div className="p-3 border-b border-slate-800/80 bg-[#090e17] flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2 truncate">
                    <FileText className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span className="text-xs font-mono font-semibold text-slate-200 truncate">
                      {selectedFilePath}
                    </span>
                    {fileContent && (
                      <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] font-mono text-slate-400 uppercase">
                        {fileContent.language}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {fileContent && (
                      <span className="text-[11px] font-mono text-slate-500">
                        {formatBytes(fileContent.size_bytes)}
                      </span>
                    )}
                    <button
                      onClick={handleCopyCode}
                      disabled={!fileContent?.content}
                      className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono transition-colors cursor-pointer"
                    >
                      {copied ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                          <span className="text-emerald-400">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          <span>Copy</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* Purpose Banner if present */}
                {(() => {
                  const currentFileRec = files.find((f) => f.file_path === selectedFilePath);
                  if (currentFileRec?.purpose) {
                    return (
                      <div className="px-3 py-1.5 bg-slate-900/60 border-b border-slate-800/50 text-[11px] text-slate-400 font-sans">
                        <span className="text-emerald-400 font-mono">Purpose:</span> {currentFileRec.purpose}
                      </div>
                    );
                  }
                  return null;
                })()}

                {/* Code Content View */}
                <div className="flex-1 p-3 overflow-auto bg-[#05080f] font-mono text-xs select-text">
                  {isLoadingContent ? (
                    <div className="h-64 flex items-center justify-center text-slate-500 gap-2">
                      <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
                      <span>Loading file source...</span>
                    </div>
                  ) : fileContent?.content ? (
                    <div className="table w-full">
                      {fileContent.content.split('\n').map((line, idx) => (
                        <div key={idx} className="table-row hover:bg-slate-900/40">
                          <span className="table-cell select-none pr-4 text-right text-slate-600 font-mono text-[11px] w-8">
                            {idx + 1}
                          </span>
                          <span className="table-cell whitespace-pre text-slate-200">
                            {line || ' '}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-8 text-center text-slate-500">
                      File is empty or could not be loaded.
                    </div>
                  )}
                </div>

                {/* Safety & Execution Disclaimer */}
                <div className="p-2 border-t border-slate-800/80 bg-[#090e17] text-[10px] font-mono text-slate-500 text-right">
                  Read-only source viewer • Generated code is never executed automatically
                </div>
              </>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-500">
                <Code2 className="w-8 h-8 mb-2 text-slate-600" />
                <p className="text-xs font-mono">Select a file from the explorer to view source code.</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
