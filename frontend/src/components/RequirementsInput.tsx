import React, { useState, useEffect, useCallback } from 'react';
import {
  Loader2,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  BrainCircuit,
  Sparkles,
  GitBranch,
  RotateCw,
  Plus,
  Play,
  FolderGit2,
} from 'lucide-react';
import { api } from '../services/api';
import type {
  ImportedRepository,
  Project,
  RequirementsAnalysis,
} from '../types/project';
import { AnalysisPanel } from './AnalysisPanel';
import { ImportRepositoryModal } from './ImportRepositoryModal';

interface RequirementsInputProps {
  onCreateProject: (
    requirements: string,
    name?: string,
    repoId?: string,
    branch?: string
  ) => Promise<Project | null>;
  onAnalyzeRequirements: (
    requirements: string,
    name?: string
  ) => Promise<RequirementsAnalysis | null>;
  onStartWorkflow?: (project: Project, repoId?: string) => Promise<void>;
  isSubmitting: boolean;
  isAnalyzing: boolean;
  onViewProjectDetails?: (project: Project) => void;
  onOpenProjectWorkflow?: (project: Project) => void;
}

const EXAMPLE_TASKS = [
  'Add JWT authentication to the existing FastAPI backend.',
  'Fix the login validation bug and return descriptive error payloads.',
  'Add pagination with limit and offset to the existing users API.',
  'Generate tests for the payment and checkout service.',
  'Explain how authentication and authorization work in this repository.',
];

