import React from 'react';
import type { Project } from '../types/project';
import { ProjectSelectorHeader } from '../components/ProjectSelectorHeader';
import { ProjectWorkspace } from '../components/ProjectWorkspace';
import { FolderCode, Plus } from 'lucide-react';

interface GeneratedCodePageProps {
  projects: Project[];
  selectedProject: Project | null;
  onSelectProject: (project: Project) => void;
  onNavigateToDashboard: () => void;
  onRefreshProjects: () => void;
}

export const GeneratedCodePage: React.FC<GeneratedCodePageProps> = ({
  projects,
  selectedProject,
  onSelectProject,
  onNavigateToDashboard,
  onRefreshProjects,
}) => {
  if (projects.length === 0) {
    return (
      <div className="flex-1 flex flex-col min-h-screen bg-[#080d15] text-slate-100">
        <ProjectSelectorHeader
          title="Generated Code"
          subtitle="Inspect generated project files, source code, and download ZIP archives"
          projects={[]}
          selectedProject={null}
          onSelectProject={() => {}}
          onNewProject={onNavigateToDashboard}
        />
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="text-center py-16 px-6 rounded-xl border border-dashed border-slate-800 bg-[#0c1322]/40 max-w-md mx-auto">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto mb-4">
              <FolderCode className="w-6 h-6" />
            </div>
            <h3 className="text-base font-semibold text-white">No Projects Available</h3>
            <p className="text-xs text-slate-400 max-w-xs mx-auto mt-1 leading-relaxed">
              Create a project first to generate and inspect source code files in an isolated workspace.
            </p>
            <button
              onClick={onNavigateToDashboard}
              className="mt-5 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition-colors shadow-sm cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>Create Project</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  const activeProject = selectedProject || projects[0];

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-[#080d15] text-slate-100 overflow-y-auto">
      <ProjectSelectorHeader
        title="Generated Code"
        subtitle={`Source code explorer and workspace for ${activeProject.name}`}
        projects={projects}
        selectedProject={activeProject}
        onSelectProject={onSelectProject}
        onNewProject={onNavigateToDashboard}
        onRefresh={onRefreshProjects}
      />

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 sm:px-10 py-8">
        <ProjectWorkspace
          projectId={activeProject.id}
          projectName={activeProject.name}
        />
      </main>
    </div>
  );
};
