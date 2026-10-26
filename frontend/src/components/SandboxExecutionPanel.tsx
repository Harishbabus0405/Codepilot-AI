import React, { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../services/api';
import type {
  SandboxJobCreateRequest,
  SandboxJobResponse,
  SandboxQuotaStatusResponse,
  SandboxWorkloadType,
} from '../types/project';
import {
  Shield,
  Play,
  RotateCw,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Clock,
  Terminal,
  Copy,
  Check,
} from 'lucide-react';


interface SandboxExecutionPanelProps {
  projectId: string;
  projectName?: string;
}

const WORKLOAD_OPTIONS: {
  id: SandboxWorkloadType;
  label: string;
  description: string;
  defaultCommand: string;
}[] = [
  {
    id: 'python_pytest',
    label: 'Python Automated Tests (pytest)',
    description: 'Runs full pytest test suite in disposable Python container.',
    defaultCommand: 'pytest -v',
  },
  {
    id: 'python_syntax',
    label: 'Python Syntax Validation (compileall)',
    description: 'Compiles and verifies AST syntax of all Python source files.',
    defaultCommand: 'python -m compileall -q .',
  },
  {
    id: 'react_build',
    label: 'React Frontend Build (npm run build)',
    description: 'Audits frontend TypeScript compilation and Vite packaging.',
    defaultCommand: 'npm run build',
  },
];

export const SandboxExecutionPanel: React.FC<SandboxExecutionPanelProps> = ({
  projectId,
  projectName = 'Project',
}) => {
  const [workloadType, setWorkloadType] = useState<SandboxWorkloadType>('python_pytest');
  const [customArgs, setCustomArgs] = useState<string>('');
  const [timeoutSeconds, setTimeoutSeconds] = useState<number>(30);

  const [activeJob, setActiveJob] = useState<SandboxJobResponse | null>(null);
  const [recentJobs, setRecentJobs] = useState<SandboxJobResponse[]>([]);
  const [quota, setQuota] = useState<SandboxQuotaStatusResponse | null>(null);

  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isLoadingJobs, setIsLoadingJobs] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  const pollIntervalRef = useRef<number | null>(null);

  // Load quota and recent jobs
  const loadInitialData = useCallback(async () => {
    setIsLoadingJobs(true);
    try {
      const [quotaData, jobsData] = await Promise.all([
        api.getSandboxQuota(projectId).catch(() => null),
        api.getSandboxJobs(projectId, 10).catch(() => ({ jobs: [], total: 0 })),
      ]);
      setQuota(quotaData);
      setRecentJobs(jobsData.jobs);
      if (jobsData.jobs.length > 0 && !activeJob) {
        setActiveJob(jobsData.jobs[0]);
      }
    } catch (err: any) {
      console.error('Failed to load sandbox data:', err);
    } finally {
      setIsLoadingJobs(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Poll active job while queued or running
  useEffect(() => {
    if (activeJob && (activeJob.status === 'queued' || activeJob.status === 'running')) {
      pollIntervalRef.current = window.setInterval(async () => {
        try {
          const updated = await api.getSandboxJob(projectId, activeJob.id);
          setActiveJob(updated);
          if (updated.status !== 'queued' && updated.status !== 'running') {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            // Refresh list and quota
            api.getSandboxJobs(projectId, 10).then((res) => setRecentJobs(res.jobs));
            api.getSandboxQuota(projectId).then((q) => setQuota(q));
          }
        } catch {
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        }
      }, 1000);
    }

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [activeJob?.id, activeJob?.status, projectId]);

  // Execute Sandbox Job
  const handleLaunchJob = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    const argsList = customArgs.trim()
      ? customArgs.trim().split(/\s+/).filter(Boolean)
      : undefined;

    const payload: SandboxJobCreateRequest = {
      workload_type: workloadType,
      custom_args: argsList,
      timeout_seconds: timeoutSeconds,
    };

    try {
      const newJob = await api.createSandboxJob(projectId, payload);
      setActiveJob(newJob);
      setRecentJobs((prev) => [newJob, ...prev.filter((j) => j.id !== newJob.id)]);
      api.getSandboxQuota(projectId).then((q) => setQuota(q));
    } catch (err: any) {
      setError(err.message || 'Failed to launch sandbox execution job.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCopyLogs = () => {
    if (!activeJob) return;
    const content = `${activeJob.stdout || ''}\n${activeJob.stderr || ''}`;
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <span className="flex items-center px-2 py-0.5 rounded text-[11px] font-mono bg-emerald-950 text-emerald-400 border border-emerald-800/40">
            <CheckCircle2 className="w-3 h-3 mr-1" />
            COMPLETED
          </span>
        );
      case 'failed':
        return (
          <span className="flex items-center px-2 py-0.5 rounded text-[11px] font-mono bg-rose-950 text-rose-400 border border-rose-800/40">
            <AlertCircle className="w-3 h-3 mr-1" />
            FAILED
          </span>
        );
      case 'timed_out':
        return (
          <span className="flex items-center px-2 py-0.5 rounded text-[11px] font-mono bg-purple-950 text-purple-400 border border-purple-800/40">
            <Clock className="w-3 h-3 mr-1" />
            TIMED OUT
          </span>
        );
      case 'running':
        return (
          <span className="flex items-center px-2 py-0.5 rounded text-[11px] font-mono bg-amber-950 text-amber-400 border border-amber-800/40 animate-pulse">
            <Loader2 className="w-3 h-3 mr-1 animate-spin" />
            RUNNING
          </span>
        );
      case 'queued':
      default:
        return (
          <span className="flex items-center px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
            <Clock className="w-3 h-3 mr-1" />
            QUEUED
          </span>
        );
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#0c1322] border border-slate-800 rounded-xl overflow-hidden text-slate-100">
      {/* Top Banner: Security Architecture & Quota */}
      <div className="p-4 border-b border-slate-800 bg-[#090e17] flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-400">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <span>Isolated Execution Sandbox</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                DISPOSABLE CONTAINERS
              </span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Execute test suites for <span className="text-slate-200 font-medium">{projectName}</span> in hardened air-gapped sandboxes without exposing host processes.
            </p>
          </div>
        </div>

        {/* Quota & Host Info Badges */}
        <div className="flex items-center space-x-2 text-xs font-mono">
          {quota && (
            <>
              <span className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
                Quota: {quota.hourly_runs_used}/{quota.hourly_runs_limit} runs/hr
              </span>
              <span
                className={`px-2 py-1 rounded border ${
                  quota.docker_available
                    ? 'bg-emerald-950/40 text-emerald-400 border-emerald-800/40'
                    : 'bg-amber-950/40 text-amber-400 border-amber-800/40'
                }`}
                title={
                  quota.docker_available
                    ? 'Docker daemon connected on host'
                    : 'Docker CLI not found on host; running simulated isolated checks'
                }
              >
                {quota.docker_available ? '🐳 Docker Active' : '🛡️ Air-Gapped Sandbox'}
              </span>
            </>
          )}
          <button
            onClick={() => loadInitialData()}
            className="p-1 bg-slate-800 hover:bg-slate-700 rounded border border-slate-700 text-slate-300 transition"
            title="Refresh jobs and quota"
          >
            <RotateCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Security Isolation Badges Bar */}
      <div className="px-4 py-2 border-b border-slate-800/80 bg-slate-950/70 flex items-center gap-3 overflow-x-auto text-[11px] text-slate-400 font-mono">
        <span className="flex items-center text-emerald-400">
          <Shield className="w-3 h-3 mr-1" /> Network: NONE
        </span>
        <span className="text-slate-600">•</span>
        <span>User: 1000:1000 (Non-Root)</span>
        <span className="text-slate-600">•</span>
        <span>Capabilities: ALL DROPPED</span>
        <span className="text-slate-600">•</span>
        <span>Memory: 512 MB</span>
        <span className="text-slate-600">•</span>
        <span>CPU: 1.0</span>
        <span className="text-slate-600">•</span>
        <span>PIDs: 64 Max</span>
        <span className="text-slate-600">•</span>
        <span>Mount: Workspace Only</span>
      </div>

      {/* Main Two-Pane View */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 min-h-0 overflow-hidden">
        {/* Left Pane: Job Configuration & History (5 cols) */}
        <div className="lg:col-span-5 border-r border-slate-800 flex flex-col h-full bg-[#080d16] overflow-y-auto p-4 space-y-4">
          <form onSubmit={handleLaunchJob} className="space-y-3">
            <h3 className="text-xs font-semibold text-slate-200 uppercase tracking-wider flex items-center">
              <Play className="w-3.5 h-3.5 mr-1.5 text-emerald-400" />
              Launch Execution Job
            </h3>

            {/* Workload Radio Selection */}
            <div className="space-y-2">
              {WORKLOAD_OPTIONS.map((opt) => (
                <label
                  key={opt.id}
                  className={`block p-2.5 rounded-lg border cursor-pointer transition ${
                    workloadType === opt.id
                      ? 'bg-emerald-500/10 border-emerald-500/40 text-slate-100'
                      : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-start space-x-2">
                    <input
                      type="radio"
                      name="workloadType"
                      value={opt.id}
                      checked={workloadType === opt.id}
                      onChange={() => setWorkloadType(opt.id)}
                      className="mt-1 text-emerald-500 focus:ring-0 bg-slate-900 border-slate-700"
                    />
                    <div className="flex-1">
                      <div className="text-xs font-medium text-slate-200">{opt.label}</div>
                      <div className="text-[11px] text-slate-500 mt-0.5">{opt.description}</div>
                      <div className="text-[10px] font-mono text-emerald-400/80 mt-1">
                        $ {opt.defaultCommand}
                      </div>
                    </div>
                  </div>
                </label>
              ))}
            </div>

            {/* Custom Filter Arguments */}
            <div>
              <label className="block text-[11px] font-medium text-slate-400 mb-1">
                Optional Arguments (Server Whitelist Validated)
              </label>
              <input
                type="text"
                placeholder="e.g. -k test_api"
                value={customArgs}
                onChange={(e) => setCustomArgs(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 font-mono"
              />
            </div>

            {/* Timeout Selection */}
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Execution Timeout:</span>
              <div className="flex items-center space-x-2">
                {[15, 30, 60].map((sec) => (
                  <button
                    key={sec}
                    type="button"
                    onClick={() => setTimeoutSeconds(sec)}
                    className={`px-2 py-0.5 rounded text-xs font-mono transition ${
                      timeoutSeconds === sec
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                        : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {sec}s
                  </button>
                ))}
              </div>
            </div>

            {error && (
              <div className="p-2.5 bg-rose-950/40 border border-rose-800/50 rounded text-xs text-rose-300 flex items-start space-x-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting || (activeJob?.status === 'running' && isSubmitting)}
              className="w-full flex items-center justify-center space-x-2 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg shadow-lg shadow-emerald-950 transition cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Submitting Job...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-white" />
                  <span>Execute in Sandbox</span>
                </>
              )}
            </button>
          </form>

          {/* Recent Jobs List */}
          <div className="border-t border-slate-800 pt-3">
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Recent Execution Jobs ({recentJobs.length})
            </h4>

            {isLoadingJobs ? (
              <div className="py-6 text-center text-slate-500 text-xs">
                <Loader2 className="w-4 h-4 animate-spin mx-auto mb-1" />
                <span>Loading execution history...</span>
              </div>
            ) : recentJobs.length === 0 ? (
              <p className="text-xs text-slate-500 py-3 text-center">No sandbox runs executed yet.</p>
            ) : (
              <div className="space-y-1.5">
                {recentJobs.map((job) => (
                  <button
                    key={job.id}
                    onClick={() => setActiveJob(job)}
                    className={`w-full p-2 rounded-lg border text-left text-xs transition flex items-center justify-between ${
                      activeJob?.id === job.id
                        ? 'bg-slate-900 border-emerald-500/40 text-slate-200'
                        : 'bg-slate-950/50 border-slate-800 text-slate-400 hover:bg-slate-900'
                    }`}
                  >
                    <div>
                      <div className="font-mono text-slate-300 text-[11px] truncate">
                        {job.workload_type}
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        {new Date(job.created_at).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                          second: '2-digit',
                        })}
                        {job.duration_ms ? ` • ${job.duration_ms}ms` : ''}
                      </div>
                    </div>
                    <div>{getStatusBadge(job.status)}</div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Pane: Live Terminal Output & Metrics (7 cols) */}
        <div className="lg:col-span-7 flex flex-col h-full bg-[#05080e] overflow-hidden">
          {/* Terminal Header */}
          <div className="px-4 py-2.5 border-b border-slate-800 bg-[#090e17] flex items-center justify-between text-xs">
            <div className="flex items-center space-x-2">
              <Terminal className="w-4 h-4 text-emerald-400" />
              <span className="font-mono text-slate-300 text-xs">
                {activeJob ? `Job ${activeJob.id.slice(0, 8)}` : 'Terminal Output'}
              </span>
              {activeJob && getStatusBadge(activeJob.status)}
            </div>

            {activeJob && (
              <div className="flex items-center space-x-3 text-[11px] font-mono">
                {activeJob.exit_code !== null && activeJob.exit_code !== undefined && (
                  <span
                    className={`px-1.5 py-0.5 rounded ${
                      activeJob.exit_code === 0
                        ? 'bg-emerald-950 text-emerald-400'
                        : 'bg-rose-950 text-rose-400'
                    }`}
                  >
                    Exit Code: {activeJob.exit_code}
                  </span>
                )}
                {activeJob.duration_ms && (
                  <span className="text-slate-400">{activeJob.duration_ms} ms</span>
                )}
                <button
                  onClick={handleCopyLogs}
                  className="p-1 hover:text-emerald-400 text-slate-400 transition"
                  title="Copy terminal output"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
            )}
          </div>

          {/* Command Executed Bar */}
          {activeJob && (
            <div className="px-4 py-1.5 border-b border-slate-800/80 bg-slate-950/80 font-mono text-[11px] text-slate-400 truncate">
              <span className="text-emerald-500 font-bold">$ </span>
              {activeJob.command.join(' ')}
            </div>
          )}

          {/* Terminal Logs View */}
          <div className="flex-1 overflow-auto p-4 font-mono text-xs leading-relaxed select-text bg-[#03060a]">
            {activeJob ? (
              <div className="space-y-2">
                {activeJob.stdout && (
                  <div className="text-slate-200 whitespace-pre-wrap">{activeJob.stdout}</div>
                )}
                {activeJob.stderr && (
                  <div className="text-rose-400 whitespace-pre-wrap">{activeJob.stderr}</div>
                )}
                {activeJob.error_message && (
                  <div className="p-3 bg-rose-950/30 border border-rose-800/40 rounded text-rose-300 text-xs">
                    {activeJob.error_message}
                  </div>
                )}
                {!activeJob.stdout && !activeJob.stderr && !activeJob.error_message && (
                  <div className="text-slate-500 italic py-8 text-center">
                    {activeJob.status === 'running' || activeJob.status === 'queued'
                      ? 'Process running inside disposable container sandbox...'
                      : 'No output generated by this job.'}
                  </div>
                )}
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-slate-500 space-y-2">
                <Terminal className="w-8 h-8 text-slate-600 mb-1" />
                <p>Select a workload and click "Execute in Sandbox" to run tests.</p>
                <p className="text-[11px] text-slate-600">
                  Container sandboxes auto-destroy on exit, protecting the host system.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
