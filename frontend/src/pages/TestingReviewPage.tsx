import React, { useState } from 'react';
import type { Project } from '../types/project';
import { ProjectSelectorHeader } from '../components/ProjectSelectorHeader';
import { QAReviewPanel } from '../components/QAReviewPanel';
import { SandboxExecutionPanel } from '../components/SandboxExecutionPanel';
import { ShieldCheck, Shield, Plus, AlertTriangle } from 'lucide-react';

interface TestingReviewPageProps {
  projects: Project[];
  selectedProject: Project | null;
  onSelectProject: (project: Project) => void;
  onNavigateToDashboard: () => void;
  onRefreshProjects: () => void;
}

export const TestingReviewPage: React.FC<TestingReviewPageProps> = ({
  projects,
  selectedProject,
  onSelectProject,
  onNavigateToDashboard,
  onRefreshProjects,
}) => {
  const [activeTab, setActiveTab] = useState<'qa' | 'sandbox'>('qa');

  if (projects.length === 0) {
    return (
      <div className="flex-1 flex flex-col min-h-screen bg-[#080d15] text-slate-100">
        <ProjectSelectorHeader
          title="Testing & Review"
          subtitle="Inspect test plans, security findings, bounded repairs, and container test runs"
          projects={[]}
          selectedProject={null}
          onSelectProject={() => {}}
          onNewProject={onNavigateToDashboard}
        />
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="text-center py-16 px-6 rounded-xl border border-dashed border-slate-800 bg-[#0c1322]/40 max-w-md mx-auto">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto mb-4">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h3 className="text-base font-semibold text-white">No Projects Available</h3>
            <p className="text-xs text-slate-400 max-w-xs mx-auto mt-1 leading-relaxed">
              Create a project first to run static security audits, generate test plans, and execute sandbox container tests.
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
        title="Testing & Review"
        subtitle={`Quality assurance, security audit, and sandbox test execution for ${activeProject.name}`}
        projects={projects}
        selectedProject={activeProject}
        onSelectProject={onSelectProject}
        onNewProject={onNavigateToDashboard}
        onRefresh={onRefreshProjects}
      />

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 sm:px-10 py-6 space-y-6">
        {/* Security Disclaimer Banner */}
        <div className="p-3.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs text-slate-400 flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <span>
            <strong className="text-slate-300">Auditing Disclaimer:</strong> Static AST checks and container tests identify known defects and insecure patterns. Passing an automated review does not guarantee total immunity from architectural flaws or zero-day vulnerabilities.
          </span>
        </div>

        {/* Sub-tab Navigation */}
        <div className="flex border-b border-slate-800 gap-2">
          <button
            onClick={() => setActiveTab('qa')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-mono font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === 'qa'
                ? 'border-emerald-400 text-emerald-300 bg-emerald-500/10'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            <span>QA & Security Audit</span>
          </button>

          <button
            onClick={() => setActiveTab('sandbox')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-mono font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === 'sandbox'
                ? 'border-emerald-400 text-emerald-300 bg-emerald-500/10'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Shield className="w-4 h-4" />
            <span>Sandbox Container Tests</span>
          </button>
        </div>

        {/* Tab Content */}
        {activeTab === 'qa' ? (
          <QAReviewPanel projectId={activeProject.id} />
        ) : (
          <SandboxExecutionPanel projectId={activeProject.id} />
        )}
      </main>
    </div>
  );
};
