import React from 'react';
import type { Project } from '../types/project';
import { FolderKanban, ChevronDown, Plus, Tag, RefreshCw } from 'lucide-react';

interface ProjectSelectorHeaderProps {
  title: string;
  subtitle: string;
  projects: Project[];
  selectedProject: Project | null;
  onSelectProject: (project: Project) => void;
  onNewProject: () => void;
  onRefresh?: () => void;
  isLoading?: boolean;
}

export const ProjectSelectorHeader: React.FC<ProjectSelectorHeaderProps> = ({
  title,
  subtitle,
  projects,
  selectedProject,
  onSelectProject,
  onNewProject,
  onRefresh,
  isLoading = false,
}) => {
  return (
    <div className="border-b border-slate-800/80 bg-[#0c1322]/80 backdrop-blur-md px-6 sm:px-10 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight flex items-center gap-2">
          {title}
        </h1>
        <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
          {subtitle}
        </p>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        {/* Project Selector Dropdown */}
        {projects.length > 0 ? (
          <div className="relative flex items-center">
            <div className="relative">
              <select
                aria-label="Active Project"
                value={selectedProject?.id || ''}
                onChange={(e) => {
                  const found = projects.find((p) => p.id === e.target.value);
                  if (found) onSelectProject(found);
                }}
                className="appearance-none bg-[#090e17] border border-slate-700/80 hover:border-slate-600 text-slate-100 text-xs font-mono rounded-lg pl-8 pr-8 py-2 focus:outline-none focus:ring-1 focus:ring-emerald-500 cursor-pointer min-w-[200px] max-w-[320px] truncate"
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id} className="bg-[#0c1322] text-slate-100 font-sans">
                    {p.name} ({p.status})
                  </option>
                ))}
              </select>
              <FolderKanban className="w-3.5 h-3.5 text-emerald-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>

            {selectedProject && (
              <span className="hidden lg:inline-flex items-center gap-1 ml-2 px-2 py-1 rounded text-[10px] font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <Tag className="w-2.5 h-2.5" />
                {selectedProject.status}
              </span>
            )}
          </div>
        ) : null}

        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isLoading}
            title="Refresh projects"
            aria-label="Refresh project list"
            className="p-2 rounded-lg bg-[#090e17] border border-slate-700/80 hover:border-slate-600 text-slate-400 hover:text-emerald-400 transition-colors disabled:opacity-50 cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-emerald-400' : ''}`} />
          </button>
        )}

        <button
          onClick={onNewProject}
          className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-emerald-600/90 hover:bg-emerald-500 text-white text-xs font-medium transition-colors shadow-sm cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New Project</span>
        </button>
      </div>
    </div>
  );
};
