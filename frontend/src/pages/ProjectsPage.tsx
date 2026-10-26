import React, { useState } from 'react';
import type { Project } from '../types/project';
import {
  FolderKanban,
  Search,
  Clock,
  ArrowRight,
  FolderCode,
  Cpu,
  ShieldCheck,
  Plus,
  RefreshCw,
  AlertCircle,
  Copy,
  Check,
} from 'lucide-react';

interface ProjectsPageProps {
  projects: Project[];
  isLoading: boolean;
  error: string | null;
  onRefresh: () => void;
  onSelectProject: (project: Project, targetView?: 'workflow' | 'code' | 'testing') => void;
  onNavigateToDashboard: () => void;
}

export const ProjectsPage: React.FC<ProjectsPageProps> = ({
  projects,
  isLoading,
  error,
  onRefresh,
  onSelectProject,
  onNavigateToDashboard,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);

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

  const filteredProjects = projects.filter((p) => {
    const q = searchQuery.toLowerCase();
    return (
      p.name.toLowerCase().includes(q) ||
      (p.original_requirements && p.original_requirements.toLowerCase().includes(q)) ||
      p.status.toLowerCase().includes(q)
    );
  });

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-[#080d15] text-slate-100 overflow-y-auto">
      {/* Header */}
      <div className="border-b border-slate-800/80 bg-[#0c1322]/80 backdrop-blur-md px-6 sm:px-10 py-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1 text-emerald-400 font-mono text-xs uppercase tracking-wider">
              <FolderKanban className="w-3.5 h-3.5" />
              <span>Project Repository</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
              Projects
            </h1>
            <p className="text-slate-400 text-xs sm:text-sm mt-1">
              Browse, reopen, and manage persisted engineering initiatives stored in PostgreSQL.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={onRefresh}
              disabled={isLoading}
              title="Refresh project list"
              aria-label="Refresh project list"
              className="p-2.5 rounded-lg bg-[#090e17] border border-slate-700/80 hover:border-slate-600 text-slate-300 hover:text-emerald-400 transition-colors cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-emerald-400' : ''}`} />
            </button>

            <button
              onClick={onNavigateToDashboard}
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition-colors shadow-sm cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>Create Project</span>
            </button>
          </div>
        </div>

        {/* Search Bar */}
        <div className="mt-5 max-w-md relative">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter projects by name, status, or keyword..."
            className="w-full pl-9 pr-4 py-2 bg-[#090e17] border border-slate-700/80 rounded-lg text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 transition-all font-sans"
          />
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 sm:px-10 py-8">
        {/* Loading State */}
        {isLoading && (
          <div className="space-y-4">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="p-5 rounded-xl bg-[#0c1322] border border-slate-800 animate-pulse space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="h-5 bg-slate-800 rounded w-1/3"></div>
                  <div className="h-5 bg-slate-800 rounded w-20"></div>
                </div>
                <div className="h-4 bg-slate-800/60 rounded w-3/4"></div>
                <div className="h-3 bg-slate-800/40 rounded w-1/4"></div>
              </div>
            ))}
          </div>
        )}

        {/* Error State */}
        {!isLoading && error && (
          <div className="p-6 rounded-xl bg-rose-950/30 border border-rose-500/30 text-rose-200 flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm font-semibold">Failed to Retrieve Projects</h3>
                <p className="text-xs text-rose-300/80 mt-1">{error}</p>
              </div>
            </div>
            <button
              onClick={onRefresh}
              className="text-xs px-3.5 py-1.5 rounded-lg bg-rose-900/60 hover:bg-rose-900 text-rose-100 transition-colors cursor-pointer"
            >
              Retry
            </button>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !error && projects.length === 0 && (
          <div className="text-center py-16 px-6 rounded-xl border border-dashed border-slate-800 bg-[#0c1322]/40 max-w-lg mx-auto">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto mb-4">
              <FolderKanban className="w-6 h-6" />
            </div>
            <h3 className="text-base font-semibold text-white">No Projects Saved Yet</h3>
            <p className="text-xs text-slate-400 max-w-xs mx-auto mt-1 leading-relaxed">
              Create your first project by describing your software requirements on the dashboard.
            </p>
            <button
              onClick={onNavigateToDashboard}
              className="mt-5 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition-colors shadow-sm cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>Create Project</span>
            </button>
          </div>
        )}

        {/* No Search Matches */}
        {!isLoading && !error && projects.length > 0 && filteredProjects.length === 0 && (
          <div className="text-center py-12 px-4 rounded-xl border border-slate-800 bg-[#0c1322]/40">
            <p className="text-sm text-slate-300 font-medium">No matching projects found</p>
            <p className="text-xs text-slate-500 mt-1">Try adjusting your search filter keywords.</p>
          </div>
        )}

        {/* Populated Project List */}
        {!isLoading && !error && filteredProjects.length > 0 && (
          <div className="space-y-4">
            {filteredProjects.map((proj) => (
              <div
                key={proj.id}
                className="p-5 rounded-xl bg-[#0c1322] border border-slate-800 hover:border-slate-700/80 transition-all shadow-md group"
              >
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <h2 className="text-base font-bold text-white group-hover:text-emerald-300 transition-colors">
                        {proj.name}
                      </h2>
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                        {proj.status}
                      </span>
                    </div>

                    <p className="text-xs text-slate-400 mt-2 line-clamp-2 leading-relaxed">
                      {proj.original_requirements}
                    </p>

                    <div className="flex items-center gap-4 mt-3 text-[11px] text-slate-500 font-mono flex-wrap">
                      <div className="flex items-center gap-1.5">
                        <span>ID: {proj.id.slice(0, 8)}...{proj.id.slice(-4)}</span>
                        <button
                          onClick={(e) => handleCopyId(e, proj.id)}
                          title="Copy Project UUID"
                          className="hover:text-slate-300 p-0.5 cursor-pointer"
                        >
                          {copiedId === proj.id ? (
                            <Check className="w-3 h-3 text-emerald-400" />
                          ) : (
                            <Copy className="w-3 h-3" />
                          )}
                        </button>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <Clock className="w-3 h-3" />
                        <span>{formatDate(proj.created_at)}</span>
                      </div>
                    </div>
                  </div>

                  {/* Actions for this project */}
                  <div className="flex items-center gap-2 self-start flex-wrap pt-1 sm:pt-0">
                    <button
                      onClick={() => onSelectProject(proj, 'code')}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-medium transition-colors cursor-pointer"
                    >
                      <FolderCode className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Code</span>
                    </button>

                    <button
                      onClick={() => onSelectProject(proj, 'workflow')}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-medium transition-colors cursor-pointer"
                    >
                      <Cpu className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Workflow</span>
                    </button>

                    <button
                      onClick={() => onSelectProject(proj, 'testing')}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-medium transition-colors cursor-pointer"
                    >
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Review</span>
                    </button>

                    <button
                      onClick={() => onSelectProject(proj, 'code')}
                      className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-600/90 hover:bg-emerald-500 text-white text-xs font-medium transition-colors cursor-pointer shadow-sm ml-1"
                    >
                      <span>Open</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
};
