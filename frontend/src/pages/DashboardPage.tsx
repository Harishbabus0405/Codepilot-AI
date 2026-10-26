import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import type { ConnectionStatus, HealthResponse, Project, RequirementsAnalysis } from '../types/project';
import { BackendStatus } from '../components/BackendStatus';
import { RequirementsInput } from '../components/RequirementsInput';
import { RecentProjectsList } from '../components/RecentProjectsList';
import { ProjectDetailModal } from '../components/ProjectDetailModal';

interface DashboardPageProps {
  onProjectsUpdated?: (count: number) => void;
  onProjectCreated?: (project: Project) => void;
  onOpenProject?: (project: Project, targetView?: 'workflow' | 'code' | 'testing') => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  onProjectsUpdated,
  onProjectCreated,
  onOpenProject,
}) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoadingProjects, setIsLoadingProjects] = useState(true);
  const [projectsError, setProjectsError] = useState<string | null>(null);

  const [backendStatus, setBackendStatus] = useState<ConnectionStatus>('checking');
  const [backendHealth, setBackendHealth] = useState<HealthResponse | null>(null);
  const [isCheckingHealth, setIsCheckingHealth] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);

  // Check backend health
  const checkHealth = useCallback(async () => {
    setIsCheckingHealth(true);
    try {
      const health = await api.getHealth();
      setBackendHealth(health);
      setBackendStatus('connected');
    } catch {
      setBackendStatus('disconnected');
      setBackendHealth(null);
    } finally {
      setIsCheckingHealth(false);
    }
  }, []);

  // Fetch projects from PostgreSQL
  const loadProjects = useCallback(async () => {
    setIsLoadingProjects(true);
    setProjectsError(null);
    try {
      const data = await api.getProjects();
      setProjects(data);
      onProjectsUpdated?.(data.length);
    } catch (err) {
      setProjectsError(
        err instanceof Error ? err.message : 'Failed to retrieve projects from database'
      );
    } finally {
      setIsLoadingProjects(false);
    }
  }, [onProjectsUpdated]);

  // Initial load and periodic heartbeat
  useEffect(() => {
    checkHealth();
    loadProjects();

    const interval = setInterval(() => {
      checkHealth();
    }, 15000);

    return () => clearInterval(interval);
  }, [checkHealth, loadProjects]);

  // Handle project creation (supports both Mode A and Mode B)
  const handleCreateProject = async (
    requirements: string,
    name?: string,
    repoId?: string,
    branch?: string
  ): Promise<Project | null> => {
    setIsSubmitting(true);
    try {
      const created = await api.createProject({
        requirements,
        name,
        repository_id: repoId || undefined,
        selected_branch: branch || undefined,
      });
      // Prepend newly created project to the recent list
      setProjects((prev) => [created, ...prev]);
      onProjectsUpdated?.(projects.length + 1);
      onProjectCreated?.(created);
      // Refresh connection status indicator
      checkHealth();
      return created;
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle launching multi-agent workflow
  const handleStartWorkflow = async (project: Project, repoId?: string) => {
    await api.startProjectWorkflow(project.id, {
      pipeline_type: 'full',
      repo_id: repoId || project.repository_id || undefined,
    });
  };

  // Handle AI requirements analysis
  const handleAnalyzeRequirements = async (
    requirements: string,
    name?: string
  ): Promise<RequirementsAnalysis | null> => {
    setIsAnalyzing(true);
    try {
      const result = await api.analyzeRequirements({
        requirements,
        project_name: name,
      });
      return result;
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-[#080d15] text-slate-100 overflow-y-auto">
      {/* Top Navbar Header */}
      <header className="h-16 border-b border-slate-800/80 px-6 sm:px-10 flex items-center justify-between bg-[#080d15]/80 backdrop-blur-md sticky top-0 z-30">
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono font-medium text-slate-400">
            ENGINEERING WORKSPACE
          </span>
          <span className="text-slate-600">/</span>
          <span className="text-xs font-medium text-emerald-400">
            DASHBOARD
          </span>
        </div>

        {/* Backend Connection Status Indicator */}
        <BackendStatus
          status={backendStatus}
          health={backendHealth}
          onRefresh={() => {
            checkHealth();
            loadProjects();
          }}
          isChecking={isCheckingHealth}
        />
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-6 sm:px-10 py-8 space-y-8">
        {/* Workspace Selector (Mode A: New Project vs Mode B: Existing Repo) */}
        <RequirementsInput
          onCreateProject={handleCreateProject}
          onAnalyzeRequirements={handleAnalyzeRequirements}
          onStartWorkflow={handleStartWorkflow}
          isSubmitting={isSubmitting}
          isAnalyzing={isAnalyzing}
          onViewProjectDetails={(p) => setSelectedProject(p)}
          onOpenProjectWorkflow={(p) => {
            if (onOpenProject) {
              onOpenProject(p, 'workflow');
            } else {
              setSelectedProject(p);
            }
          }}
        />

        {/* Recent Projects List */}
        <RecentProjectsList
          projects={projects}
          isLoading={isLoadingProjects}
          error={projectsError}
          onRefresh={loadProjects}
          onSelectProject={(p) => {
            if (onOpenProject) {
              onOpenProject(p, 'code');
            } else {
              setSelectedProject(p);
            }
          }}
        />
      </main>

      {/* Detail Modal */}
      <ProjectDetailModal
        project={selectedProject}
        onClose={() => setSelectedProject(null)}
      />
    </div>
  );
};
