import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import type {
  QAFindingItem,
  QARunResponse,
  QAFindingSeverity,
} from '../types/project';
import {
  ShieldAlert,
  ShieldCheck,
  Bug,
  CheckCircle2,
  AlertTriangle,
  Info,
  Wrench,
  Loader2,
  RefreshCw,
  FileCode,
  Check,
  Sparkles,
} from 'lucide-react';

interface QAReviewPanelProps {
  projectId: string;
  projectName?: string;
}

export const QAReviewPanel: React.FC<QAReviewPanelProps> = ({
  projectId,
  projectName = 'Project',
}) => {
  const [qaRun, setQaRun] = useState<QARunResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRunningQA, setIsRunningQA] = useState<boolean>(false);
  const [repairingFindingId, setRepairingFindingId] = useState<string | null>(null);
  const [repairSuccessMsg, setRepairSuccessMsg] = useState<string | null>(null);
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadQARun = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await api.getLatestQARun(projectId);
      setQaRun(data);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to fetch QA review status.');
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadQARun();
  }, [loadQARun]);

  const handleRunQA = async () => {
    setIsRunningQA(true);
    setErrorMessage(null);
    setRepairSuccessMsg(null);
    try {
      const res = await api.triggerQARun(projectId);
      setQaRun(res);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to trigger QA run.');
    } finally {
      setIsRunningQA(false);
    }
  };

  const handleApplyRepair = async (finding: QAFindingItem) => {
    setRepairingFindingId(finding.id);
    setErrorMessage(null);
    setRepairSuccessMsg(null);
    try {
      const res = await api.applyFindingRepair(projectId, finding.id);
      setRepairSuccessMsg(
        `Repaired ${finding.file_path}: ${res.message} (${res.recheck_verified ? 'Re-verified Fixed' : 'Needs review'})`
      );
      // Reload QA run to reflect latest status and recalculated security score
      const updated = await api.getLatestQARun(projectId);
      setQaRun(updated);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to apply repair.');
    } finally {
      setRepairingFindingId(null);
    }
  };

  const getSeverityBadge = (sev: QAFindingSeverity) => {
    switch (sev) {
      case 'critical':
        return (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-950 text-rose-400 border border-rose-800">
            <ShieldAlert className="w-3 h-3" /> CRITICAL
          </span>
        );
      case 'high':
        return (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-950 text-amber-400 border border-amber-800">
            <AlertTriangle className="w-3 h-3" /> HIGH
          </span>
        );
      case 'medium':
        return (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-yellow-950/60 text-yellow-300 border border-yellow-800/60">
            <Bug className="w-3 h-3" /> MEDIUM
          </span>
        );
      case 'low':
        return (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-blue-950 text-blue-300 border border-blue-800">
            <Info className="w-3 h-3" /> LOW
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-slate-800 text-slate-400">
            INFO
          </span>
        );
    }
  };

  const findings = qaRun?.findings || [];
  const filteredFindings =
    filterSeverity === 'all'
      ? findings
      : findings.filter((f) => f.severity === filterSeverity);

  const summary = qaRun?.summary;
  const score = summary?.security_score ?? 100;
  const isPassed = summary?.security_status === 'passed';

  return (
    <div className="flex flex-col h-full bg-[#0c1322] border border-slate-800 rounded-xl overflow-hidden text-slate-100">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 bg-[#090e17] flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-400">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <span>QA, Security & Code Review</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                PHASE 5 AGENTS
              </span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Automated AST static audit, defect detection, and bounded repair coordinator for{' '}
              <span className="text-slate-200 font-medium">{projectName}</span>.
            </p>
          </div>
        </div>

        <button
          onClick={handleRunQA}
          disabled={isRunningQA}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-xs font-mono font-medium transition-colors cursor-pointer shadow-sm shadow-emerald-950"
        >
          {isRunningQA ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <RefreshCw className="w-3.5 h-3.5" />
          )}
          <span>{isRunningQA ? 'Auditing Codebase...' : 'Run QA & Security Audit'}</span>
        </button>
      </div>

      {/* Messages */}
      {errorMessage && (
        <div className="p-3 mx-4 mt-4 bg-rose-950/60 border border-rose-800 text-rose-300 text-xs rounded-lg flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{errorMessage}</span>
        </div>
      )}

      {repairSuccessMsg && (
        <div className="p-3 mx-4 mt-4 bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-xs rounded-lg flex items-center gap-2 animate-in fade-in duration-200">
          <Check className="w-4 h-4 shrink-0 text-emerald-400" />
          <span>{repairSuccessMsg}</span>
        </div>
      )}

      {/* Body */}
      <div className="p-4 overflow-y-auto space-y-4">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-12 text-slate-400">
            <Loader2 className="w-6 h-6 animate-spin text-emerald-400 mb-2" />
            <p className="text-xs font-mono">Loading QA audit state...</p>
          </div>
        ) : !qaRun ? (
          <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-slate-800 rounded-xl bg-slate-900/30">
            <ShieldAlert className="w-8 h-8 text-slate-500 mb-2" />
            <h3 className="text-sm font-medium text-slate-300">No QA Audit Performed Yet</h3>
            <p className="text-xs text-slate-400 max-w-md mt-1 mb-4">
              Click &quot;Run QA &amp; Security Audit&quot; to scan generated project files with AST security visitors, evaluate test coverage, and synthesize repair proposals.
            </p>
            <button
              onClick={handleRunQA}
              disabled={isRunningQA}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-mono font-medium transition-colors cursor-pointer"
            >
              {isRunningQA ? 'Running Audit...' : 'Execute Initial QA Audit'}
            </button>
          </div>
        ) : (
          <>
            {/* Top Cards: Security Score and Findings Breakdown */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              {/* Score Card */}
              <div className="p-3.5 bg-slate-900/60 border border-slate-800 rounded-lg flex flex-col justify-between">
                <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                  Security Posture
                </div>
                <div className="flex items-baseline justify-between mt-2">
                  <span
                    className={`text-2xl font-bold font-mono ${
                      score >= 80 ? 'text-emerald-400' : score >= 60 ? 'text-amber-400' : 'text-rose-400'
                    }`}
                  >
                    {score}/100
                  </span>
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                      isPassed
                        ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                        : 'bg-amber-950 text-amber-400 border border-amber-800'
                    }`}
                  >
                    {isPassed ? 'PASSED' : 'ACTION REQUIRED'}
                  </span>
                </div>
                <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                  <div
                    className={`h-full ${
                      score >= 80 ? 'bg-emerald-500' : score >= 60 ? 'bg-amber-500' : 'bg-rose-500'
                    }`}
                    style={{ width: `${score}%` }}
                  />
                </div>
              </div>

              {/* Critical Findings */}
              <div className="p-3.5 bg-slate-900/60 border border-slate-800 rounded-lg">
                <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                  Critical Vulnerabilities
                </div>
                <div className="text-2xl font-bold font-mono text-rose-400 mt-2">
                  {summary?.critical_count ?? 0}
                </div>
                <div className="text-[11px] text-slate-500 mt-1">Requires immediate remediation</div>
              </div>

              {/* High & Medium */}
              <div className="p-3.5 bg-slate-900/60 border border-slate-800 rounded-lg">
                <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                  High / Medium Issues
                </div>
                <div className="text-2xl font-bold font-mono text-amber-400 mt-2">
                  {(summary?.high_count ?? 0) + (summary?.medium_count ?? 0)}
                </div>
                <div className="text-[11px] text-slate-500 mt-1">Defects &amp; code quality risks</div>
              </div>

              {/* Resolved / Verified */}
              <div className="p-3.5 bg-slate-900/60 border border-slate-800 rounded-lg">
                <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                  Repairs Verified
                </div>
                <div className="text-2xl font-bold font-mono text-emerald-400 mt-2">
                  {summary?.resolved_count ?? 0} / {summary?.total_findings ?? 0}
                </div>
                <div className="text-[11px] text-slate-500 mt-1">Bounded repairs applied</div>
              </div>
            </div>

            {/* Test Plan Card */}
            {qaRun.test_plan && (
              <div className="p-3.5 bg-slate-900/40 border border-slate-800 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-xs font-bold font-mono text-slate-200 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                    <span>QA Agent Test Strategy ({qaRun.test_plan.test_framework})</span>
                  </h4>
                  <span className="text-[10px] font-mono text-slate-400">
                    {qaRun.test_plan.test_cases.length} Planned Scenarios
                  </span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2">
                  {qaRun.test_plan.test_cases.map((tc, idx) => (
                    <div
                      key={idx}
                      className="p-2 bg-slate-950/60 border border-slate-800/80 rounded text-xs flex flex-col justify-between"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono text-[11px] text-emerald-300 truncate">
                          {tc.file_target}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 font-mono">
                          {tc.test_type}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-1">{tc.description}</p>
                      <div className="text-[10px] text-slate-500 font-mono mt-1">
                        Coverage target: {tc.expected_coverage}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Findings List Section */}
            <div className="space-y-2">
              <div className="flex items-center justify-between pt-2">
                <h3 className="text-xs font-bold font-mono text-slate-200">
                  Audit Findings ({filteredFindings.length})
                </h3>
                <div className="flex items-center gap-1">
                  {['all', 'critical', 'high', 'medium', 'low'].map((sev) => (
                    <button
                      key={sev}
                      onClick={() => setFilterSeverity(sev)}
                      className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase transition-colors cursor-pointer ${
                        filterSeverity === sev
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                          : 'bg-slate-900 text-slate-400 border border-slate-800 hover:text-slate-200'
                      }`}
                    >
                      {sev}
                    </button>
                  ))}
                </div>
              </div>

              {filteredFindings.length === 0 ? (
                <div className="p-6 text-center border border-slate-800 rounded-lg bg-slate-900/20 text-slate-400 text-xs font-mono">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 mx-auto mb-1.5" />
                  No findings matching filter &apos;{filterSeverity}&apos;.
                </div>
              ) : (
                filteredFindings.map((finding) => (
                  <div
                    key={finding.id}
                    className="p-3.5 bg-slate-900/50 border border-slate-800 rounded-lg space-y-2.5 transition-all hover:border-slate-700"
                  >
                    {/* Finding Header */}
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-2 flex-wrap">
                        {getSeverityBadge(finding.severity)}
                        <span className="font-mono text-xs text-slate-200 flex items-center gap-1 font-semibold">
                          <FileCode className="w-3.5 h-3.5 text-slate-400" />
                          {finding.file_path}
                          {finding.line_number && (
                            <span className="text-slate-400 font-normal">
                              :L{finding.line_number}
                            </span>
                          )}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                          {finding.category}
                        </span>
                      </div>

                      {finding.status === 'resolved' ? (
                        <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950 text-emerald-300 border border-emerald-800">
                          <CheckCircle2 className="w-3 h-3 text-emerald-400" /> RESOLVED
                        </span>
                      ) : (
                        finding.proposed_code && (
                          <button
                            onClick={() => handleApplyRepair(finding)}
                            disabled={repairingFindingId === finding.id}
                            className="flex items-center gap-1 px-2.5 py-1 bg-emerald-600/90 hover:bg-emerald-500 disabled:opacity-50 text-white rounded text-xs font-mono font-medium transition-colors cursor-pointer shrink-0 shadow-sm"
                          >
                            {repairingFindingId === finding.id ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              <Wrench className="w-3 h-3" />
                            )}
                            <span>Approve &amp; Apply Repair</span>
                          </button>
                        )
                      )}
                    </div>

                    {/* Explanation */}
                    <p className="text-xs text-slate-300 leading-relaxed">
                      {finding.explanation}
                    </p>

                    {/* Evidence Snippet */}
                    {finding.evidence && (
                      <div className="bg-slate-950 border border-slate-800/80 rounded p-2 font-mono text-[11px] text-amber-300 overflow-x-auto">
                        <span className="text-[10px] text-slate-500 uppercase block mb-1">
                          Detected Pattern / Evidence:
                        </span>
                        <code>{finding.evidence}</code>
                      </div>
                    )}

                    {/* Proposed Repair Snippet */}
                    {finding.proposed_code && (
                      <div className="bg-[#080d1a] border border-emerald-900/40 rounded p-2 font-mono text-[11px] text-emerald-300 overflow-x-auto">
                        <span className="text-[10px] text-emerald-400 uppercase block mb-1 font-semibold">
                          Proposed Bounded Remediation:
                        </span>
                        <code>{finding.proposed_code}</code>
                      </div>
                    )}

                    {/* Remediation Note */}
                    <div className="text-[11px] text-slate-400 flex items-start gap-1">
                      <span className="text-emerald-400 font-medium">Recommendation:</span>
                      <span>{finding.suggested_remediation}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};
