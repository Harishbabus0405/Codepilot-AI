import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import type { Project, ImportedRepository } from '../types/project';
import { VersionControlPanel } from '../components/VersionControlPanel';
import { GitBranch, Loader2 } from 'lucide-react';




interface WorkspaceOption {
  id: string;
  name: string;
  type: 'project' | 'repository';
}

export const VersionControlPage: React.FC = () => {
  const [workspaces, setWorkspaces] = useState<WorkspaceOption[]>([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState<WorkspaceOption | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchWorkspaces = async () => {
      setIsLoading(true);
      try {
        const [projects, repos] = await Promise.all([
          api.getProjects().catch(() => [] as Project[]),
          api.getRepositories().catch(() => [] as ImportedRepository[]),
        ]);

        const projectOptions: WorkspaceOption[] = (projects || []).map((p) => ({
          id: p.id,
          name: p.name,
          type: 'project',
        }));

        const repoOptions: WorkspaceOption[] = (repos || []).map((r) => ({
          id: r.id,
          name: `${r.owner}/${r.name}`,
          type: 'repository',
        }));

        const combined = [...projectOptions, ...repoOptions];
        setWorkspaces(combined);
        if (combined.length > 0) {
          setSelectedWorkspace(combined[0]);
        }
      } catch (err) {
        console.error('Failed to load workspaces:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchWorkspaces();
  }, []);

  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-12 text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-500 mb-3" />
        <p className="text-sm">Loading available project workspaces...</p>
      </div>
    );
  }

  if (workspaces.length === 0) {
    return (
      <div className="flex-1 p-6 sm:p-10 flex flex-col items-center justify-center text-center">
        <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mb-4">
          <GitBranch className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-bold text-slate-100 mb-2">No Project Workspaces Available</h2>
        <p className="text-xs text-slate-400 max-w-md mb-6">
          Create a project on the Dashboard or import an authorized GitHub repository to start inspecting working tree changes, reviewing diffs, committing, and opening Pull Requests.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col p-6 sm:p-10 space-y-4 max-w-7xl mx-auto w-full">
      {/* Workspace Selector Bar */}
      <div className="bg-[#0c1322] border border-slate-800 rounded-lg p-3 flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center space-x-2 text-xs">
          <span className="text-slate-400 font-medium">Active Workspace:</span>
          <select
            value={selectedWorkspace?.id || ''}
            onChange={(e) => {
              const found = workspaces.find((w) => w.id === e.target.value);
              if (found) setSelectedWorkspace(found);
            }}
            className="bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-emerald-500 font-mono"
          >
            {workspaces.map((w) => (
              <option key={w.id} value={w.id}>
                {w.type === 'project' ? '📁 Project: ' : '🐙 GitHub: '}
                {w.name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center space-x-2 text-xs text-slate-400">
          <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300 font-mono text-[10px]">
            UUID: {selectedWorkspace?.id.slice(0, 8)}...
          </span>
          <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono text-[10px] uppercase">
            {selectedWorkspace?.type}
          </span>
        </div>
      </div>

      {/* Main Version Control Panel */}
      {selectedWorkspace && (
        <div className="flex-1 min-h-[650px]">
          <VersionControlPanel
            workspaceId={selectedWorkspace.id}
            workspaceName={selectedWorkspace.name}
            isProject={selectedWorkspace.type === 'project'}
          />
        </div>
      )}
    </div>
  );
};
