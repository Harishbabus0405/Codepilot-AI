import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import type {
  GitAuditLogResponse,
  GitDiffResponse,
  GitPRCreateResponse,
  GitPRSummaryResponse,
  GitStatusResponse,
} from '../types/project';
import {
  GitBranch,
  GitCommit,
  GitPullRequest,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Sparkles,
  Plus,
  RotateCw,
  ExternalLink,
  FileCode,
  History,
  ShieldCheck,
  Eye,
  EyeOff,
  FolderGit2,
} from 'lucide-react';


interface VersionControlPanelProps {
  workspaceId: string;
  workspaceName?: string;
  isProject?: boolean;
}

export const VersionControlPanel: React.FC<VersionControlPanelProps> = ({
  workspaceId,
  workspaceName = 'Project Workspace',
}) => {
  // Git Status & Diff States
  const [status, setStatus] = useState<GitStatusResponse | null>(null);
  const [diff, setDiff] = useState<GitDiffResponse | null>(null);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [branches, setBranches] = useState<string[]>([]);
  const [currentBranch, setCurrentBranch] = useState<string>('main');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Tab State
  const [activeTab, setActiveTab] = useState<'commit' | 'pr' | 'audit'>('commit');

  // New Branch State
  const [isCreatingBranch, setIsCreatingBranch] = useState<boolean>(false);
  const [newBranchName, setNewBranchName] = useState<string>('');
  const [branchError, setBranchError] = useState<string | null>(null);

  // Commit Form State
  const [commitMessage, setCommitMessage] = useState<string>('');
  const [commitApproved, setCommitApproved] = useState<boolean>(false);
  const [isCommitting, setIsCommitting] = useState<boolean>(false);
  const [isProposingMsg, setIsProposingMsg] = useState<boolean>(false);
  const [commitSuccess, setCommitSuccess] = useState<string | null>(null);

  // Pull Request Form State
  const [prRepoUrl, setPrRepoUrl] = useState<string>('');
  const [prTitle, setPrTitle] = useState<string>('');
  const [prBody, setPrBody] = useState<string>('');
  const [prBaseBranch, setPrBaseBranch] = useState<string>('main');
  const [prHeadBranch, setPrHeadBranch] = useState<string>('');
  const [prToken, setPrToken] = useState<string>('');
  const [showToken, setShowToken] = useState<boolean>(false);
  const [prApproved, setPrApproved] = useState<boolean>(false);
  const [isGeneratingPRSummary, setIsGeneratingPRSummary] = useState<boolean>(false);
  const [isCreatingPR, setIsCreatingPR] = useState<boolean>(false);
  const [prSuccess, setPrSuccess] = useState<GitPRCreateResponse | null>(null);
  const [prError, setPrError] = useState<string | null>(null);

  // Audit Logs State
  const [auditLogs, setAuditLogs] = useState<GitAuditLogResponse[]>([]);
  const [isLoadingAudit, setIsLoadingAudit] = useState<boolean>(false);

  // Load Status & Branches
  const loadGitState = useCallback(async (isInitial = false) => {
    if (isInitial) setIsLoading(true);
    else setIsRefreshing(true);
    setError(null);

    try {
      const gitStatus = await api.getGitStatus(workspaceId);
      setStatus(gitStatus);
      if (gitStatus.current_branch) {
        setCurrentBranch(gitStatus.current_branch);
        setPrHeadBranch(gitStatus.current_branch);
      }

      if (gitStatus.is_git_repo) {
        const [diffData, branchData] = await Promise.all([
          api.getGitDiff(workspaceId, false, selectedFile || undefined),
          api.listBranches(workspaceId),
        ]);
        setDiff(diffData);
        setBranches(branchData.branches);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to inspect Git workspace status.');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [workspaceId, selectedFile]);

  useEffect(() => {
    loadGitState(true);
  }, [loadGitState]);

  // Load Audit Logs when Audit tab is selected
  useEffect(() => {
    if (activeTab === 'audit') {
      setIsLoadingAudit(true);
      api
        .getGitAuditLogs(workspaceId)
        .then((logs) => setAuditLogs(logs))
        .catch(() => {})
        .finally(() => setIsLoadingAudit(false));
    }
  }, [activeTab, workspaceId]);

  // Initialize Git
  const handleInitGit = async () => {
    setIsRefreshing(true);
    setError(null);
    try {
      await api.initGit(workspaceId);
      await loadGitState();
    } catch (err: any) {
      setError(err.message || 'Failed to initialize Git repository.');
    } finally {
      setIsRefreshing(false);
    }
  };

  // Branch creation
  const handleCreateBranch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newBranchName.trim()) return;
    setBranchError(null);
    try {
      const res = await api.createBranch(workspaceId, newBranchName.trim(), true);
      setCurrentBranch(res.current_branch);
      setPrHeadBranch(res.current_branch);
      setNewBranchName('');
      setIsCreatingBranch(false);
      await loadGitState();
    } catch (err: any) {
      setBranchError(err.message || 'Failed to create branch.');
    }
  };

  // Branch checkout
  const handleCheckoutBranch = async (branch: string) => {
    if (branch === currentBranch) return;
    setError(null);
    try {
      const res = await api.checkoutBranch(workspaceId, branch);
      setCurrentBranch(res.current_branch);
      setPrHeadBranch(res.current_branch);
      await loadGitState();
    } catch (err: any) {
      setError(err.message || `Failed to checkout branch '${branch}'.`);
    }
  };

  // Propose commit message via AI
  const handleProposeMessage = async () => {
    setIsProposingMsg(true);
    setError(null);
    try {
      const res = await api.proposeCommitMessage(workspaceId);
      setCommitMessage(res.proposed_message);
    } catch (err: any) {
      setError(err.message || 'Failed to propose commit message.');
    } finally {
      setIsProposingMsg(false);
    }
  };

  // Execute Commit
  const handleCommit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commitApproved) {
      setError('Please review and check the confirmation box to approve this commit.');
      return;
    }
    if (!commitMessage.trim()) {
      setError('Commit message cannot be empty.');
      return;
    }

    setIsCommitting(true);
    setError(null);
    setCommitSuccess(null);

    try {
      const res = await api.createCommit(workspaceId, {
        message: commitMessage.trim(),
        files: selectedFile ? [selectedFile] : undefined,
        approved: true,
      });
      setCommitSuccess(`Committed ${res.files_committed} file(s) [${res.commit_sha.slice(0, 7)}] on ${res.branch}`);
      setCommitMessage('');
      setCommitApproved(false);
      setSelectedFile(null);
      await loadGitState();
    } catch (err: any) {
      setError(err.message || 'Commit failed.');
    } finally {
      setIsCommitting(false);
    }
  };

  // Generate PR Summary
  const handleGeneratePRSummary = async () => {
    setIsGeneratingPRSummary(true);
    setPrError(null);
    try {
      const summary: GitPRSummaryResponse = await api.getPRSummary(workspaceId, prBaseBranch);
      setPrTitle(summary.title);
      setPrBody(summary.body);
    } catch (err: any) {
      setPrError(err.message || 'Failed to generate PR summary.');
    } finally {
      setIsGeneratingPRSummary(false);
    }
  };

  // Create Pull Request
  const handleCreatePR = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prApproved) {
      setPrError('Explicit user approval is required to create a Pull Request.');
      return;
    }
    if (!prToken.trim()) {
      setPrError('A valid GitHub Personal Access Token is required.');
      return;
    }
    if (!prRepoUrl.trim()) {
      setPrError('Target GitHub repository (owner/repo) is required.');
      return;
    }

    setIsCreatingPR(true);
    setPrError(null);
    setPrSuccess(null);

    try {
      const res = await api.createPullRequest(workspaceId, {
        repo_url: prRepoUrl.trim(),
        title: prTitle.trim(),
        body: prBody.trim(),
        head_branch: prHeadBranch || currentBranch,
        base_branch: prBaseBranch || 'main',
        github_token: prToken.trim(),
        approved: true,
      });
      setPrSuccess(res);
      setPrApproved(false);
    } catch (err: any) {
      setPrError(err.message || 'GitHub Pull Request creation failed.');
    } finally {
      setIsCreatingPR(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-500 mb-3" />
        <p className="text-sm">Inspecting Git workspace status...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-slate-900 text-slate-100 rounded-lg overflow-hidden border border-slate-800">
      {/* Top Header Bar */}
      <div className="px-5 py-4 border-b border-slate-800 bg-slate-950/60 flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-emerald-500/10 border border-emerald-500/20 rounded-md text-emerald-400">
            <FolderGit2 className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-base font-semibold text-slate-100">{workspaceName}</h2>
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                Git Workspace
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Controlled Version Control & GitHub Integration
            </p>
          </div>
        </div>

        {/* Branch Indicator & Controls */}
        <div className="flex items-center space-x-2">
          {status?.is_git_repo ? (
            <>
              {/* Branch Selector */}
              <div className="flex items-center bg-slate-900 border border-slate-700 rounded-md px-2.5 py-1.5 text-xs text-slate-200">
                <GitBranch className="w-3.5 h-3.5 mr-1.5 text-emerald-400" />
                <select
                  value={currentBranch}
                  onChange={(e) => handleCheckoutBranch(e.target.value)}
                  className="bg-transparent text-xs text-slate-200 focus:outline-none cursor-pointer"
                >
                  {branches.map((b) => (
                    <option key={b} value={b} className="bg-slate-900 text-slate-200">
                      {b}
                    </option>
                  ))}
                </select>
              </div>

              {/* New Branch Button */}
              <button
                onClick={() => setIsCreatingBranch(!isCreatingBranch)}
                className="flex items-center px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-md border border-slate-700 transition"
                title="Create a new branch"
              >
                <Plus className="w-3.5 h-3.5 mr-1 text-slate-400" />
                New Branch
              </button>
            </>
          ) : null}

          {/* Refresh Button */}
          <button
            onClick={() => loadGitState()}
            disabled={isRefreshing}
            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-md border border-slate-700 transition"
            title="Refresh Git status"
          >
            <RotateCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-emerald-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* New Branch Dialog Drawer */}
      {isCreatingBranch && (
        <form
          onSubmit={handleCreateBranch}
          className="p-4 bg-slate-950/80 border-b border-slate-800 flex items-center space-x-3 text-xs"
        >
          <span className="text-slate-400 font-medium">New Branch:</span>
          <input
            type="text"
            placeholder="e.g. feature/payment-gateway"
            value={newBranchName}
            onChange={(e) => setNewBranchName(e.target.value)}
            className="flex-1 bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-slate-200 focus:outline-none focus:border-emerald-500"
            autoFocus
          />
          <button
            type="submit"
            className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded transition"
          >
            Create & Checkout
          </button>
          <button
            type="button"
            onClick={() => setIsCreatingBranch(false)}
            className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-400 rounded transition"
          >
            Cancel
          </button>
          {branchError && <span className="text-rose-400 text-xs">{branchError}</span>}
        </form>
      )}

      {/* Uninitialized Git Banner */}
      {!status?.is_git_repo && (
        <div className="m-6 p-8 bg-slate-950/50 border border-dashed border-slate-700 rounded-xl flex flex-col items-center justify-center text-center">
          <div className="w-12 h-12 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-400 mb-4">
            <GitBranch className="w-6 h-6" />
          </div>
          <h3 className="text-base font-medium text-slate-200 mb-1">Git Repository Not Initialized</h3>
          <p className="text-xs text-slate-400 max-w-md mb-5">
            Initialize an isolated local Git repository with safe branch defaults and a protected .gitignore to inspect diffs, review changes, commit, and open pull requests.
          </p>
          <button
            onClick={handleInitGit}
            disabled={isRefreshing}
            className="flex items-center space-x-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-md shadow-lg shadow-emerald-950 transition"
          >
            {isRefreshing ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : (
              <FolderGit2 className="w-4 h-4 mr-2" />
            )}
            Initialize Git Workspace
          </button>
        </div>
      )}

      {/* Main Two-Pane View when Git is Initialized */}
      {status?.is_git_repo && (
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 min-h-0 overflow-hidden">
          {/* Left Column: Changed Files (4 cols) */}
          <div className="lg:col-span-4 border-r border-slate-800 flex flex-col h-full bg-slate-950/30 overflow-hidden">
            {/* Working Tree Header */}
            <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
              <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Changes ({status.total_changes})
              </span>
              <button
                onClick={() => setSelectedFile(null)}
                className={`text-[11px] px-2 py-0.5 rounded transition ${
                  selectedFile === null
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                All Diffs
              </button>
            </div>

            {/* Changed Files List */}
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {status.is_clean && (
                <div className="py-8 text-center text-slate-500 text-xs">
                  <CheckCircle2 className="w-8 h-8 mx-auto text-emerald-500/60 mb-2" />
                  <p className="text-slate-300 font-medium">Working tree clean</p>
                  <p className="mt-0.5 text-slate-500">No uncommitted changes</p>
                  {status.latest_commit && (
                    <div className="mt-4 p-2 bg-slate-900/80 rounded border border-slate-800 text-left text-[11px]">
                      <span className="text-slate-400 font-mono">
                        {status.latest_commit.sha.slice(0, 7)}
                      </span>
                      <p className="text-slate-300 truncate mt-0.5">{status.latest_commit.message}</p>
                    </div>
                  )}
                </div>
              )}

              {/* Staged Files */}
              {status.staged_files.length > 0 && (
                <div className="mb-2">
                  <div className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider px-2 py-1">
                    Staged ({status.staged_files.length})
                  </div>
                  {status.staged_files.map((file) => (
                    <button
                      key={file.path}
                      onClick={() => setSelectedFile(file.path)}
                      className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded text-left text-xs transition ${
                        selectedFile === file.path
                          ? 'bg-slate-800 text-slate-100 font-medium'
                          : 'text-slate-300 hover:bg-slate-900'
                      }`}
                    >
                      <div className="flex items-center space-x-2 truncate">
                        <FileCode className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                        <span className="truncate">{file.path}</span>
                      </div>
                      <span className="text-[10px] uppercase font-mono px-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800/40">
                        {file.status[0]}
                      </span>
                    </button>
                  ))}
                </div>
              )}

              {/* Unstaged Files */}
              {status.unstaged_files.length > 0 && (
                <div className="mb-2">
                  <div className="text-[10px] font-semibold text-amber-400 uppercase tracking-wider px-2 py-1">
                    Unstaged ({status.unstaged_files.length})
                  </div>
                  {status.unstaged_files.map((file) => (
                    <button
                      key={file.path}
                      onClick={() => setSelectedFile(file.path)}
                      className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded text-left text-xs transition ${
                        selectedFile === file.path
                          ? 'bg-slate-800 text-slate-100 font-medium'
                          : 'text-slate-300 hover:bg-slate-900'
                      }`}
                    >
                      <div className="flex items-center space-x-2 truncate">
                        <FileCode className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                        <span className="truncate">{file.path}</span>
                      </div>
                      <span className="text-[10px] uppercase font-mono px-1 rounded bg-amber-950 text-amber-400 border border-amber-800/40">
                        {file.status[0]}
                      </span>
                    </button>
                  ))}
                </div>
              )}

              {/* Untracked Files */}
              {status.untracked_files.length > 0 && (
                <div>
                  <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider px-2 py-1">
                    Untracked ({status.untracked_files.length})
                  </div>
                  {status.untracked_files.map((path) => (
                    <button
                      key={path}
                      onClick={() => setSelectedFile(path)}
                      className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded text-left text-xs transition ${
                        selectedFile === path
                          ? 'bg-slate-800 text-slate-100 font-medium'
                          : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
                      }`}
                    >
                      <div className="flex items-center space-x-2 truncate">
                        <FileCode className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                        <span className="truncate">{path}</span>
                      </div>
                      <span className="text-[10px] font-mono px-1 rounded bg-slate-800 text-slate-400 border border-slate-700">
                        ?
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Diff Preview + Actions (8 cols) */}
          <div className="lg:col-span-8 flex flex-col h-full overflow-hidden">
            {/* Diff Preview Pane (Top half) */}
            <div className="flex-1 flex flex-col min-h-[220px] max-h-[50%] border-b border-slate-800 bg-slate-950/70 overflow-hidden">
              <div className="px-4 py-2 border-b border-slate-800/80 bg-slate-900/80 flex items-center justify-between text-xs">
                <span className="font-mono text-slate-300">
                  {selectedFile ? `diff: ${selectedFile}` : 'Working Tree Diff'}
                </span>
                {diff && (
                  <div className="flex items-center space-x-3 text-[11px] font-mono">
                    <span className="text-emerald-400">+{diff.insertions}</span>
                    <span className="text-rose-400">-{diff.deletions}</span>
                    <span className="text-slate-400">{diff.files_changed.length} file(s)</span>
                  </div>
                )}
              </div>

              <div className="flex-1 overflow-auto p-3 font-mono text-[11px] leading-relaxed select-text">
                {diff?.diff ? (
                  diff.diff.split('\n').map((line, idx) => {
                    let lineClass = 'text-slate-300';
                    if (line.startsWith('+') && !line.startsWith('+++')) {
                      lineClass = 'bg-emerald-950/50 text-emerald-300';
                    } else if (line.startsWith('-') && !line.startsWith('---')) {
                      lineClass = 'bg-rose-950/50 text-rose-300';
                    } else if (line.startsWith('@@')) {
                      lineClass = 'bg-cyan-950/40 text-cyan-400 font-semibold';
                    } else if (line.startsWith('diff --git')) {
                      lineClass = 'text-amber-300 font-bold mt-2 pt-1 border-t border-slate-800';
                    }
                    return (
                      <div key={idx} className={`px-1 py-0.5 whitespace-pre ${lineClass}`}>
                        {line || ' '}
                      </div>
                    );
                  })
                ) : (
                  <div className="h-full flex items-center justify-center text-slate-500 text-xs">
                    {status.is_clean ? 'Working directory is clean.' : 'Select a changed file or modify source code to inspect diffs.'}
                  </div>
                )}
              </div>
            </div>

            {/* Bottom Actions Pane with Tabs */}
            <div className="flex-1 flex flex-col min-h-0 bg-slate-900/60 overflow-hidden">
              {/* Tab navigation */}
              <div className="flex border-b border-slate-800 bg-slate-950/80 px-4 text-xs">
                <button
                  onClick={() => setActiveTab('commit')}
                  className={`py-2.5 px-3 font-medium flex items-center space-x-1.5 border-b-2 transition ${
                    activeTab === 'commit'
                      ? 'border-emerald-500 text-emerald-400 bg-slate-900/50'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <GitCommit className="w-3.5 h-3.5" />
                  <span>Review & Commit</span>
                </button>
                <button
                  onClick={() => setActiveTab('pr')}
                  className={`py-2.5 px-3 font-medium flex items-center space-x-1.5 border-b-2 transition ${
                    activeTab === 'pr'
                      ? 'border-emerald-500 text-emerald-400 bg-slate-900/50'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <GitPullRequest className="w-3.5 h-3.5" />
                  <span>Create Pull Request</span>
                </button>
                <button
                  onClick={() => setActiveTab('audit')}
                  className={`py-2.5 px-3 font-medium flex items-center space-x-1.5 border-b-2 transition ${
                    activeTab === 'audit'
                      ? 'border-emerald-500 text-emerald-400 bg-slate-900/50'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <History className="w-3.5 h-3.5" />
                  <span>Audit History</span>
                </button>
              </div>

              {/* Tab 1: Review & Commit */}
              {activeTab === 'commit' && (
                <form onSubmit={handleCommit} className="flex-1 overflow-y-auto p-4 flex flex-col space-y-3">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-medium text-slate-300">
                      Commit Message
                    </label>
                    <button
                      type="button"
                      onClick={handleProposeMessage}
                      disabled={isProposingMsg || status.is_clean}
                      className="flex items-center space-x-1 text-xs text-emerald-400 hover:text-emerald-300 disabled:opacity-50 transition"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>{isProposingMsg ? 'Proposing...' : 'AI Propose Message'}</span>
                    </button>
                  </div>

                  <textarea
                    rows={3}
                    placeholder="e.g. feat(api): add repository intelligence and git workflows"
                    value={commitMessage}
                    onChange={(e) => setCommitMessage(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-md p-2.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-mono"
                  />

                  {/* Strict User Approval Checkbox */}
                  <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-md">
                    <label className="flex items-start space-x-2 text-xs text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={commitApproved}
                        onChange={(e) => setCommitApproved(e.target.checked)}
                        className="mt-0.5 rounded border-slate-700 bg-slate-900 text-emerald-500 focus:ring-0 focus:outline-none"
                      />
                      <div>
                        <span className="font-medium text-slate-200">
                          Approve commit to branch <code className="text-emerald-400 font-mono">{currentBranch}</code>
                        </span>
                        <p className="text-[11px] text-slate-400 mt-0.5">
                          Requires explicit user confirmation before recording the commit in this workspace.
                        </p>
                      </div>
                    </label>
                  </div>

                  {commitSuccess && (
                    <div className="p-2.5 bg-emerald-950/40 border border-emerald-800/50 rounded text-xs text-emerald-300 flex items-center space-x-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>{commitSuccess}</span>
                    </div>
                  )}

                  {error && (
                    <div className="p-2.5 bg-rose-950/40 border border-rose-800/50 rounded text-xs text-rose-300 flex items-center space-x-2">
                      <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                      <span>{error}</span>
                    </div>
                  )}

                  <div className="pt-1">
                    <button
                      type="submit"
                      disabled={isCommitting || !commitApproved || !commitMessage.trim() || status.is_clean}
                      className="flex items-center space-x-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-medium rounded-md shadow-md transition"
                    >
                      {isCommitting ? (
                        <Loader2 className="w-4 h-4 animate-spin mr-1" />
                      ) : (
                        <GitCommit className="w-4 h-4 mr-1" />
                      )}
                      <span>Commit Changes</span>
                    </button>
                  </div>
                </form>
              )}

              {/* Tab 2: Create Pull Request */}
              {activeTab === 'pr' && (
                <form onSubmit={handleCreatePR} className="flex-1 overflow-y-auto p-4 flex flex-col space-y-3 text-xs">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-slate-200">GitHub Pull Request Details</h3>
                    <button
                      type="button"
                      onClick={handleGeneratePRSummary}
                      disabled={isGeneratingPRSummary}
                      className="flex items-center space-x-1 text-emerald-400 hover:text-emerald-300 text-xs transition"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>{isGeneratingPRSummary ? 'Synthesizing...' : 'Generate PR Summary from Diffs & QA'}</span>
                    </button>
                  </div>

                  {/* Repo URL & Branches */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                    <div>
                      <label className="block text-[11px] font-medium text-slate-400 mb-1">
                        GitHub Repo (owner/repo)
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. octocat/Hello-World"
                        value={prRepoUrl}
                        onChange={(e) => setPrRepoUrl(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 font-mono"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-medium text-slate-400 mb-1">
                        Base Branch (target)
                      </label>
                      <input
                        type="text"
                        placeholder="main"
                        value={prBaseBranch}
                        onChange={(e) => setPrBaseBranch(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 font-mono"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-medium text-slate-400 mb-1">
                        Head Branch (source)
                      </label>
                      <input
                        type="text"
                        placeholder="current branch"
                        value={prHeadBranch}
                        onChange={(e) => setPrHeadBranch(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 font-mono"
                        required
                      />
                    </div>
                  </div>

                  {/* PR Title */}
                  <div>
                    <label className="block text-[11px] font-medium text-slate-400 mb-1">
                      Pull Request Title
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. feat: integrate GitHub developer workflow"
                      value={prTitle}
                      onChange={(e) => setPrTitle(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                      required
                    />
                  </div>

                  {/* PR Body */}
                  <div>
                    <label className="block text-[11px] font-medium text-slate-400 mb-1">
                      Pull Request Description (Markdown)
                    </label>
                    <textarea
                      rows={4}
                      placeholder="## Overview\nSummary of changes..."
                      value={prBody}
                      onChange={(e) => setPrBody(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 font-mono"
                    />
                  </div>

                  {/* GitHub Token with Security Safeguards */}
                  <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-md">
                    <div className="flex items-center justify-between mb-1">
                      <label className="flex items-center text-[11px] font-medium text-slate-300">
                        <ShieldCheck className="w-3.5 h-3.5 mr-1 text-emerald-400" />
                        GitHub Personal Access Token (PAT)
                      </label>
                      <button
                        type="button"
                        onClick={() => setShowToken(!showToken)}
                        className="text-[11px] text-slate-400 hover:text-slate-200 flex items-center space-x-1"
                      >
                        {showToken ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                        <span>{showToken ? 'Hide' : 'Show'}</span>
                      </button>
                    </div>
                    <input
                      type={showToken ? 'text' : 'password'}
                      placeholder="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                      value={prToken}
                      onChange={(e) => setPrToken(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 font-mono"
                      required
                    />
                    <p className="text-[10px] text-slate-500 mt-1">
                      Tokens are processed strictly in-flight for this single API call. They are NEVER logged, persisted, or saved.
                    </p>
                  </div>

                  {/* Strict User Approval Checkbox */}
                  <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-md">
                    <label className="flex items-start space-x-2 text-xs text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={prApproved}
                        onChange={(e) => setPrApproved(e.target.checked)}
                        className="mt-0.5 rounded border-slate-700 bg-slate-900 text-emerald-500 focus:ring-0 focus:outline-none"
                      />
                      <div>
                        <span className="font-medium text-slate-200">
                          Approve Pull Request creation on GitHub
                        </span>
                        <p className="text-[11px] text-slate-400 mt-0.5">
                          Requires explicit confirmation before submitting a Pull Request to external GitHub API.
                        </p>
                      </div>
                    </label>
                  </div>

                  {prSuccess && (
                    <div className="p-3 bg-emerald-950/40 border border-emerald-800/60 rounded-md text-xs text-emerald-300">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-emerald-200">Pull Request Created Successfully!</span>
                        <a
                          href={prSuccess.pull_request_url}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center text-xs text-emerald-400 hover:underline"
                        >
                          <span>PR #{prSuccess.pull_request_number}</span>
                          <ExternalLink className="w-3 h-3 ml-1" />
                        </a>
                      </div>
                      <p className="mt-1 text-[11px] text-slate-300">{prSuccess.title}</p>
                    </div>
                  )}

                  {prError && (
                    <div className="p-3 bg-rose-950/40 border border-rose-800/60 rounded-md text-xs text-rose-300 flex items-start space-x-2">
                      <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                      <span>{prError}</span>
                    </div>
                  )}

                  <div className="pt-1">
                    <button
                      type="submit"
                      disabled={isCreatingPR || !prApproved || !prToken.trim() || !prTitle.trim() || !prRepoUrl.trim()}
                      className="flex items-center space-x-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-medium rounded-md shadow-md transition"
                    >
                      {isCreatingPR ? (
                        <Loader2 className="w-4 h-4 animate-spin mr-1" />
                      ) : (
                        <GitPullRequest className="w-4 h-4 mr-1" />
                      )}
                      <span>Submit Pull Request to GitHub</span>
                    </button>
                  </div>
                </form>
              )}

              {/* Tab 3: Audit Trail */}
              {activeTab === 'audit' && (
                <div className="flex-1 overflow-y-auto p-4 space-y-2 text-xs">
                  {isLoadingAudit ? (
                    <div className="flex items-center justify-center p-8 text-slate-400">
                      <Loader2 className="w-5 h-5 animate-spin mr-2" />
                      <span>Loading operation audit trail...</span>
                    </div>
                  ) : auditLogs.length === 0 ? (
                    <p className="text-center text-slate-500 py-8">No Git operations recorded yet.</p>
                  ) : (
                    auditLogs.map((log) => (
                      <div
                        key={log.id}
                        className="p-3 bg-slate-950/60 border border-slate-800 rounded-md flex items-center justify-between"
                      >
                        <div className="flex items-center space-x-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase ${
                              log.status === 'success'
                                ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/40'
                                : 'bg-rose-950 text-rose-400 border border-rose-800/40'
                            }`}
                          >
                            {log.operation}
                          </span>
                          <div>
                            <div className="flex items-center space-x-2">
                              {log.branch && (
                                <span className="text-slate-300 font-mono text-[11px]">
                                  {log.branch}
                                </span>
                              )}
                              {log.commit_sha && (
                                <span className="text-slate-500 font-mono text-[10px]">
                                  [{log.commit_sha.slice(0, 7)}]
                                </span>
                              )}
                            </div>
                            {log.error_message && (
                              <p className="text-rose-400 text-[11px] mt-0.5">{log.error_message}</p>
                            )}
                          </div>
                        </div>
                        <span className="text-[10px] text-slate-500">
                          {new Date(log.created_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
