import React, { useState } from 'react';
import type { Project } from '../types/project';
import { X, Copy, Check, Calendar, Tag, FileText, Cpu, FolderCode, FolderGit2, Shield, ShieldCheck } from 'lucide-react';
import { WorkflowView } from './WorkflowView';
import { ProjectWorkspace } from './ProjectWorkspace';
import { VersionControlPanel } from './VersionControlPanel';
import { SandboxExecutionPanel } from './SandboxExecutionPanel';
import { QAReviewPanel } from './QAReviewPanel';

interface ProjectDetailModalProps {
  project: Project | null;
  initialTab?: 'workspace' | 'workflow' | 'qa' | 'details' | 'git' | 'sandbox';
  onClose: () => void;
}

export const ProjectDetailModal: React.FC<ProjectDetailModalProps> = ({
  project,
  initialTab = 'workspace',
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<'workspace' | 'workflow' | 'qa' | 'details' | 'git' | 'sandbox'>(initialTab);


  const [copied, setCopied] = useState(false);

  if (!project) return null;

  const handleCopyId = () => {
    navigator.clipboard.writeText(project.id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatDate = (isoString: string) => {
    try {
      return new Date(isoString).toLocaleString(undefined, {
        dateStyle: 'full',
        timeStyle: 'medium',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div
        className="w-full max-w-5xl bg-[#0c1322] border border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[94vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-slate-800 flex items-start justify-between gap-4 bg-[#090e17]">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                PROJECT WORKSPACE
              </span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-slate-800 text-slate-300">
                <Tag className="w-2.5 h-2.5 text-emerald-400" />
                {project.status}
              </span>
            </div>
            <h2 className="text-xl font-bold text-white tracking-tight">
              {project.name}
            </h2>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Switcher */}
        <div className="flex border-b border-slate-800/80 bg-[#070b14] px-6 gap-2 pt-2">
          <button
            onClick={() => setActiveTab('workspace')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-mono font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === 'workspace'
                ? 'border-emerald-400 text-emerald-300 bg-emerald-500/10'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FolderCode className="w-4 h-4" />
            Code Workspace & Files
          </button>

          <button
            onClick={() => setActiveTab('workflow')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-mono font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === 'workflow'
                ? 'border-emerald-400 text-emerald-300 bg-emerald-500/10'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Cpu className="w-4 h-4" />
            Multi-Agent Architecture
          </button>

          <button
            onClick={() => setActiveTab('qa')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-mono font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === 'qa'
                ? 'border-emerald-400 text-emerald-300 bg-emerald-500/10'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            QA & Security Audit
          </button>

          <button
            onClick={() => setActiveTab('git')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-mono font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === 'git'
                ? 'border-emerald-400 text-emerald-300 bg-emerald-500/10'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FolderGit2 className="w-4 h-4" />
            Git & Version Control
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
            Sandbox Execution
          </button>

          <button
            onClick={() => setActiveTab('details')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-mono font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === 'details'
                ? 'border-emerald-400 text-emerald-300 bg-emerald-500/10'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileText className="w-4 h-4" />
            Project Details & Info
          </button>

        </div>


        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          {activeTab === 'workspace' && (
            <div className="animate-in fade-in duration-150">
              <ProjectWorkspace
                projectId={project.id}
                projectName={project.name}
              />
            </div>
          )}

          {activeTab === 'workflow' && (
            <div className="animate-in fade-in duration-150">
              <WorkflowView projectId={project.id} />
            </div>
          )}

          {activeTab === 'qa' && (
            <div className="animate-in fade-in duration-150">
              <QAReviewPanel
                projectId={project.id}
                projectName={project.name}
              />
            </div>
          )}

          {activeTab === 'git' && (
            <div className="animate-in fade-in duration-150">
              <VersionControlPanel
                workspaceId={project.id}
                workspaceName={project.name}
                isProject={true}
              />
            </div>
          )}

          {activeTab === 'sandbox' && (
            <div className="animate-in fade-in duration-150">
              <SandboxExecutionPanel
                projectId={project.id}
                projectName={project.name}
              />
            </div>
          )}

          {activeTab === 'details' && (
            <div className="space-y-6 animate-in fade-in duration-150">
              {/* Metadata Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-lg bg-[#070b12] border border-slate-800">
                  <span className="text-slate-500 block mb-1">UUID</span>
                  <div className="flex items-center justify-between font-mono text-slate-300">
                    <span className="truncate mr-2">{project.id}</span>
                    <button
                      onClick={handleCopyId}
                      title="Copy full UUID"
                      className="p-1 hover:text-emerald-400 text-slate-400 transition-colors cursor-pointer"
                    >
                      {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-[#070b12] border border-slate-800">
                  <span className="text-slate-500 block mb-1">Created Timestamp</span>
                  <div className="flex items-center gap-1.5 text-slate-300">
                    <Calendar className="w-3.5 h-3.5 text-emerald-400" />
                    <span>{formatDate(project.created_at)}</span>
                  </div>
                </div>
              </div>

              {/* Original Requirements */}
              <div>
                <div className="flex items-center gap-2 mb-2 text-xs font-semibold text-slate-300 uppercase tracking-wider font-mono">
                  <FileText className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Original Software Requirements</span>
                </div>
                <div className="p-4 rounded-lg bg-[#070b12] border border-slate-800 text-slate-200 text-xs sm:text-sm whitespace-pre-wrap font-sans leading-relaxed">
                  {project.original_requirements}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 flex justify-end bg-[#090e17]">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium font-mono transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
