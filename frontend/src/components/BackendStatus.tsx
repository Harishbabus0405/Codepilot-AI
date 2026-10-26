import React from 'react';
import type { ConnectionStatus, HealthResponse } from '../types/project';
import { RefreshCw } from 'lucide-react';

interface BackendStatusProps {
  status: ConnectionStatus;
  health: HealthResponse | null;
  onRefresh: () => void;
  isChecking: boolean;
}

export const BackendStatus: React.FC<BackendStatusProps> = ({
  status,
  health,
  onRefresh,
  isChecking,
}) => {
  return (
    <div className="flex items-center gap-3 px-3 py-1.5 rounded-full bg-slate-900/90 border border-slate-800 text-xs shadow-sm">
      <div className="flex items-center gap-2">
        <span className="relative flex h-2 w-2">
          {status === 'connected' && (
            <>
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </>
          )}
          {status === 'checking' && (
            <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-400 animate-pulse"></span>
          )}
          {status === 'disconnected' && (
            <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
          )}
        </span>

        <span className="font-medium text-slate-300">
          {status === 'connected' && 'Backend Connected'}
          {status === 'checking' && 'Connecting...'}
          {status === 'disconnected' && 'Backend Disconnected'}
        </span>

        {status === 'connected' && health && (
          <span className="text-slate-500 text-[11px] hidden sm:inline border-l border-slate-800 pl-2">
            DB: <span className={health.database === 'connected' ? 'text-emerald-400' : 'text-amber-400'}>{health.database}</span>
          </span>
        )}
      </div>

      <button
        onClick={onRefresh}
        disabled={isChecking}
        title="Check connection"
        aria-label="Refresh backend connection"
        className="text-slate-400 hover:text-emerald-400 transition-colors p-0.5 rounded focus:outline-none disabled:opacity-50"
      >
        <RefreshCw className={`w-3.5 h-3.5 ${isChecking ? 'animate-spin text-emerald-400' : ''}`} />
      </button>
    </div>
  );
};
