import React from 'react';
import {
  Terminal,
  Layers,
  FolderKanban,
  Cpu,
  FolderCode,
  ShieldCheck,
  FolderGit2,
  GitBranch,
} from 'lucide-react';

interface SidebarProps {
  currentView?: string;
  onNavigate?: (view: string) => void;
  projectCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentView = 'dashboard',
  onNavigate,
  projectCount = 0,
}) => {
  const primaryNavItems = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: Layers,
      count: undefined,
    },
    {
      id: 'projects',
      label: 'Projects',
      icon: FolderKanban,
      count: projectCount > 0 ? projectCount : undefined,
    },
    {
      id: 'workflow',
      label: 'Agent Workflow',
      icon: Cpu,
      count: undefined,
    },
    {
      id: 'repositories',
      label: 'Repository Intelligence',
      icon: FolderGit2,
      count: undefined,
    },
    {
      id: 'code',
      label: 'Generated Code',
      icon: FolderCode,
      count: undefined,
    },
    {
      id: 'testing',
      label: 'Testing & Review',
      icon: ShieldCheck,
      count: undefined,
    },
    {
      id: 'git',
      label: 'Version Control',
      icon: GitBranch,
      count: undefined,
    },
  ];

  return (
    <aside className="w-64 bg-[#080d15] border-r border-slate-800/80 flex flex-col h-screen shrink-0 select-none">
      {/* Branding */}
      <div className="h-16 flex items-center px-6 border-b border-slate-800/80 gap-3">
        <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-sm">
          <Terminal className="w-4 h-4" />
        </div>
        <div>
          <div className="flex items-center gap-1.5">
            <span className="font-semibold text-white tracking-tight text-base">CodePilot</span>
            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
              AI
            </span>
          </div>
          <span className="text-[11px] text-slate-500 block -mt-0.5">Software Engineering Assistant</span>
        </div>
      </div>

      {/* Primary Navigation */}
      <div className="flex-1 py-5 px-3 space-y-2 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-mono uppercase tracking-wider text-slate-500 font-semibold">
          Platform Navigation
        </div>

        {primaryNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentView === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate?.(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
                isActive
                  ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/25 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent'
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </div>
              {item.count !== undefined && (
                <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono">
                  {item.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Footer Info */}
      <div className="p-4 border-t border-slate-800/80">
        <div className="rounded-lg bg-slate-900/50 border border-slate-800/80 p-3">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span className="font-mono text-slate-400">Environment</span>
            <span className="text-emerald-400 font-mono text-[11px] flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              Ready
            </span>
          </div>
          <p className="text-[11px] text-slate-500 leading-relaxed">
            Multi-agent orchestration with Groq & LangGraph.
          </p>
        </div>
      </div>
    </aside>
  );
};
