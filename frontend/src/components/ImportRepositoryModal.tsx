import React, { useState } from 'react';
import { api } from '../services/api';
import type { ImportedRepository } from '../types/project';
import { Lock, Loader2, X } from 'lucide-react';

interface ImportRepositoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (repo: ImportedRepository) => void;
}

const GithubIcon: React.FC<{ className?: string }> = ({ className = 'w-5 h-5' }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
    <path d="M9 18c-4.51 2-5-2-7-2" />
  </svg>
);

export const ImportRepositoryModal: React.FC<ImportRepositoryModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [importUrl, setImportUrl] = useState('');
  const [importName, setImportName] = useState('');
  const [importBranch, setImportBranch] = useState('');
  const [importToken, setImportToken] = useState('');
  const [isImporting, setIsImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleImportSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!importUrl.trim()) return;

    setIsImporting(true);
    setImportError(null);
    try {
      const created = await api.importRepository({
        repo_url: importUrl.trim(),
        name: importName.trim() || undefined,
        branch: importBranch.trim() || undefined,
        access_token: importToken.trim() || undefined,
      });

      // Reset form
      setImportUrl('');
      setImportName('');
      setImportBranch('');
      setImportToken('');
      onSuccess(created);
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to import repository.';
      setImportError(msg);
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div
        className="w-full max-w-lg bg-[#0e1626] border border-slate-700/80 rounded-xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-[#090e17]">
          <div className="flex items-center gap-2 text-slate-100 font-semibold text-sm">
            <GithubIcon className="w-5 h-5 text-emerald-400" />
            <span>Import GitHub Repository</span>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleImportSubmit} className="p-6 space-y-4 text-xs font-mono">
          <div>
            <label className="block text-slate-300 mb-1.5 font-medium">
              GitHub Repository URL <span className="text-emerald-400">*</span>
            </label>
            <input
              type="url"
              required
              placeholder="https://github.com/owner/repo"
              value={importUrl}
              onChange={(e) => setImportUrl(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500 font-sans text-sm"
            />
            <span className="text-[10px] text-slate-500 mt-1 block font-sans">
              Supports public and private GitHub repositories.
            </span>
          </div>

          <div>
            <label className="block text-slate-300 mb-1.5 font-medium">
              Display Name (Optional)
            </label>
            <input
              type="text"
              placeholder="e.g. My Backend Service"
              value={importName}
              onChange={(e) => setImportName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500 font-sans text-sm"
            />
          </div>

          <div>
            <label className="block text-slate-300 mb-1.5 font-medium">
              Branch / Tag (Optional)
            </label>
            <input
              type="text"
              placeholder="main"
              value={importBranch}
              onChange={(e) => setImportBranch(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500 font-sans text-sm"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-slate-300 flex items-center gap-1 font-medium">
                <Lock className="w-3 h-3 text-amber-400" />
                Personal Access Token (For Private Repos)
              </label>
            </div>
            <input
              type="password"
              placeholder="ghp_xxxxxxxxxxxx"
              value={importToken}
              onChange={(e) => setImportToken(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500 font-sans text-sm"
            />
            <span className="text-[10px] text-slate-500 mt-1 block leading-relaxed font-sans">
              Never enter passwords. Scoped Personal Access Tokens are used transiently to fetch files and are never saved or logged.
            </span>
          </div>

          {importError && (
            <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-500/30 text-rose-300 text-xs font-sans">
              {importError}
            </div>
          )}

          <div className="pt-2 flex justify-end gap-2 font-sans">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isImporting}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-slate-950 text-xs font-semibold transition-colors disabled:opacity-50 cursor-pointer"
            >
              {isImporting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Importing...</span>
                </>
              ) : (
                <span>Import & Index</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
