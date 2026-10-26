import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import type { ImportedRepository, RepoChatResponse, RetrievedChunk } from '../types/project';
import {
  GitBranch,
  Plus,
  MessageSquare,
  Send,
  Loader2,
  CheckCircle2,
  AlertCircle,
  FileCode,
  Lock,
  Trash2,
  RotateCw,
  ExternalLink,
  Code2,
  X,
} from 'lucide-react';

const GithubIcon: React.FC<{ className?: string }> = ({ className = 'w-4 h-4' }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
    <path d="M9 18c-4.51 2-5-2-7-2" />
  </svg>
);


export const RepositoryChatPanel: React.FC = () => {
  const [repositories, setRepositories] = useState<ImportedRepository[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string | null>(null);
  const [isLoadingRepos, setIsLoadingRepos] = useState(true);

  // Import Modal state
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [importUrl, setImportUrl] = useState('');
  const [importName, setImportName] = useState('');
  const [importBranch, setImportBranch] = useState('');
  const [importToken, setImportToken] = useState('');
  const [isImporting, setIsImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);

  // Chat state
  const [messages, setMessages] = useState<
    Array<{
      id: string;
      role: 'user' | 'assistant';
      content: string;
      sources?: RetrievedChunk[];
      evidence_sufficient?: boolean;
    }>
  >([]);
  const [inputQuery, setInputQuery] = useState('');
  const [isQuerying, setIsQuerying] = useState(false);
  const [activeChunkModal, setActiveChunkModal] = useState<RetrievedChunk | null>(null);

  // Load repositories
  const loadRepositories = useCallback(async () => {
    try {
      const data = await api.getRepositories();
      setRepositories(data);
      if (data.length > 0 && !selectedRepoId) {
        setSelectedRepoId(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load repositories:', err);
    } finally {
      setIsLoadingRepos(false);
    }
  }, [selectedRepoId]);

  useEffect(() => {
    loadRepositories();
  }, [loadRepositories]);

  // Periodic polling for repos in progress
  useEffect(() => {
    const activeRepo = repositories.find((r) => r.id === selectedRepoId);
    if (activeRepo && (activeRepo.status === 'importing' || activeRepo.status === 'indexing' || activeRepo.status === 'pending')) {
      const interval = setInterval(async () => {
        try {
          const updated = await api.getRepositoryStatus(activeRepo.id);
          setRepositories((prev) =>
            prev.map((r) => (r.id === updated.id ? { ...r, ...updated } : r))
          );
        } catch (e) {
          console.error('Failed to poll repo status:', e);
        }
      }, 2500);
      return () => clearInterval(interval);
    }
  }, [selectedRepoId, repositories]);

  const selectedRepo = repositories.find((r) => r.id === selectedRepoId);

  // Handle repository import
  const handleImport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!importUrl.trim()) return;

    setIsImporting(true);
    setImportError(null);
    try {
      const created = await api.importRepository({
        repo_url: importUrl.trim(),
        name: importName.trim() || undefined,
        branch: importBranch.trim() || undefined,
        access_token: importToken.trim() || undefined,
      });

      setRepositories((prev) => [created, ...prev.filter((r) => r.id !== created.id)]);
      setSelectedRepoId(created.id);
      setIsImportModalOpen(false);
      setImportUrl('');
      setImportName('');
      setImportBranch('');
      setImportToken('');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Import failed.';
      setImportError(msg);
    } finally {
      setIsImporting(false);
    }
  };

  // Handle Delete
  const handleDeleteRepo = async (repoId: string) => {
    if (!confirm('Are you sure you want to delete this repository and its vector index?')) return;
    try {
      await api.deleteRepository(repoId);
      setRepositories((prev) => prev.filter((r) => r.id !== repoId));
      if (selectedRepoId === repoId) {
        setSelectedRepoId(repositories.find((r) => r.id !== repoId)?.id || null);
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete repository');
    }
  };

  // Handle Re-index
  const handleReindex = async (repoId: string) => {
    try {
      const updated = await api.reindexRepository(repoId);
      setRepositories((prev) =>
        prev.map((r) => (r.id === updated.id ? { ...r, ...updated } : r))
      );
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to reindex');
    }
  };

  // Handle Chat Question
  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputQuery.trim() || !selectedRepoId || isQuerying) return;

    const query = inputQuery.trim();
    setInputQuery('');

    const userMsgId = String(Date.now());
    setMessages((prev) => [
      ...prev,
      { id: userMsgId, role: 'user', content: query },
    ]);

    setIsQuerying(true);
    try {
      const res: RepoChatResponse = await api.chatRepository(selectedRepoId, query);
      setMessages((prev) => [
        ...prev,
        {
          id: String(Date.now() + 1),
          role: 'assistant',
          content: res.answer,
          sources: res.sources,
          evidence_sufficient: res.evidence_sufficient,
        },
      ]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error generating response';
      setMessages((prev) => [
        ...prev,
        {
          id: String(Date.now() + 1),
          role: 'assistant',
          content: `Error contacting repository intelligence: ${msg}`,
          evidence_sufficient: false,
        },
      ]);
    } finally {
      setIsQuerying(false);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="flex flex-col lg:flex-row gap-6 h-[calc(100vh-140px)] min-h-[600px]">
      {/* Left Sidebar: Repository List */}
      <div className="lg:w-80 shrink-0 bg-[#0c1322] border border-slate-800 rounded-xl flex flex-col overflow-hidden">
        <div className="p-4 border-b border-slate-800/80 flex items-center justify-between bg-[#090e17]">
          <div className="flex items-center gap-2">
            <GithubIcon className="w-4 h-4 text-emerald-400" />
            <h3 className="text-xs font-mono font-semibold text-slate-200 uppercase tracking-wider">
              Repositories
            </h3>
          </div>
          <button
            onClick={() => setIsImportModalOpen(true)}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-emerald-500 hover:bg-emerald-600 text-slate-950 text-xs font-mono font-semibold transition-colors cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            Import
          </button>
        </div>

        {/* Repository Items List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {isLoadingRepos ? (
            <div className="p-8 text-center text-slate-500 flex items-center justify-center gap-2 text-xs font-mono">
              <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
              <span>Loading repos...</span>
            </div>
          ) : repositories.length === 0 ? (
            <div className="p-8 text-center text-slate-500 space-y-2">
              <GithubIcon className="w-8 h-8 mx-auto text-slate-600" />
              <p className="text-xs font-mono">No repositories imported yet.</p>
              <button
                onClick={() => setIsImportModalOpen(true)}
                className="text-xs font-mono text-emerald-400 hover:underline cursor-pointer"
              >
                + Import your first GitHub repo
              </button>
            </div>
          ) : (
            repositories.map((repo) => {
              const isSelected = repo.id === selectedRepoId;
              const isReady = repo.status === 'ready';
              const isWorking = repo.status === 'importing' || repo.status === 'indexing' || repo.status === 'pending';
              const isFailed = repo.status === 'failed';

              return (
                <div
                  key={repo.id}
                  onClick={() => setSelectedRepoId(repo.id)}
                  className={`p-3 rounded-lg border text-xs font-mono transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-emerald-500/10 border-emerald-500/40 text-slate-200 shadow-sm'
                      : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:bg-slate-900 hover:text-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="font-semibold truncate text-slate-100 flex items-center gap-1.5">
                      <FileCode className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      <span className="truncate">{repo.name}</span>
                    </span>
                    {repo.is_private && (
                      <span title="Private repository" className="text-amber-400 shrink-0">
                        <Lock className="w-3 h-3" />
                      </span>
                    )}
                  </div>

                  <p className="text-[11px] text-slate-500 truncate mb-2">
                    {repo.owner}/{repo.name} • {repo.default_branch}
                  </p>

                  <div className="flex items-center justify-between text-[10px] text-slate-500">
                    <span className="flex items-center gap-1">
                      {isReady && <CheckCircle2 className="w-3 h-3 text-emerald-400" />}
                      {isWorking && <Loader2 className="w-3 h-3 animate-spin text-cyan-400" />}
                      {isFailed && <AlertCircle className="w-3 h-3 text-rose-400" />}
                      <span className="capitalize">{repo.status}</span>
                    </span>
                    <span>{repo.total_chunks} chunks</span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        <div className="p-3 border-t border-slate-800/80 bg-[#090e17] text-[11px] font-mono text-slate-500 text-center">
          FAISS Vector Engine • Isolated Indexes
        </div>
      </div>

      {/* Right Area: Repository Details & Chat Interface */}
      <div className="flex-1 bg-[#0c1322] border border-slate-800 rounded-xl flex flex-col overflow-hidden">
        {selectedRepo ? (
          <>
            {/* Repo Header */}
            <div className="p-4 border-b border-slate-800 bg-[#090e17] flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                  <GithubIcon className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-white font-mono">
                      {selectedRepo.name}
                    </h3>
                    <span className="text-xs font-mono text-slate-500">
                      ({selectedRepo.owner})
                    </span>
                    <a
                      href={selectedRepo.repo_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-slate-500 hover:text-slate-300 transition-colors"
                      title="Open on GitHub"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-400 font-mono mt-0.5">
                    <span className="flex items-center gap-1">
                      <GitBranch className="w-3 h-3 text-emerald-400" />
                      {selectedRepo.default_branch}
                    </span>
                    <span>•</span>
                    <span>{selectedRepo.total_files} files</span>
                    <span>•</span>
                    <span>{selectedRepo.total_chunks} vectors</span>
                    <span>•</span>
                    <span>{formatBytes(selectedRepo.total_size_bytes)}</span>
                  </div>
                </div>
              </div>

              {/* Header Action Buttons */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleReindex(selectedRepo.id)}
                  disabled={selectedRepo.status === 'indexing' || selectedRepo.status === 'importing'}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-xs font-mono transition-colors cursor-pointer"
                  title="Re-run FAISS indexing"
                >
                  <RotateCw className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Re-index</span>
                </button>
                <button
                  onClick={() => handleDeleteRepo(selectedRepo.id)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition-colors cursor-pointer"
                  title="Delete repository and index"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* In-Progress Progress Banner */}
            {(selectedRepo.status === 'importing' || selectedRepo.status === 'indexing') && (
              <div className="p-3 bg-cyan-950/40 border-b border-cyan-800/40 flex items-center justify-between text-xs font-mono text-cyan-300">
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
                  <span>
                    {selectedRepo.status === 'importing'
                      ? 'Fetching and filtering repository files from GitHub...'
                      : 'Chunking code and generating FAISS vector embeddings...'}
                  </span>
                </div>
                <span>Please wait</span>
              </div>
            )}

            {/* Error Banner */}
            {selectedRepo.status === 'failed' && (
              <div className="p-3 bg-rose-950/40 border-b border-rose-800/40 flex items-center justify-between text-xs font-mono text-rose-300">
                <div className="flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-rose-400" />
                  <span>Error: {selectedRepo.error_message || 'Indexing failed.'}</span>
                </div>
                <button
                  onClick={() => handleReindex(selectedRepo.id)}
                  className="px-2 py-0.5 rounded bg-rose-900/60 hover:bg-rose-800 text-rose-200 text-xs"
                >
                  Retry
                </button>
              </div>
            )}

            {/* Chat Message Stream */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center p-8 text-center text-slate-500 space-y-3">
                  <div className="w-12 h-12 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center text-emerald-400">
                    <MessageSquare className="w-6 h-6" />
                  </div>
                  <h4 className="text-sm font-semibold text-slate-200 font-mono">
                    Ask Questions About {selectedRepo.name}
                  </h4>
                  <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed font-sans">
                    CodePilot uses FAISS vector retrieval to find relevant source code chunks,
                    and synthesizes grounded answers with exact file paths and line ranges.
                  </p>

                  <div className="flex flex-wrap gap-2 justify-center max-w-lg pt-2">
                    {[
                      'How is authentication structured?',
                      'What are the primary API routes?',
                      'Explain the database models',
                      'Where are dependencies managed?',
                    ].map((example, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          setInputQuery(example);
                        }}
                        className="px-3 py-1.5 rounded-lg bg-slate-900/80 hover:bg-slate-850 border border-slate-800 text-[11px] font-mono text-slate-300 hover:text-emerald-400 hover:border-emerald-500/30 transition-all cursor-pointer"
                      >
                        {example}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex flex-col ${
                      msg.role === 'user' ? 'items-end' : 'items-start'
                    }`}
                  >
                    <div
                      className={`max-w-2xl rounded-2xl p-4 text-xs leading-relaxed ${
                        msg.role === 'user'
                          ? 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-200 rounded-tr-none font-mono'
                          : 'bg-[#090e17] border border-slate-800 text-slate-200 rounded-tl-none font-sans space-y-3'
                      }`}
                    >
                      <div className="whitespace-pre-wrap">{msg.content}</div>

                      {/* Evidence Insufficiency Notice */}
                      {msg.role === 'assistant' && msg.evidence_sufficient === false && (
                        <div className="p-2.5 rounded-lg bg-amber-950/40 border border-amber-500/30 text-amber-300 font-mono text-[11px] flex items-center gap-2">
                          <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                          <span>Repository evidence was insufficient to verify with certainty.</span>
                        </div>
                      )}

                      {/* Retrieved Source Citations */}
                      {msg.sources && msg.sources.length > 0 && (
                        <div className="pt-2 border-t border-slate-800/80 space-y-1.5">
                          <span className="text-[10px] font-mono uppercase text-slate-500 block">
                            Retrieved Code Citations ({msg.sources.length}):
                          </span>
                          <div className="flex flex-wrap gap-1.5">
                            {msg.sources.map((src, sIdx) => (
                              <button
                                key={sIdx}
                                onClick={() => setActiveChunkModal(src)}
                                className="flex items-center gap-1 px-2 py-1 rounded bg-slate-900 border border-slate-700/80 hover:border-emerald-500/40 text-[11px] font-mono text-emerald-400 hover:text-emerald-300 transition-colors cursor-pointer"
                              >
                                <Code2 className="w-3 h-3 text-slate-500" />
                                <span>{src.file_path}:{src.line_range}</span>
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}

              {isQuerying && (
                <div className="flex items-start">
                  <div className="bg-[#090e17] border border-slate-800 rounded-2xl rounded-tl-none p-4 text-xs font-mono text-slate-400 flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
                    <span>Searching FAISS vectors & synthesizing response...</span>
                  </div>
                </div>
              )}
            </div>

            {/* Chat Input Bar */}
            <form
              onSubmit={handleSendMessage}
              className="p-3 border-t border-slate-800 bg-[#090e17] flex items-center gap-2"
            >
              <input
                type="text"
                placeholder={
                  selectedRepo.status === 'ready'
                    ? `Ask anything about ${selectedRepo.name}...`
                    : 'Repository is indexing. Chat will be enabled once ready...'
                }
                value={inputQuery}
                disabled={selectedRepo.status !== 'ready' || isQuerying}
                onChange={(e) => setInputQuery(e.target.value)}
                className="flex-1 px-4 py-2 rounded-xl bg-slate-900 border border-slate-700/80 text-xs text-slate-100 placeholder:text-slate-500 font-mono focus:outline-none focus:border-emerald-500 disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={!inputQuery.trim() || selectedRepo.status !== 'ready' || isQuerying}
                className="p-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 disabled:bg-slate-800 disabled:text-slate-600 text-slate-950 font-semibold transition-colors cursor-pointer"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-500 space-y-3">
            <GithubIcon className="w-12 h-12 text-slate-600" />
            <h3 className="text-sm font-semibold text-slate-300 font-mono">
              No Repository Selected
            </h3>
            <p className="text-xs text-slate-400 max-w-sm font-sans">
              Select an imported repository from the sidebar or click Import to connect a new GitHub repository.
            </p>
          </div>
        )}
      </div>

      {/* Import Modal */}
      {isImportModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150">
          <div
            className="w-full max-w-md bg-[#0c1322] border border-slate-700 rounded-2xl shadow-2xl overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-[#090e17]">
              <div className="flex items-center gap-2">
                <GithubIcon className="w-5 h-5 text-emerald-400" />
                <h3 className="text-sm font-bold text-white font-mono">
                  Import GitHub Repository
                </h3>
              </div>
              <button
                onClick={() => setIsImportModalOpen(false)}
                className="p-1 rounded text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleImport} className="p-6 space-y-4 text-xs font-mono">
              <div>
                <label className="block text-slate-300 mb-1.5 font-medium">
                  GitHub Repository URL <span className="text-emerald-400">*</span>
                </label>
                <input
                  type="url"
                  required
                  placeholder="https://github.com/owner/repo"
                  value={importUrl}
                  onChange={(e) => setImportUrl(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500"
                />
                <span className="text-[10px] text-slate-500 mt-1 block">
                  Supports public and private GitHub repositories.
                </span>
              </div>

              <div>
                <label className="block text-slate-300 mb-1.5">
                  Display Name (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. My Backend Service"
                  value={importName}
                  onChange={(e) => setImportName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 mb-1.5">
                  Branch / Tag (Optional)
                </label>
                <input
                  type="text"
                  placeholder="main"
                  value={importBranch}
                  onChange={(e) => setImportBranch(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-slate-300 flex items-center gap-1">
                    <Lock className="w-3 h-3 text-amber-400" />
                    Personal Access Token (For Private Repos)
                  </label>
                </div>
                <input
                  type="password"
                  placeholder="ghp_xxxxxxxxxxxx"
                  value={importToken}
                  onChange={(e) => setImportToken(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500"
                />
                <span className="text-[10px] text-slate-500 mt-1 block leading-relaxed">
                  Never enter passwords. Scoped Personal Access Tokens are used transiently to fetch files and are never saved or logged.
                </span>
              </div>

              {importError && (
                <div className="p-3 rounded bg-rose-950/40 border border-rose-500/30 text-rose-300 text-xs">
                  {importError}
                </div>
              )}

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsImportModalOpen(false)}
                  className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isImporting}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold transition-colors disabled:opacity-50"
                >
                  {isImporting ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      Importing...
                    </>
                  ) : (
                    'Import & Index'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Code Chunk Detail Drawer / Modal */}
      {activeChunkModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150">
          <div
            className="w-full max-w-3xl bg-[#0c1322] border border-slate-700 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-[#090e17]">
              <div className="flex items-center gap-2 truncate">
                <Code2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span className="text-xs font-mono font-semibold text-slate-200 truncate">
                  {activeChunkModal.file_path}
                </span>
                <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] font-mono text-emerald-400">
                  Lines {activeChunkModal.line_range}
                </span>
                <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] font-mono text-slate-400 uppercase">
                  {activeChunkModal.language}
                </span>
              </div>
              <button
                onClick={() => setActiveChunkModal(null)}
                className="p-1 text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 p-4 overflow-y-auto bg-[#070b14] font-mono text-xs select-text">
              <pre className="text-slate-200 whitespace-pre-wrap leading-relaxed">
                {activeChunkModal.content}
              </pre>
            </div>

            <div className="p-3 border-t border-slate-800 bg-[#090e17] flex justify-between text-[11px] font-mono text-slate-500">
              <span>Similarity Score: {(activeChunkModal.score * 100).toFixed(1)}%</span>
              <button
                onClick={() => setActiveChunkModal(null)}
                className="px-3 py-1 rounded bg-slate-800 text-slate-300 hover:bg-slate-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
