import React from 'react';
import type { Project } from '../types/project';
import { FolderGit2, Clock, Copy, Check, RefreshCw, AlertCircle, Eye } from 'lucide-react';

interface RecentProjectsListProps {
  projects: Project[];
  isLoading: boolean;
  error: string | null;
  onRefresh: () => void;
  onSelectProject: (project: Project) => void;
}

export const RecentProjectsList: React.FC<RecentProjectsListProps> = ({
  projects,
  isLoading,
  error,
  onRefresh,
  onSelectProject,
}) => {
  const [copiedId, setCopiedId] = React.useState<string | null>(null);

  const handleCopyId = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const formatDate = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="bg-[#0e1626] border border-slate-800/80 rounded-xl p-6 sm:p-8 shadow-xl">
      {/* Section Header */}
      <div className="flex items-center justify-between pb-5 border-b border-slate-800/80 mb-6">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <FolderGit2 className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white tracking-tight">
              Recent Projects
            </h2>
            <p className="text-xs text-slate-400">
              Persisted projects stored in PostgreSQL
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 font-mono">
            {projects.length} {projects.length === 1 ? 'project' : 'projects'}
          </span>
          <button
            onClick={onRefresh}
            disabled={isLoading}
            title="Refresh projects list"
            aria-label="Refresh project list"
            className="p-1.5 rounded-lg text-slate-400 hover:text-emerald-400 hover:bg-slate-800 transition-colors focus:outline-none disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-emerald-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="p-4 rounded-lg bg-[#090e17] border border-slate-800/60 animate-pulse space-y-3"
            >
              <div className="flex items-center justify-between">
                <div className="h-4 bg-slate-800 rounded w-1/3"></div>
                <div className="h-4 bg-slate-800 rounded w-16"></div>
              </div>
              <div className="h-3 bg-slate-800/60 rounded w-3/4"></div>
              <div className="h-3 bg-slate-800/40 rounded w-1/2"></div>
            </div>
          ))}
        </div>
      )}

      {/* Error State */}
      {!isLoading && error && (
        <div className="p-4 rounded-lg bg-rose-950/30 border border-rose-500/30 text-rose-200 flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold">Failed to Load Projects</p>
              <p className="text-xs text-rose-300/80 mt-0.5">{error}</p>
            </div>
          </div>
          <button
            onClick={onRefresh}
            className="text-xs px-3 py-1.5 rounded bg-rose-900/60 hover:bg-rose-900 text-rose-100 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && projects.length === 0 && (
        <div className="text-center py-12 px-4 rounded-lg border border-dashed border-slate-800 bg-[#090e17]/50">
          <div className="w-12 h-12 rounded-full bg-slate-800/60 text-slate-500 flex items-center justify-center mx-auto mb-3">
            <FolderGit2 className="w-6 h-6" />
          </div>
          <p className="text-sm font-medium text-slate-300">
            No projects created yet
          </p>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 leading-relaxed">
            Describe your software requirements in the form above and click &quot;Create Project&quot; to initialize your first project.
          </p>
        </div>
      )}

      {/* Populated List State */}
      {!isLoading && !error && projects.length > 0 && (
        <div className="space-y-3">
          {projects.map((proj) => (
            <div
              key={proj.id}
              onClick={() => onSelectProject(proj)}
              className="group p-4 rounded-lg bg-[#090e17] hover:bg-[#0c1320] border border-slate-800/80 hover:border-emerald-500/30 transition-all cursor-pointer shadow-sm"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-sm font-semibold text-white group-hover:text-emerald-300 transition-colors truncate">
                      {proj.name}
                    </h3>
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      <span className="w-1 h-1 rounded-full bg-emerald-400"></span>
                      {proj.status}
                    </span>
                  </div>

                  <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                    {proj.original_requirements}
                  </p>
                </div>

                <div className="flex items-center gap-1 shrink-0 text-slate-400 group-hover:text-slate-200">
                  <button
                    onClick={(e) => handleCopyId(e, proj.id)}
                    title="Copy Project UUID"
                    className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
                  >
                    {copiedId === proj.id ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>

                  <button
                    title="View details"
                    className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-emerald-400 transition-colors"
                  >
                    <Eye className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Card Footer */}
              <div className="flex items-center justify-between text-[11px] text-slate-500 mt-3 pt-2 border-t border-slate-800/60 font-mono flex-wrap gap-2">
                <span className="truncate max-w-[180px]">
                  UUID: {proj.id.slice(0, 8)}...{proj.id.slice(-4)}
                </span>
                <div className="flex items-center gap-3">
                  <span className="text-emerald-400 group-hover:text-emerald-300 font-sans font-medium text-[11px] flex items-center gap-1 transition-colors">
                    Open Project Workspace →
                  </span>

                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {formatDate(proj.created_at)}
                  </span>
                </div>
              </div>
            </div>
          ))}

        </div>
      )}
    </div>
  );
};