export const RequirementsInput: React.FC<RequirementsInputProps> = ({
  onCreateProject,
  onAnalyzeRequirements,
  onStartWorkflow,
  isSubmitting,
  isAnalyzing,
  onViewProjectDetails,
  onOpenProjectWorkflow,
}) => {
  // Mode selection: 'new_project' vs 'existing_repo'
  const [activeMode, setActiveMode] = useState<'new_project' | 'existing_repo'>('new_project');

  // New Project Form State
  const [projectName, setProjectName] = useState('');
  const [requirements, setRequirements] = useState('');

  // Existing Repository State
  const [repositories, setRepositories] = useState<ImportedRepository[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string | null>(null);
  const [selectedBranch, setSelectedBranch] = useState<string>('main');
  const [engineeringTask, setEngineeringTask] = useState('');
  const [isLoadingRepos, setIsLoadingRepos] = useState(false);
  const [repoLoadError, setRepoLoadError] = useState<string | null>(null);
  const [isReindexing, setIsReindexing] = useState(false);

  // Import Modal State
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);

  // Workflow launch State
  const [isStartingWorkflow, setIsStartingWorkflow] = useState(false);

  // Common UI states
  const [validationError, setValidationError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [createdProject, setCreatedProject] = useState<Project | null>(null);
  const [analysis, setAnalysis] = useState<RequirementsAnalysis | null>(null);

  // Load repositories from backend
  const loadRepositories = useCallback(async () => {
    setIsLoadingRepos(true);
    setRepoLoadError(null);
    try {
      const data = await api.getRepositories();
      setRepositories(data);
      if (data.length > 0 && !selectedRepoId) {
        setSelectedRepoId(data[0].id);
        setSelectedBranch(data[0].default_branch || 'main');
      }
    } catch (err) {
      setRepoLoadError(
        err instanceof Error ? err.message : 'Failed to retrieve imported repositories.'
      );
    } finally {
      setIsLoadingRepos(false);
    }
  }, [selectedRepoId]);

  useEffect(() => {
    loadRepositories();
  }, [loadRepositories]);

  // Selected Repository object
  const selectedRepo = repositories.find((r) => r.id === selectedRepoId) || null;

  // Sync selected branch when selectedRepo changes
  useEffect(() => {
    if (selectedRepo) {
      setSelectedBranch(selectedRepo.default_branch || 'main');
    }
  }, [selectedRepoId, selectedRepo]);

  // Periodic polling for selected repo if status is 'indexing' or 'pending'
  useEffect(() => {
    if (
      selectedRepo &&
      (selectedRepo.status === 'indexing' ||
        selectedRepo.status === 'pending' ||
        selectedRepo.status === 'importing')
    ) {
      const interval = setInterval(async () => {
        try {
          const updated = await api.getRepositoryStatus(selectedRepo.id);
          setRepositories((prev) =>
            prev.map((r) => (r.id === updated.id ? { ...r, ...updated } : r))
          );
        } catch {
          // Ignore polling errors
        }
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [selectedRepo]);

  // Handle re-index action
  const handleReindex = async () => {
    if (!selectedRepo) return;
    setIsReindexing(true);
    try {
      const updated = await api.reindexRepository(selectedRepo.id);
      setRepositories((prev) =>
        prev.map((r) => (r.id === updated.id ? { ...r, ...updated } : r))
      );
    } catch (err) {
      setApiError(err instanceof Error ? err.message : 'Reindexing failed.');
    } finally {
      setIsReindexing(false);
    }
  };

  // MODE A: Handle New Project Creation
  const handleCreateNewProjectSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);
    setApiError(null);
    setCreatedProject(null);

    const trimmedReqs = requirements.trim();
    if (!trimmedReqs) {
      setValidationError('Please provide software requirements before creating a project.');
      return;
    }

    try {
      const newProj = await onCreateProject(trimmedReqs, projectName.trim() || undefined);
      if (newProj) {
        setCreatedProject(newProj);
        setRequirements('');
        setProjectName('');
      }
    } catch (err) {
      setApiError(err instanceof Error ? err.message : 'An error occurred while creating the project.');
    }
  };

  // MODE A: Handle New Project AI Requirements Analysis
  const handleAnalyzeNewProjectClick = async () => {
    setValidationError(null);
    setAnalysisError(null);

    const trimmedReqs = requirements.trim();
    if (!trimmedReqs || trimmedReqs.length < 10) {
      setValidationError('Please enter at least 10 characters of software requirements to analyze.');
      return;
    }

    try {
      const result = await onAnalyzeRequirements(trimmedReqs, projectName.trim() || undefined);
      if (result) {
        setAnalysis(result);
      }
    } catch (err) {
      setAnalysisError(err instanceof Error ? err.message : 'Failed to analyze requirements.');
    }
  };

  // MODE B: Handle Analyze Task for Existing Repository
  const handleAnalyzeTaskClick = async () => {
    setValidationError(null);
    setAnalysisError(null);

    if (!selectedRepo) {
      setValidationError('Please select an imported GitHub repository first.');
      return;
    }

    const trimmedTask = engineeringTask.trim();
    if (!trimmedTask || trimmedTask.length < 10) {
      setValidationError('Please enter at least 10 characters for the engineering task.');
      return;
    }

    try {
      const result = await onAnalyzeRequirements(
        `[Repository: ${selectedRepo.name} (${selectedBranch})]\n\n${trimmedTask}`,
        `${selectedRepo.name}: ${trimmedTask.slice(0, 40)}`
      );
      if (result) {
        setAnalysis(result);
      }
    } catch (err) {
      setAnalysisError(err instanceof Error ? err.message : 'Failed to analyze engineering task.');
    }
  };

  // MODE B: Handle Start Engineering Workflow
  const handleStartWorkflowClick = async () => {
    setValidationError(null);
    setApiError(null);

    if (!selectedRepo) {
      setValidationError('Please select an imported GitHub repository.');
      return;
    }

    if (selectedRepo.status !== 'ready') {
      setValidationError(
        `Repository indexing status is '${selectedRepo.status}'. Engineering workflow requires an indexed repository to retrieve code context.`
      );
      return;
    }

    const trimmedTask = engineeringTask.trim();
    if (!trimmedTask) {
      setValidationError('Please enter an engineering task to execute against this repository.');
      return;
    }

    setIsStartingWorkflow(true);
    try {
      // 1. Create a dedicated project linked directly to the repository
      const projTitle = `${selectedRepo.name}: ${trimmedTask.split('\n')[0].slice(0, 50).trim()}`;
      const project = await onCreateProject(
        trimmedTask,
        projTitle,
        selectedRepo.id,
        selectedBranch
      );

      if (!project) {
        throw new Error('Project initialization returned null.');
      }

      // 2. Start the LangGraph multi-agent workflow
      if (onStartWorkflow) {
        await onStartWorkflow(project, selectedRepo.id);
      } else {
        await api.startProjectWorkflow(project.id, {
          pipeline_type: 'full',
          repo_id: selectedRepo.id,
        });
      }

      // 3. Open the workflow view for this project
      if (onOpenProjectWorkflow) {
        onOpenProjectWorkflow(project);
      } else if (onViewProjectDetails) {
        onViewProjectDetails(project);
      }
    } catch (err) {
      setApiError(
        err instanceof Error ? err.message : 'Failed to launch multi-agent engineering workflow.'
      );
    } finally {
      setIsStartingWorkflow(false);
    }
  };

  // Save Analysis as a project
  const handleSaveAnalysisAsProject = async () => {
    if (!analysis) return;
    const isRepoMode = activeMode === 'existing_repo' && selectedRepo;
    const trimmedReqs = isRepoMode
      ? engineeringTask.trim() || analysis.project_summary
      : requirements.trim() || analysis.project_summary;
    const name = isRepoMode
      ? `${selectedRepo.name}: ${trimmedReqs.split('\n')[0].slice(0, 40)}`
      : projectName.trim() || undefined;

    try {
      const newProj = await onCreateProject(
        trimmedReqs,
        name,
        isRepoMode ? selectedRepo.id : undefined,
        isRepoMode ? selectedBranch : undefined
      );
      if (newProj) {
        setCreatedProject(newProj);
        setAnalysis(null);
      }
    } catch (err) {
      setApiError(err instanceof Error ? err.message : 'Failed to save project from analysis.');
    }
  };

  return (
    <div className="bg-[#0e1626] border border-slate-800/80 rounded-xl p-6 sm:p-8 shadow-xl">
      {/* Welcome Heading */}
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight flex items-center gap-3">
          <span>Welcome to CodePilot AI</span>
        </h1>
        <p className="text-slate-400 mt-1.5 text-sm leading-relaxed max-w-2xl">
          Multi-agent software engineering assistant. Turn natural-language requirements into architectures,
          or submit engineering tasks directly against existing GitHub repositories.
        </p>
      </div>

      {/* Workspace Selection Section: MODE A vs MODE B */}
      <div className="mb-6 p-1.5 rounded-xl bg-[#090e17] border border-slate-800 flex flex-col sm:flex-row gap-2">
        <button
          type="button"
          onClick={() => {
            setActiveMode('new_project');
            setValidationError(null);
            setApiError(null);
          }}
          className={`flex-1 flex items-center justify-center gap-2.5 px-4 py-3 rounded-lg text-xs font-mono font-medium transition-all cursor-pointer ${
            activeMode === 'new_project'
              ? 'bg-slate-800 text-white border border-slate-700 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
          }`}
        >
          <Sparkles
            className={`w-4 h-4 ${
              activeMode === 'new_project' ? 'text-emerald-400' : 'text-slate-500'
            }`}
          />
          <div className="text-left font-sans">
            <div className="font-semibold text-sm">Mode A: New Project</div>
            <div className="text-[11px] text-slate-400 font-normal">
              Create project from plain-language requirements
            </div>
          </div>
        </button>

        <button
          type="button"
          onClick={() => {
            setActiveMode('existing_repo');
            setValidationError(null);
            setApiError(null);
          }}
          className={`flex-1 flex items-center justify-center gap-2.5 px-4 py-3 rounded-lg text-xs font-mono font-medium transition-all cursor-pointer ${
            activeMode === 'existing_repo'
              ? 'bg-slate-800 text-white border border-slate-700 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
          }`}
        >
          <FolderGit2
            className={`w-4 h-4 ${
              activeMode === 'existing_repo' ? 'text-emerald-400' : 'text-slate-500'
            }`}
          />
          <div className="text-left font-sans">
            <div className="font-semibold text-sm">Mode B: Existing Repository</div>
            <div className="text-[11px] text-slate-400 font-normal">
              Work directly on an imported GitHub codebase
            </div>
          </div>
        </button>
      </div>

      {/* Success Notification */}
      {createdProject && (
        <div className="mb-6 p-4 rounded-lg bg-emerald-950/40 border border-emerald-500/30 text-emerald-200 flex items-start justify-between gap-4 animate-in fade-in duration-200">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-white text-sm">
                Project Created Successfully
              </p>
              <p className="text-xs text-emerald-300/90 mt-0.5">
                <span className="font-medium text-emerald-200">{createdProject.name}</span> has
                been saved to the PostgreSQL database with status{' '}
                <span className="font-mono uppercase bg-emerald-900/60 px-1 py-0.5 rounded text-[10px]">
                  {createdProject.status}
                </span>.
              </p>
              <p className="text-[11px] text-slate-400 font-mono mt-1">
                ID: {createdProject.id}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {onViewProjectDetails && (
              <button
                type="button"
                onClick={() => onViewProjectDetails(createdProject)}
                className="text-xs font-medium text-emerald-400 hover:text-emerald-300 underline underline-offset-4 cursor-pointer"
              >
                View Details
              </button>
            )}
            <button
              type="button"
              onClick={() => setCreatedProject(null)}
              className="text-slate-400 hover:text-slate-200 text-xs px-2 py-1 rounded cursor-pointer"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Validation Error Banner */}
      {validationError && (
        <div className="mb-6 p-4 rounded-lg bg-rose-950/40 border border-rose-500/30 text-rose-200 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
          <span className="text-sm">{validationError}</span>
        </div>
      )}

      {/* API Creation Error Banner */}
      {apiError && (
        <div className="mb-6 p-4 rounded-lg bg-rose-950/40 border border-rose-500/30 text-rose-200 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
          <div className="text-sm">
            <span className="font-semibold">Error: </span>
            {apiError}
          </div>
        </div>
      )}

      {/* AI Analysis Error Banner */}
      {analysisError && (
        <div className="mb-6 p-4 rounded-lg bg-amber-950/40 border border-amber-500/30 text-amber-200 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-amber-400 shrink-0" />
          <div className="text-sm">
            <span className="font-semibold">Analysis Notice: </span>
            {analysisError}
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* MODE A: NEW PROJECT FORM                                      */}
      {/* ============================================================== */}
      {activeMode === 'new_project' && (
        <form onSubmit={handleCreateNewProjectSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="projectName"
              className="block text-xs font-medium text-slate-300 mb-1.5"
            >
              Project Name{' '}
              <span className="text-slate-500 font-normal">
                (Optional — auto-derived if left blank)
              </span>
            </label>
            <input
              id="projectName"
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              disabled={isSubmitting || isAnalyzing}
              placeholder="e.g., High-Throughput Payment Webhook Gateway"
              className="w-full px-3.5 py-2.5 rounded-lg bg-[#090e17] border border-slate-700/80 text-white placeholder:text-slate-600 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500/60 transition-all disabled:opacity-50"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label
                htmlFor="requirements"
                className="block text-xs font-medium text-slate-300"
              >
                Software Requirements <span className="text-emerald-400">*</span>
              </label>
              <span className="text-[11px] font-mono text-slate-500">
                {requirements.length} characters
              </span>
            </div>

            <textarea
              id="requirements"
              rows={6}
              value={requirements}
              onChange={(e) => {
                setRequirements(e.target.value);
                if (validationError && e.target.value.trim()) {
                  setValidationError(null);
                }
              }}
              disabled={isSubmitting || isAnalyzing}
              placeholder="Describe your software in detail. For example:
• Build a backend REST API with FastAPI and PostgreSQL.
• Implement authentication with JWT tokens and role-based permissions (Admin, Member).
• Provide rate limiting for public endpoints using Redis tokens bucket.
• Include automated database migrations via Alembic and health monitoring."
              className="w-full px-4 py-3 rounded-lg bg-[#090e17] border border-slate-700/80 text-slate-100 placeholder:text-slate-600 text-sm font-sans focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500/60 transition-all leading-relaxed resize-y disabled:opacity-50"
            />
          </div>

          {/* Action Row */}
          <div className="flex items-center justify-between pt-2 flex-wrap gap-3">
            <div className="text-xs text-slate-500">
              Analyze requirements with AI or directly create project in PostgreSQL
            </div>

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleAnalyzeNewProjectClick}
                disabled={isSubmitting || isAnalyzing}
                id="analyze-requirements-btn"
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 font-medium text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
                    <span>Analyzing with AI...</span>
                  </>
                ) : (
                  <>
                    <BrainCircuit className="w-4 h-4 text-emerald-400" />
                    <span>Analyze Requirements</span>
                  </>
                )}
              </button>

              <button
                type="submit"
                disabled={isSubmitting || isAnalyzing}
                id="create-project-btn"
                className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white font-medium text-sm transition-all shadow-md shadow-emerald-950/50 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Creating Project...</span>
                  </>
                ) : (
                  <>
                    <span>Create Project</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      )}

      {/* ============================================================== */}
      {/* MODE B: EXISTING REPOSITORY FORM                              */}
      {/* ============================================================== */}
      {activeMode === 'existing_repo' && (
        <div className="space-y-5">
          {/* Repository Selector and Branch Input */}
          {isLoadingRepos ? (
            <div className="p-6 rounded-lg bg-[#090e17] border border-slate-800 flex items-center justify-center gap-2 text-slate-400 text-xs">
              <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
              <span>Loading imported GitHub repositories...</span>
            </div>
          ) : repoLoadError ? (
            <div className="p-4 rounded-lg bg-rose-950/30 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between">
              <span>{repoLoadError}</span>
              <button
                type="button"
                onClick={loadRepositories}
                className="px-2.5 py-1 rounded bg-rose-900/60 hover:bg-rose-800 text-white font-medium cursor-pointer"
              >
                Retry
              </button>
            </div>
          ) : repositories.length === 0 ? (
            /* Empty State: No Repositories Imported Yet */
            <div className="p-8 rounded-xl border border-dashed border-slate-700 bg-[#090e17] text-center">
              <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto mb-3">
                <FolderGit2 className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-semibold text-white">
                No GitHub Repositories Imported Yet
              </h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto mt-1 leading-relaxed">
                Import an existing public or authorized private repository to analyze its code,
                perform FAISS RAG searches, and submit real engineering tasks.
              </p>
              <button
                type="button"
                onClick={() => setIsImportModalOpen(true)}
                className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition-all shadow-md cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                <span>Import GitHub Repository</span>
              </button>
            </div>
          ) : (
            /* Repository Configuration Controls */
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Repository Dropdown */}
                <div className="md:col-span-2">
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                      <FolderGit2 className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Select Imported Repository</span>
                      <span className="text-emerald-400">*</span>
                    </label>
                    <button
                      type="button"
                      onClick={() => setIsImportModalOpen(true)}
                      className="text-xs text-emerald-400 hover:text-emerald-300 flex items-center gap-1 cursor-pointer font-medium"
                    >
                      <Plus className="w-3 h-3" />
                      <span>Import Another</span>
                    </button>
                  </div>
                  <select
                    value={selectedRepoId || ''}
                    onChange={(e) => setSelectedRepoId(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-lg bg-[#090e17] border border-slate-700 text-white text-sm focus:outline-none focus:border-emerald-500 font-sans cursor-pointer"
                  >
                    {repositories.map((repo) => (
                      <option key={repo.id} value={repo.id}>
                        {repo.name} ({repo.owner || 'GitHub'} / {repo.default_branch}) — [
                        {repo.status.toUpperCase()}]
                      </option>
                    ))}
                  </select>
                </div>

                {/* Branch Selection */}
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    Selected Branch / Tag
                  </label>
                  <div className="relative">
                    <GitBranch className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                    <input
                      type="text"
                      value={selectedBranch}
                      onChange={(e) => setSelectedBranch(e.target.value)}
                      placeholder="main"
                      className="w-full pl-9 pr-3.5 py-2.5 rounded-lg bg-[#090e17] border border-slate-700 text-white text-sm focus:outline-none focus:border-emerald-500 font-mono"
                    />
                  </div>
                </div>
              </div>

              {/* Selected Repository Status Banner */}
              {selectedRepo && (
                <div
                  className={`p-3.5 rounded-lg border text-xs flex items-center justify-between gap-3 ${
                    selectedRepo.status === 'ready'
                      ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-300'
                      : selectedRepo.status === 'indexing' || selectedRepo.status === 'pending'
                      ? 'bg-amber-950/30 border-amber-500/30 text-amber-300'
                      : 'bg-rose-950/30 border-rose-500/30 text-rose-300'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    {selectedRepo.status === 'ready' && (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    )}
                    {(selectedRepo.status === 'indexing' ||
                      selectedRepo.status === 'pending') && (
                      <Loader2 className="w-4 h-4 text-amber-400 animate-spin shrink-0" />
                    )}
                    {selectedRepo.status === 'failed' && (
                      <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                    )}

                    <div>
                      <span className="font-semibold text-white">
                        {selectedRepo.name}
                      </span>{' '}
                      <span className="text-slate-400">({selectedRepo.repo_url})</span> —{' '}
                      {selectedRepo.status === 'ready' ? (
                        <span>
                          Indexed & Ready • {selectedRepo.total_files} files •{' '}
                          {selectedRepo.total_chunks} FAISS code chunks
                        </span>
                      ) : selectedRepo.status === 'indexing' ||
                        selectedRepo.status === 'pending' ? (
                        <span>
                          Indexing in progress... Code context will be available once
                          indexing finishes.
                        </span>
                      ) : (
                        <span>
                          Indexing failed: {selectedRepo.error_message || 'Indexing error.'}
                        </span>
                      )}
                    </div>
                  </div>

                  {selectedRepo.status === 'failed' && (
                    <button
                      type="button"
                      onClick={handleReindex}
                      disabled={isReindexing}
                      className="flex items-center gap-1.5 px-3 py-1 rounded bg-rose-900/60 hover:bg-rose-800 text-white font-medium text-xs shrink-0 cursor-pointer disabled:opacity-50"
                    >
                      {isReindexing ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <RotateCw className="w-3 h-3" />
                      )}
                      <span>Re-index</span>
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Multiline Engineering Task Input */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label
                htmlFor="engineeringTask"
                className="block text-xs font-medium text-slate-300"
              >
                Engineering Task for Repository <span className="text-emerald-400">*</span>
              </label>
              <span className="text-[11px] font-mono text-slate-500">
                {engineeringTask.length} characters
              </span>
            </div>

            <textarea
              id="engineeringTask"
              rows={6}
              value={engineeringTask}
              onChange={(e) => {
                setEngineeringTask(e.target.value);
                if (validationError && e.target.value.trim()) {
                  setValidationError(null);
                }
              }}
              disabled={isSubmitting || isAnalyzing || isStartingWorkflow}
              placeholder="Describe what needs to be changed, added, or investigated in this repository. For example:
• Add JWT authentication to the existing FastAPI backend.
• Fix the login validation bug.
• Add pagination to the existing users API.
• Generate tests for the payment service.
• Explain how authentication works in this repository."
              className="w-full px-4 py-3 rounded-lg bg-[#090e17] border border-slate-700/80 text-slate-100 placeholder:text-slate-600 text-sm font-sans focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500/60 transition-all leading-relaxed resize-y disabled:opacity-50"
            />

            {/* Quick Example Task Chips */}
            <div className="mt-2.5 flex items-center gap-1.5 flex-wrap">
              <span className="text-[11px] text-slate-500 mr-1">Examples:</span>
              {EXAMPLE_TASKS.map((task, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setEngineeringTask(task)}
                  className="px-2.5 py-1 rounded-full bg-slate-800/80 hover:bg-slate-700 border border-slate-700/60 text-slate-300 text-[11px] transition-colors cursor-pointer"
                >
                  {task.split(' ')[0]} {task.split(' ')[1]} {task.split(' ')[2]}...
                </button>
              ))}
            </div>
          </div>

          {/* Action Row for Existing Repository */}
          <div className="flex items-center justify-between pt-2 flex-wrap gap-3">
            <div className="text-xs text-slate-500">
              {selectedRepo?.status === 'ready'
                ? 'Planner, Repo Understanding, and Developer agents will use actual code context'
                : 'Repository must be indexed before launching multi-agent workflow'}
            </div>

            <div className="flex items-center gap-3">
              {/* Analyze Task Action */}
              <button
                type="button"
                onClick={handleAnalyzeTaskClick}
                disabled={isSubmitting || isAnalyzing || isStartingWorkflow || !selectedRepo}
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 font-medium text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
                    <span>Analyzing Task...</span>
                  </>
                ) : (
                  <>
                    <BrainCircuit className="w-4 h-4 text-emerald-400" />
                    <span>Analyze Task</span>
                  </>
                )}
              </button>

              {/* Start Engineering Workflow Action */}
              <button
                type="button"
                onClick={handleStartWorkflowClick}
                disabled={
                  isSubmitting ||
                  isAnalyzing ||
                  isStartingWorkflow ||
                  !selectedRepo ||
                  selectedRepo.status !== 'ready'
                }
                id="start-repo-workflow-btn"
                className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white font-medium text-sm transition-all shadow-md shadow-emerald-950/50 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
              >
                {isStartingWorkflow ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Launching Agents...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-white" />
                    <span>Start Engineering Workflow</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Analysis Panel (when analysis is generated in either mode) */}
      {analysis && (
        <AnalysisPanel
          analysis={analysis}
          onClose={() => setAnalysis(null)}
          onCreateProjectFromAnalysis={handleSaveAnalysisAsProject}
          isCreatingProject={isSubmitting || isStartingWorkflow}
        />
      )}

      {/* Reusable Import Repository Modal */}
      <ImportRepositoryModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        onSuccess={(newRepo) => {
          setRepositories((prev) => [newRepo, ...prev.filter((r) => r.id !== newRepo.id)]);
          setSelectedRepoId(newRepo.id);
          setSelectedBranch(newRepo.default_branch || 'main');
        }}
      />
    </div>
  );
};
