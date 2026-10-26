import React from 'react';
import type { RequirementsAnalysis } from '../types/project';
import {
  Sparkles,
  CheckCircle2,
  Cpu,
  Layers,
  HelpCircle,
  AlertTriangle,
  X,
  FileCheck2,
} from 'lucide-react';

interface AnalysisPanelProps {
  analysis: RequirementsAnalysis;
  onClose: () => void;
  onCreateProjectFromAnalysis?: () => void;
  isCreatingProject?: boolean;
}

export const AnalysisPanel: React.FC<AnalysisPanelProps> = ({
  analysis,
  onClose,
  onCreateProjectFromAnalysis,
  isCreatingProject,
}) => {
  return (
    <div className="mt-6 bg-[#0c1322] border border-emerald-500/30 rounded-xl p-6 sm:p-8 shadow-2xl animate-in fade-in slide-in-from-top-2 duration-200">
      {/* Panel Header */}
      <div className="flex items-start justify-between gap-4 pb-5 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
              <Sparkles className="w-3 h-3" />
              AI ARCHITECTURAL ANALYSIS
            </span>
            {analysis.model_used && (
              <span className="text-[11px] font-mono text-slate-400 px-2 py-0.5 rounded bg-slate-800/80 border border-slate-700/60">
                Model: {analysis.model_used}
              </span>
            )}
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">
            Synthesized System Specifications
          </h2>
        </div>

        <button
          onClick={onClose}
          title="Close analysis panel"
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="mt-6 space-y-6">
        {/* 1. Project Summary */}
        <div>
          <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 mb-2">
            1. Project Summary
          </h3>
          <div className="p-4 rounded-lg bg-[#070b14] border border-slate-800/80 text-slate-200 text-sm leading-relaxed">
            {analysis.project_summary}
          </div>
        </div>

        {/* 2. Suggested Technology Stack */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Cpu className="w-4 h-4 text-emerald-400" />
            <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400">
              2. Suggested Technology Stack
            </h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {analysis.suggested_tech_stack.map((tech, idx) => (
              <span
                key={idx}
                className="px-3 py-1 rounded-md text-xs font-mono font-medium bg-emerald-950/40 text-emerald-300 border border-emerald-500/25 shadow-sm"
              >
                {tech}
              </span>
            ))}
          </div>
        </div>

        {/* 3. Core Functional Requirements */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400">
              3. Functional Requirements
            </h3>
          </div>
          <ul className="space-y-2">
            {analysis.functional_requirements.map((req, idx) => (
              <li
                key={idx}
                className="flex items-start gap-2.5 text-xs sm:text-sm text-slate-300 p-2.5 rounded-lg bg-[#070b14] border border-slate-800/60"
              >
                <span className="font-mono text-emerald-400 font-semibold text-xs mt-0.5">
                  {idx + 1}.
                </span>
                <span className="leading-relaxed">{req}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* 4. Main Modules */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Layers className="w-4 h-4 text-emerald-400" />
            <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400">
              4. Main Modules
            </h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {analysis.main_modules.map((mod, idx) => (
              <div
                key={idx}
                className="p-3.5 rounded-lg bg-[#070b14] border border-slate-800/80"
              >
                <h4 className="text-sm font-semibold text-white mb-1 flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                  {mod.name}
                </h4>
                <p className="text-xs text-slate-400 leading-relaxed">
                  {mod.description}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* 5. Important Assumptions & 6. Potential Risks Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Important Assumptions */}
          <div className="p-4 rounded-lg bg-[#070b14] border border-slate-800/80">
            <div className="flex items-center gap-2 mb-2.5">
              <HelpCircle className="w-4 h-4 text-sky-400" />
              <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-300">
                5. Important Assumptions
              </h3>
            </div>
            <ul className="space-y-2">
              {analysis.important_assumptions.map((item, idx) => (
                <li key={idx} className="text-xs text-slate-400 leading-relaxed flex items-start gap-2">
                  <span className="text-sky-400">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Potential Risks */}
          <div className="p-4 rounded-lg bg-[#070b14] border border-rose-500/20">
            <div className="flex items-center gap-2 mb-2.5">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-300">
                6. Potential Risks
              </h3>
            </div>
            <ul className="space-y-2">
              {analysis.potential_risks.map((item, idx) => (
                <li key={idx} className="text-xs text-slate-400 leading-relaxed flex items-start gap-2">
                  <span className="text-amber-400">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Footer Actions */}
      <div className="mt-6 pt-4 border-t border-slate-800 flex items-center justify-between flex-wrap gap-3">
        <span className="text-xs text-slate-500">
          Analysis generated dynamically via Groq API.
        </span>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors"
          >
            Close Panel
          </button>

          {onCreateProjectFromAnalysis && (
            <button
              type="button"
              onClick={onCreateProjectFromAnalysis}
              disabled={isCreatingProject}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition-colors shadow-md disabled:opacity-50"
            >
              <FileCheck2 className="w-4 h-4" />
              <span>{isCreatingProject ? 'Saving Project...' : 'Save As Project'}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
