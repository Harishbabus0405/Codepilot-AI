import React, { useState, useEffect, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import { DashboardPage } from './pages/DashboardPage';
import { ProjectsPage } from './pages/ProjectsPage';
import { AgentWorkflowPage } from './pages/AgentWorkflowPage';
import { GeneratedCodePage } from './pages/GeneratedCodePage';
import { TestingReviewPage } from './pages/TestingReviewPage';
import { RepositoryChatPanel } from './components/RepositoryChatPanel';
import { VersionControlPage } from './pages/VersionControlPage';
import { api } from './services/api';
import type { Project } from './types/project';

export const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<string>('dashboard');
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [isLoadingProjects, setIsLoadingProjects] = useState<boolean>(true);
  const [projectsError, setProjectsError] = useState<string | null>(null);

  // Fetch all persisted projects from PostgreSQL
  const loadProjects = useCallback(async () => {
    setIsLoadingProjects(true);
    setProjectsError(null);
    try {
      const data = await api.getProjects();
      setProjects(data);
      if (data.length > 0) {
        setSelectedProject((prev) => (prev ? (data.find((p) => p.id === prev.id) || data[0]) : data[0]));
      }
    } catch (err) {
      setProjectsError(
        err instanceof Error ? err.message : 'Failed to retrieve projects from database'
      );
    } finally {
      setIsLoadingProjects(false);
    }
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const handleSelectProjectAndNavigate = (
    project: Project,
    targetView?: 'workflow' | 'code' | 'testing'
  ) => {
    setSelectedProject(project);
    if (targetView) {
      setCurrentView(targetView);
    }
  };

  const handleProjectCreated = (newProject: Project) => {
    setProjects((prev) => [newProject, ...prev]);
    setSelectedProject(newProject);
  };

  return (
    <div className="flex h-screen bg-[#080d15] text-slate-100 overflow-hidden font-sans">
      {/* Minimal Navigation Sidebar */}
      <Sidebar
        currentView={currentView}
        onNavigate={(view) => setCurrentView(view)}
        projectCount={projects.length}
      />

      {/* Main View Router */}
      <main className="flex-1 flex flex-col min-h-screen bg-[#080d15] overflow-y-auto">
        {currentView === 'dashboard' && (
          <DashboardPage
            onProjectCreated={handleProjectCreated}
            onOpenProject={(p, view) => handleSelectProjectAndNavigate(p, view)}
          />
        )}

        {currentView === 'projects' && (
          <ProjectsPage
            projects={projects}
            isLoading={isLoadingProjects}
            error={projectsError}
            onRefresh={loadProjects}
            onSelectProject={handleSelectProjectAndNavigate}
            onNavigateToDashboard={() => setCurrentView('dashboard')}
          />
        )}

        {currentView === 'workflow' && (
          <AgentWorkflowPage
            projects={projects}
            selectedProject={selectedProject}
            onSelectProject={(p) => setSelectedProject(p)}
            onNavigateToDashboard={() => setCurrentView('dashboard')}
            onRefreshProjects={loadProjects}
          />
        )}

        {currentView === 'code' && (
          <GeneratedCodePage
            projects={projects}
            selectedProject={selectedProject}
            onSelectProject={(p) => setSelectedProject(p)}
            onNavigateToDashboard={() => setCurrentView('dashboard')}
            onRefreshProjects={loadProjects}
          />
        )}

        {currentView === 'testing' && (
          <TestingReviewPage
            projects={projects}
            selectedProject={selectedProject}
            onSelectProject={(p) => setSelectedProject(p)}
            onNavigateToDashboard={() => setCurrentView('dashboard')}
            onRefreshProjects={loadProjects}
          />
        )}

        {currentView === 'repositories' && (
          <div className="flex-1 flex flex-col min-h-screen bg-[#080d15] text-slate-100 overflow-y-auto">
            <header className="h-16 border-b border-slate-800/80 px-6 sm:px-10 flex items-center justify-between bg-[#080d15]/80 backdrop-blur-md sticky top-0 z-30">
              <div className="flex items-center gap-3">
                <span className="text-xs font-mono font-medium text-slate-400">ENGINEERING WORKSPACE</span>
                <span className="text-slate-600">/</span>
                <span className="text-xs font-medium text-emerald-400">REPOSITORY INTELLIGENCE</span>
              </div>
            </header>
            <main className="flex-1 max-w-6xl w-full mx-auto p-6 sm:px-10 py-6">
              <RepositoryChatPanel />
            </main>
          </div>
        )}

        {currentView === 'git' && (
          <VersionControlPage />
        )}
      </main>
    </div>
  );
};

export default App;
