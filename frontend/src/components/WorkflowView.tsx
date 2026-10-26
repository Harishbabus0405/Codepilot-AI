import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import type { WorkflowRun } from '../types/project';
import {
  Play,
  Loader2,
  CheckCircle2,
  AlertCircle,
  GitBranch,
  Layers,
  ShieldCheck,
  RotateCw,
  ListTodo,
  FileCode,
  FileText,
  ShieldAlert,
  CheckSquare,
  FolderGit2,
} from 'lucide-react';

interface WorkflowViewProps {
  projectId: string;
}

export const WorkflowView: React.FC<WorkflowViewProps> = ({ projectId }) => {
  const [workflow, setWorkflow] = useState<WorkflowRun | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pipelineType, setPipelineType] = useState<'full' | 'planning' | 'qa' | 'docs'>('full');
  const [activeTab, setActiveTab] = useState<
    | 'plan'
    | 'repo'
    | 'architecture'
    | 'validation'
    | 'developer'
    | 'qa'
    | 'security'
    | 'code_review'
    | 'documentation'
  >('plan');

  const fetchWorkflow = useCallback(async () => {
    try {
      const data = await api.getLatestProjectWorkflow(projectId);
      setWorkflow(data);
      setError(null);
      return data;
    } catch {
      setWorkflow(null);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchWorkflow();
  }, [fetchWorkflow]);

  useEffect(() => {
    if (!workflow || (workflow.status !== 'running' && workflow.status !== 'pending')) {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const updated = await api.getProjectWorkflowStatus(projectId);
        setWorkflow(updated);
        if (updated.status === 'completed' || updated.status === 'failed') {
          clearInterval(interval);
        }
      } catch {
        // Keep polling
      }
    }, 2500);

    return () => clearInterval(interval);
  }, [workflow?.status, projectId]);

  const handleStartWorkflow = async () => {
    setIsStarting(true);
    setError(null);
    try {
      await api.startProjectWorkflow(projectId, { pipeline_type: pipelineType });
      await fetchWorkflow();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to launch workflow.');
    } finally {
      setIsStarting(false);
    }
  };

  const stages = [
    { id: 'supervisor', label: 'Supervisor', desc: 'Coordination & Routing' },
    { id: 'planner', label: 'Planner Agent', desc: 'Task Decomposition' },
    { id: 'repo_understanding', label: 'Repo Agent', desc: 'Code Context & Deps' },
    { id: 'architect', label: 'Architect Agent', desc: 'System & Schema Design' },
    { id: 'validator', label: 'Validator Node', desc: 'Requirements Audit' },
    { id: 'developer', label: 'Developer Agent', desc: 'Code Generation' },
    { id: 'qa', label: 'QA Agent', desc: 'Test Suites' },
    { id: 'security', label: 'Security Agent', desc: 'Security Audit' },
    { id: 'code_review', label: 'Review Agent', desc: 'Quality Review' },
    { id: 'documentation', label: 'Docs Agent', desc: 'README & Report' },
  ];

  return (
    <div className="mt-6 p-6 rounded-xl bg-[#090e17] border border-slate-800 text-slate-100 space-y-6">
      {/* Header and Trigger Action */}
      <div className="flex items-center justify-between flex-wrap gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <GitBranch className="w-4 h-4 text-emerald-400" />
            <h3 className="text-base font-semibold text-white tracking-tight">
              LangGraph Multi-Agent Orchestration
            </h3>
          </div>
          <p className="text-xs text-slate-400">
            Coordinated autonomous workflow across all 8 specialized agents with conditional routing and bounded retries.
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-slate-400">Pipeline:</span>
            <select
              value={pipelineType}
              onChange={(e) => setPipelineType(e.target.value as any)}
              disabled={workflow?.status === 'running' || workflow?.status === 'pending'}
              className="bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded px-2.5 py-1.5 focus:outline-none focus:border-emerald-500 font-mono"
            >
              <option value="full">Full Engineering Pipeline (8 Agents)</option>
              <option value="planning">Planning & Architecture Only</option>
              <option value="qa">QA & Security Audit Only</option>
              <option value="docs">Documentation Only</option>
            </select>
          </div>

          {workflow && (
            <span
              className={`px-2.5 py-1 rounded-full text-xs font-mono font-medium flex items-center gap-1.5 ${
                workflow.status === 'completed'
                  ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-500/30'
                  : workflow.status === 'running' || workflow.status === 'pending'
                  ? 'bg-sky-950/60 text-sky-300 border border-sky-500/30 animate-pulse'
                  : 'bg-rose-950/60 text-rose-300 border border-rose-500/30'
              }`}
            >
              {(workflow.status === 'running' || workflow.status === 'pending') && (
                <Loader2 className="w-3 h-3 animate-spin" />
              )}
              {workflow.status === 'completed' && <CheckCircle2 className="w-3 h-3" />}
              {workflow.status === 'failed' && <AlertCircle className="w-3 h-3" />}
              <span>{workflow.status.toUpperCase()}</span>
            </span>
          )}

          <button
            onClick={handleStartWorkflow}
            disabled={isStarting || workflow?.status === 'running' || workflow?.status === 'pending'}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-medium transition-all shadow-md cursor-pointer"
          >
            {isStarting ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Launching...</span>
              </>
            ) : workflow?.status === 'running' || workflow?.status === 'pending' ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-300" />
                <span>Orchestrating...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Run Agent Pipeline</span>
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3.5 rounded-lg bg-rose-950/30 border border-rose-500/30 text-rose-200 text-xs flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {isLoading ? (
        <div className="py-12 flex flex-col items-center justify-center text-slate-400">
          <Loader2 className="w-6 h-6 animate-spin text-emerald-400 mb-2" />
          <p className="text-xs font-mono">Loading workflow status from PostgreSQL...</p>
        </div>
      ) : !workflow ? (
        <div className="text-center py-12 px-4 rounded-lg border border-dashed border-slate-800 bg-[#070b14]/50">
          <Layers className="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <h4 className="text-sm font-semibold text-slate-300">No Multi-Agent Execution Yet</h4>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
            Click &quot;Run Agent Pipeline&quot; to execute the coordinated workflow across all 8 specialized agents.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Stage Progression Visualizer */}
          <div className="grid grid-cols-2 sm:grid-cols-5 lg:grid-cols-5 gap-2.5">
            {stages.map((stage) => {
              const isCompleted = workflow.completed_stages?.includes(stage.id);
              const isCurrent = workflow.current_stage === stage.id && workflow.status === 'running';
              const isFailed = workflow.current_stage === stage.id && workflow.status === 'failed';

              return (
                <div
                  key={stage.id}
                  className={`p-3 rounded-lg border text-left transition-all ${
                    isCompleted
                      ? 'bg-emerald-950/20 border-emerald-500/30 text-slate-200'
                      : isCurrent
                      ? 'bg-sky-950/30 border-sky-500/50 text-white ring-1 ring-sky-500/30'
                      : isFailed
                      ? 'bg-rose-950/20 border-rose-500/40 text-rose-200'
                      : 'bg-[#070b14] border-slate-800/80 text-slate-500 opacity-60'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-[10px] text-slate-400 uppercase tracking-wider">
                      {stage.label}
                    </span>
                    {isCompleted && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
                    {isCurrent && <Loader2 className="w-3.5 h-3.5 animate-spin text-sky-400" />}
                    {isFailed && <AlertCircle className="w-3.5 h-3.5 text-rose-400" />}
                  </div>
                  <p className="text-xs font-semibold text-slate-200 truncate">
                    {stage.desc}
                  </p>
                  <span className="text-[10px] font-mono mt-1 block text-slate-500">
                    {isCompleted ? 'Finished' : isCurrent ? 'Active Execution' : isFailed ? 'Failed' : 'Pending'}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Error Message & Retry Counter */}
          {workflow.error_message && (
            <div className="p-3.5 rounded-lg bg-rose-950/30 border border-rose-500/30 text-rose-200 text-xs flex items-start justify-between gap-4">
              <div className="flex items-start gap-2.5">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold text-rose-200">Workflow Error Encountered</p>
                  <p className="text-rose-300/80 mt-0.5">{workflow.error_message}</p>
                  {workflow.error_message.includes('RateLimit') && (
                    <p className="text-[11px] text-amber-300/90 mt-1">
                      AI provider rate limit reached. Built-in exponential backoff has been enhanced with automatic retry and rate-limit cooldown.
                    </p>
                  )}
                  {workflow.retry_count > 0 && (
                    <p className="text-[11px] font-mono text-slate-400 mt-1 flex items-center gap-1">
                      <RotateCw className="w-3 h-3" />
                      Retries attempted: {workflow.retry_count}
                    </p>
                  )}
                </div>
              </div>
              <button
                onClick={handleStartWorkflow}
                disabled={isStarting}
                className="px-3 py-1.5 rounded-lg bg-rose-900/60 hover:bg-rose-800 text-rose-200 border border-rose-700/50 text-xs font-medium flex items-center gap-1.5 shrink-0 transition-colors shadow-sm cursor-pointer disabled:opacity-50"
              >
                <RotateCw className={`w-3.5 h-3.5 ${isStarting ? 'animate-spin' : ''}`} />
                <span>Retry Workflow</span>
              </button>
            </div>
          )}

          {/* Stage Outputs Tabs */}
          <div className="pt-2">
            {/* Tab Navigation */}
            <div className="flex items-center gap-2 border-b border-slate-800 pb-2 mb-4 overflow-x-auto">
              <button
                onClick={() => setActiveTab('plan')}
                disabled={!workflow.plan_output}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
                  activeTab === 'plan'
                    ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                    : 'text-slate-400 hover:text-slate-200 disabled:opacity-40'
                }`}
              >
                <ListTodo className="w-3.5 h-3.5" />
                <span>1. Plan</span>
                {workflow.plan_output?.tasks && (
                  <span className="px-1.5 py-0.2 rounded-full bg-slate-800 text-[10px] font-mono">
                    {workflow.plan_output.tasks.length}
                  </span>
                )}
              </button>

              <button
                onClick={() => setActiveTab('repo')}
                disabled={!workflow.repo_understanding_output}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
                  activeTab === 'repo'
                    ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                    : 'text-slate-400 hover:text-slate-200 disabled:opacity-40'
                }`}
              >
                <FolderGit2 className="w-3.5 h-3.5" />
                <span>2. Repo Context</span>
                {workflow.repo_understanding_output?.evidence_snippets && (
                  <span className="px-1.5 py-0.2 rounded-full bg-slate-800 text-[10px] font-mono">
                    {workflow.repo_understanding_output.evidence_snippets.length}
                  </span>
                )}
              </button>

              <button
                onClick={() => setActiveTab('architecture')}
                disabled={!workflow.architecture_output}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
                  activeTab === 'architecture'
                    ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                    : 'text-slate-400 hover:text-slate-200 disabled:opacity-40'
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
                <span>3. Architecture</span>
              </button>

              <button
                onClick={() => setActiveTab('validation')}
                disabled={!workflow.validation_output}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
                  activeTab === 'validation'
                    ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                    : 'text-slate-400 hover:text-slate-200 disabled:opacity-40'
                }`}
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Audit</span>
                {workflow.validation_output && (
                  <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-emerald-950 text-emerald-400">
                    {workflow.validation_output.score}/100
                  </span>
                )}
              </button>

              <button
                onClick={() => setActiveTab('developer')}
                disabled={!workflow.developer_output}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
                  activeTab === 'developer'
                    ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                    : 'text-slate-400 hover:text-slate-200 disabled:opacity-40'
                }`}
              >
                <FileCode className="w-3.5 h-3.5" />
                <span>4. Developer</span>
                {workflow.developer_output?.total_files && (
                  <span className="px-1.5 py-0.2 rounded-full bg-slate-800 text-[10px] font-mono">
                    {workflow.developer_output.total_files} files
                  </span>
                )}
              </button>

              <button
                onClick={() => setActiveTab('qa')}
                disabled={!workflow.qa_output}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
                  activeTab === 'qa'
                    ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                    : 'text-slate-400 hover:text-slate-200 disabled:opacity-40'
                }`}
              >
                <CheckSquare className="w-3.5 h-3.5" />
                <span>5. QA Tests</span>
              </button>

              <button
                onClick={() => setActiveTab('security')}
                disabled={!workflow.security_output}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
                  activeTab === 'security'
                    ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                    : 'text-slate-400 hover:text-slate-200 disabled:opacity-40'
                }`}
              >
                <ShieldAlert className="w-3.5 h-3.5" />
                <span>6. Security</span>
                {workflow.security_output && (
                  <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-emerald-950 text-emerald-400">
                    {workflow.security_output.security_score}/100
                  </span>
                )}
              </button>

              <button
                onClick={() => setActiveTab('code_review')}
                disabled={!workflow.code_review_output}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
                  activeTab === 'code_review'
                    ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                    : 'text-slate-400 hover:text-slate-200 disabled:opacity-40'
                }`}
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>7. Review</span>
              </button>

              <button
                onClick={() => setActiveTab('documentation')}
                disabled={!workflow.documentation_output}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
                  activeTab === 'documentation'
                    ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                    : 'text-slate-400 hover:text-slate-200 disabled:opacity-40'
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>8. Documentation</span>
              </button>
            </div>

            {/* Tab Content: Planner Output */}
            {activeTab === 'plan' && workflow.plan_output && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div className="p-3 rounded-lg bg-[#070b14] border border-slate-800 text-xs text-slate-300">
                  <span className="font-mono text-emerald-400 font-semibold block mb-1">
                    Execution Strategy:
                  </span>
                  {workflow.plan_output.execution_strategy}
                </div>

                <div className="space-y-2.5">
                  {workflow.plan_output.tasks.map((task) => (
                    <div
                      key={task.id}
                      className="p-3.5 rounded-lg bg-[#070b14] border border-slate-800/80 space-y-2"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2">
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-slate-800 text-slate-300">
                            {task.id}
                          </span>
                          <h4 className="text-xs font-semibold text-white">
                            {task.title}
                          </h4>
                        </div>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
                            task.estimated_complexity === 'High'
                              ? 'bg-rose-950 text-rose-300 border border-rose-500/30'
                              : task.estimated_complexity === 'Medium'
                              ? 'bg-amber-950 text-amber-300 border border-amber-500/30'
                              : 'bg-emerald-950 text-emerald-300 border border-emerald-500/30'
                          }`}
                        >
                          {task.estimated_complexity}
                        </span>
                      </div>

                      <p className="text-xs text-slate-400 leading-relaxed">
                        {task.description}
                      </p>

                      {task.acceptance_criteria?.length > 0 && (
                        <div className="pt-1.5 border-t border-slate-800/60 text-[11px] text-slate-400">
                          <span className="font-mono text-slate-500 block mb-1">
                            Acceptance Criteria:
                          </span>
                          <ul className="list-disc list-inside space-y-0.5">
                            {task.acceptance_criteria.map((c, i) => (
                              <li key={i}>{c}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tab Content: Repository Understanding Output */}
            {activeTab === 'repo' && workflow.repo_understanding_output && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div className="p-4 rounded-lg bg-[#070b14] border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-emerald-400 font-semibold uppercase">
                      Repository Context & Evidence
                    </span>
                    {workflow.repo_understanding_output.indexing_status && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-300 border border-slate-700">
                        Status: {workflow.repo_understanding_output.indexing_status}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {workflow.repo_understanding_output.summary}
                  </p>
                  {workflow.repo_understanding_output.relevant_modules?.length > 0 && (
                    <div className="flex items-center gap-1.5 flex-wrap pt-1">
                      <span className="text-[11px] text-slate-500 font-mono">Modules Detected:</span>
                      {workflow.repo_understanding_output.relevant_modules.map((mod: string, i: number) => (
                        <span key={i} className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[11px] font-mono">
                          {mod}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {workflow.repo_understanding_output.evidence_snippets?.length > 0 ? (
                  <div className="space-y-3">
                    <h4 className="text-xs font-mono font-semibold text-slate-400 uppercase">
                      Retrieved Code Evidence ({workflow.repo_understanding_output.evidence_snippets.length} chunks)
                    </h4>
                    {workflow.repo_understanding_output.evidence_snippets.map((snip: any, idx: number) => (
                      <div key={idx} className="p-3.5 rounded-lg bg-[#070b14] border border-slate-800 text-xs font-mono">
                        <div className="flex items-center justify-between text-slate-400 mb-2">
                          <span className="text-emerald-400 font-medium">{snip.file_path}</span>
                          <span className="text-[10px] text-slate-500 font-mono">{snip.line_range}</span>
                        </div>
                        <pre className="text-slate-300 overflow-x-auto text-[11px] bg-slate-950/70 p-2.5 rounded border border-slate-800/80 leading-relaxed">
                          {snip.snippet}
                        </pre>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-4 rounded-lg bg-[#070b14] border border-slate-800 text-xs text-slate-400 text-center">
                    No relevant code chunks matching this task were retrieved from the repository index.
                  </div>
                )}
              </div>
            )}

            {/* Tab Content: Architecture Output */}
            {activeTab === 'architecture' && workflow.architecture_output && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-mono text-slate-500 uppercase">Pattern:</span>
                  <span className="px-2.5 py-0.5 rounded font-mono font-medium bg-emerald-950/60 text-emerald-400 border border-emerald-500/30">
                    {workflow.architecture_output.system_pattern}
                  </span>
                </div>

                <div>
                  <h4 className="text-xs font-mono font-semibold text-slate-400 mb-2 uppercase">
                    Components
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                    {workflow.architecture_output.components.map((c, i) => (
                      <div key={i} className="p-3 rounded-lg bg-[#070b14] border border-slate-800">
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span className="font-semibold text-white">{c.name}</span>
                          <span className="text-[10px] font-mono text-emerald-400">{c.type}</span>
                        </div>
                        <p className="text-xs text-slate-400 leading-relaxed mb-2">{c.responsibilities}</p>
                        <div className="flex flex-wrap gap-1">
                          {c.technologies.map((t, idx) => (
                            <span key={idx} className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] font-mono text-slate-300">
                              {t}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="text-xs font-mono font-semibold text-slate-400 mb-2 uppercase">
                    API Boundaries
                  </h4>
                  <div className="overflow-x-auto rounded-lg border border-slate-800">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-[#070b14] border-b border-slate-800 text-slate-400 font-mono text-[11px]">
                        <tr>
                          <th className="p-2.5">Method</th>
                          <th className="p-2.5">Endpoint</th>
                          <th className="p-2.5">Description</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 bg-[#070b14]/50">
                        {workflow.architecture_output.api_boundaries.map((apiItem, idx) => (
                          <tr key={idx}>
                            <td className="p-2.5 font-mono font-medium text-emerald-400">{apiItem.method}</td>
                            <td className="p-2.5 font-mono text-slate-200">{apiItem.endpoint}</td>
                            <td className="p-2.5 text-slate-400">{apiItem.description}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* Tab Content: Validation Output */}
            {activeTab === 'validation' && workflow.validation_output && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div className="p-4 rounded-lg bg-[#070b14] border border-slate-800 flex items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-mono uppercase text-slate-400">Coverage Score</span>
                      <span className="text-lg font-bold text-emerald-400 font-mono">
                        {workflow.validation_output.score} / 100
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed">
                      {workflow.validation_output.coverage_summary}
                    </p>
                  </div>

                  <div className="shrink-0">
                    {workflow.validation_output.is_valid ? (
                      <span className="px-3 py-1.5 rounded-lg text-xs font-medium font-mono bg-emerald-950/60 text-emerald-300 border border-emerald-500/30">
                        ✓ VALIDATED
                      </span>
                    ) : (
                      <span className="px-3 py-1.5 rounded-lg text-xs font-medium font-mono bg-amber-950/60 text-amber-300 border border-amber-500/30">
                        ⚠ ISSUES FLAGGED
                      </span>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Tab Content: Developer Output */}
            {activeTab === 'developer' && workflow.developer_output && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div className="p-3 rounded-lg bg-[#070b14] border border-slate-800 text-xs text-slate-300 flex items-center justify-between">
                  <span>Generated {workflow.developer_output.total_files} workspace files</span>
                  <span className="font-mono text-emerald-400">Status: {workflow.developer_output.status}</span>
                </div>
                <div className="space-y-1">
                  {(workflow.developer_output.files || []).map((f: string, idx: number) => (
                    <div key={idx} className="p-2 rounded bg-slate-900 border border-slate-800 text-xs font-mono text-slate-300 flex items-center gap-2">
                      <FileCode className="w-3.5 h-3.5 text-emerald-400" />
                      <span>{f}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tab Content: QA Output */}
            {activeTab === 'qa' && workflow.qa_output && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div className="p-3 rounded-lg bg-[#070b14] border border-slate-800 text-xs text-slate-300">
                  <span className="font-semibold text-emerald-400 block mb-1">Generated Test Suite:</span>
                  <p className="font-mono text-slate-400">{workflow.qa_output.test_file_path}</p>
                </div>
                <div className="space-y-2">
                  {(workflow.qa_output.test_plan || []).map((t: any, idx: number) => (
                    <div key={idx} className="p-3 rounded-lg bg-[#070b14] border border-slate-800 text-xs space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-medium text-emerald-400">{t.id}</span>
                        <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 uppercase font-mono">{t.category}</span>
                      </div>
                      <p className="text-slate-300">{t.description}</p>
                      <span className="text-[11px] font-mono text-slate-500">Target: {t.target}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tab Content: Security Output */}
            {activeTab === 'security' && workflow.security_output && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div className="p-4 rounded-lg bg-[#070b14] border border-slate-800 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-mono uppercase text-slate-400">Security Score</span>
                    <span className="text-lg font-bold text-emerald-400 font-mono block">
                      {workflow.security_output.security_score} / 100
                    </span>
                  </div>
                  <span className={`px-2.5 py-1 rounded text-xs font-mono uppercase ${workflow.security_output.status === 'passed' ? 'bg-emerald-950 text-emerald-300 border border-emerald-500/30' : 'bg-amber-950 text-amber-300 border border-amber-500/30'}`}>
                    {workflow.security_output.status}
                  </span>
                </div>
                {(workflow.security_output.findings || []).map((f: any, idx: number) => (
                  <div key={idx} className="p-3 rounded-lg bg-[#070b14] border border-slate-800 text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-white">{f.title}</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-rose-950 text-rose-300 border border-rose-500/30">{f.severity}</span>
                    </div>
                    <p className="text-slate-400">{f.description}</p>
                    <p className="text-emerald-400 font-mono text-[11px]">Fix: {f.recommendation}</p>
                  </div>
                ))}
              </div>
            )}

            {/* Tab Content: Code Review Output */}
            {activeTab === 'code_review' && workflow.code_review_output && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div className="p-4 rounded-lg bg-[#070b14] border border-slate-800 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-mono uppercase text-slate-400">Review Quality Score</span>
                    <span className="text-lg font-bold text-emerald-400 font-mono block">
                      {workflow.code_review_output.score} / 100
                    </span>
                  </div>
                  <span className="px-2.5 py-1 rounded text-xs font-mono uppercase bg-emerald-950 text-emerald-300 border border-emerald-500/30">
                    {workflow.code_review_output.status}
                  </span>
                </div>
                <p className="text-xs text-slate-400">{workflow.code_review_output.summary}</p>
                {(workflow.code_review_output.comments || []).map((c: any, idx: number) => (
                  <div key={idx} className="p-3 rounded-lg bg-[#070b14] border border-slate-800 text-xs space-y-1">
                    <span className="font-mono text-slate-400">{c.file_path}:{c.line_number} [{c.type}]</span>
                    <p className="text-slate-200">{c.comment}</p>
                  </div>
                ))}
              </div>
            )}

            {/* Tab Content: Documentation Output (Phase G) */}
            {activeTab === 'documentation' && workflow.documentation_output && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div className="p-4 rounded-lg bg-[#070b14] border border-slate-800 text-xs space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                    <span className="font-semibold text-emerald-400">Engineering Implementation Report</span>
                    <span className="font-mono text-[10px] text-slate-400">Phase G Output</span>
                  </div>
                  <pre className="font-mono text-xs text-slate-300 whitespace-pre-wrap max-h-96 overflow-y-auto p-3 bg-slate-950/70 rounded border border-slate-800/80">
                    {workflow.documentation_output.engineering_report}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
