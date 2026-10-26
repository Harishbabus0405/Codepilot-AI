from datetime import datetime, timezone
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.git import GitAuditLog
from app.schemas.git import (
    GitBranchListResponse,
    GitBranchResponse,
    GitCommitInfo,
    GitCommitResponse,
    GitDiffResponse,
    GitFileChange,
    GitStatusResponse,
)


class GitSecurityError(ValueError):
    """Raised when an unsafe path, forbidden directory, or dangerous argument is detected."""
    pass


class GitApprovalRequiredError(PermissionError):
    """Raised when an operation requiring explicit approval is attempted without approved=True."""
    pass


class GitError(RuntimeError):
    """Raised when a git CLI command fails."""
    pass


# Strict branch name validator: alphanumeric, hyphens, underscores, dots, slashes
# Cannot start/end with dot or slash, cannot contain consecutive dots or slashes
BRANCH_REGEX = re.compile(r"^(?!/)(?!.*//)(?!.*\.\.)[a-zA-Z0-9_.\-/]+(?<!/)$")


def sanitize_output(text: str) -> str:
    """Removes sensitive credentials or tokens from git output strings."""
    if not text:
        return ""
    # Redact URL credentials: https://token@github.com -> https://***@github.com
    sanitized = re.sub(r"https?://([^:@\s]+)(:[^@\s]+)?@github\.com", "https://***@github.com", text)
    # Redact GitHub classic and fine-grained PAT tokens
    sanitized = re.sub(r"ghp_[a-zA-Z0-9]{36}", "ghp_***", sanitized)
    sanitized = re.sub(r"github_pat_[a-zA-Z0-9_]{82}", "github_pat_***", sanitized)
    return sanitized


class GitService:
    """
    Dedicated Git workspace management service.
    Enforces repository isolation, input sanitization, and explicit approval guardrails.
    """

    def __init__(self):
        self.gen_dir = Path(settings.GENERATED_PROJECTS_DIR).resolve()
        self.import_dir = Path(settings.IMPORTED_REPOS_DIR).resolve()
        self.gen_dir.mkdir(parents=True, exist_ok=True)
        self.import_dir.mkdir(parents=True, exist_ok=True)

        # CodePilot's own root directory to prevent accidental contamination
        self.app_root = Path(__file__).resolve().parent.parent.parent.parent

    def resolve_workspace(self, workspace_id: uuid.UUID) -> Path:
        """
        Resolves the workspace directory for a project or imported repository.
        Enforces strict boundary isolation against CodePilot's own repository.
        """
        str_id = str(workspace_id)
        candidate_gen = (self.gen_dir / str_id).resolve()
        candidate_import = (self.import_dir / str_id).resolve()

        if candidate_gen.exists() and candidate_gen.is_dir():
            target_path = candidate_gen
        elif candidate_import.exists() and candidate_import.is_dir():
            target_path = candidate_import
        else:
            # Default to generated project directory
            target_path = candidate_gen

        # Validate security boundaries
        is_in_gen = target_path.is_relative_to(self.gen_dir) and target_path != self.gen_dir
        is_in_import = target_path.is_relative_to(self.import_dir) and target_path != self.import_dir

        if not (is_in_gen or is_in_import):
            raise GitSecurityError(f"Target workspace {workspace_id} resolves outside allowed workspace boundaries.")

        if target_path == self.app_root or self.app_root in target_path.parents or target_path in self.app_root.parents:
            # Only allowed if strictly a descendant of generated_projects or imported_repositories
            if not (is_in_gen or is_in_import):
                raise GitSecurityError("Target workspace conflicts with CodePilot AI's own source repository.")

        target_path.mkdir(parents=True, exist_ok=True)
        return target_path

    def _run_git(
        self,
        cwd: Path,
        args: List[str],
        timeout: float = 15.0,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        Executes a git command in the target workspace.
        Never invokes a shell. Strips credentials from outputs and logs.
        """
        cmd = ["git", *args]
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GIT_ASKPASS"] = ""

        try:
            result = subprocess.run(
                cmd,
                cwd=str(cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
                env=env,
            )
            if check and result.returncode != 0:
                err_msg = sanitize_output(result.stderr.strip() or result.stdout.strip())
                raise GitError(f"Git command failed ('git {' '.join(args)}'): {err_msg}")
            return result
        except subprocess.TimeoutExpired as exc:
            raise GitError(f"Git command timed out after {timeout}s: {' '.join(args)}") from exc
        except FileNotFoundError as exc:
            raise GitError("git executable not found on host system.") from exc

    def _log_audit(
        self,
        db: Optional[Session],
        workspace_id: uuid.UUID,
        operation: str,
        status: str,
        branch: Optional[str] = None,
        commit_sha: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ):
        """Records an audit log entry for this Git operation if a database session is provided."""
        if not db:
            return
        try:
            audit = GitAuditLog(
                project_id=workspace_id,
                operation=operation,
                branch=branch,
                commit_sha=commit_sha,
                details=details,
                status=status,
                error_message=sanitize_output(error_message) if error_message else None,
            )
            db.add(audit)
            db.commit()
        except Exception:
            db.rollback()

    def init_repository(self, workspace_id: uuid.UUID, db: Optional[Session] = None) -> GitStatusResponse:
        """
        Initializes a Git repository in the target workspace with safe defaults.
        """
        cwd = self.resolve_workspace(workspace_id)
        dot_git = cwd / ".git"

        if not dot_git.is_dir():
            self._run_git(cwd, ["init", "-b", "main"])

            # Configure isolated local identity for this workspace
            self._run_git(cwd, ["config", "user.name", "CodePilot AI"])
            self._run_git(cwd, ["config", "user.email", "codepilot@local"])

            # Ensure baseline .gitignore exists
            gitignore_path = cwd / ".gitignore"
            if not gitignore_path.exists():
                gitignore_content = (
                    "# Generated by CodePilot AI\n"
                    "node_modules/\n"
                    "__pycache__/\n"
                    "*.pyc\n"
                    ".env\n"
                    ".venv/\n"
                    "venv/\n"
                    "dist/\n"
                    "build/\n"
                    ".DS_Store\n"
                    "Thumbs.db\n"
                )
                gitignore_path.write_text(gitignore_content, encoding="utf-8")

            self._log_audit(
                db,
                workspace_id,
                operation="init",
                status="success",
                branch="main",
                details={"workspace": str(cwd)},
            )

        return self.get_status(workspace_id)

    def get_status(self, workspace_id: uuid.UUID) -> GitStatusResponse:
        """
        Inspects the current working tree, staged, unstaged, and untracked changes.
        """
        cwd = self.resolve_workspace(workspace_id)
        dot_git = cwd / ".git"

        if not dot_git.is_dir():
            return GitStatusResponse(is_git_repo=False, is_clean=True)

        # Get current branch
        branch_proc = self._run_git(cwd, ["branch", "--show-current"], check=False)
        current_branch = branch_proc.stdout.strip()
        if not current_branch:
            # Fallback to rev-parse if unborn or detached
            rev_proc = self._run_git(cwd, ["rev-parse", "--abbrev-ref", "HEAD"], check=False)
            current_branch = rev_proc.stdout.strip() or "main"

        # Get status porcelain
        status_proc = self._run_git(cwd, ["status", "--porcelain=v1", "-u"], check=True)
        lines = status_proc.stdout.splitlines()

        staged_files: List[GitFileChange] = []
        unstaged_files: List[GitFileChange] = []
        untracked_files: List[str] = []

        status_map = {
            "M": "modified",
            "A": "added",
            "D": "deleted",
            "R": "renamed",
            "C": "copied",
            "?": "untracked",
        }

        for line in lines:
            if not line or len(line) < 3:
                continue
            x = line[0]
            y = line[1]
            file_path = line[3:].strip()

            if x == "?" and y == "?":
                untracked_files.append(file_path)
            else:
                if x in status_map and x != " ":
                    staged_files.append(
                        GitFileChange(path=file_path, status=status_map[x], staged=True)
                    )
                if y in status_map and y != " ":
                    unstaged_files.append(
                        GitFileChange(path=file_path, status=status_map[y], staged=False)
                    )

        total_changes = len(staged_files) + len(unstaged_files) + len(untracked_files)
        is_clean = total_changes == 0

        # Latest commit
        latest_commit = None
        log_proc = self._run_git(
            cwd,
            ["log", "-1", "--pretty=format:%H%x00%s%x00%an%x00%aI"],
            check=False,
        )
        if log_proc.returncode == 0 and log_proc.stdout.strip():
            parts = log_proc.stdout.strip().split("\x00")
            if len(parts) >= 4:
                latest_commit = GitCommitInfo(
                    sha=parts[0],
                    message=parts[1],
                    author=parts[2],
                    date=parts[3],
                )

        return GitStatusResponse(
            is_git_repo=True,
            current_branch=current_branch,
            is_clean=is_clean,
            staged_files=staged_files,
            unstaged_files=unstaged_files,
            untracked_files=untracked_files,
            total_changes=total_changes,
            latest_commit=latest_commit,
        )

    def get_diff(
        self,
        workspace_id: uuid.UUID,
        cached: bool = False,
        file_path: Optional[str] = None,
    ) -> GitDiffResponse:
        """
        Retrieves unified diffs for staged or unstaged working tree changes.
        """
        cwd = self.resolve_workspace(workspace_id)
        dot_git = cwd / ".git"

        if not dot_git.is_dir():
            return GitDiffResponse(diff="", files_changed=[], insertions=0, deletions=0)

        args = ["diff"]
        if cached:
            args.append("--cached")

        if file_path:
            # Validate safe relative path
            clean_fp = file_path.strip()
            if clean_fp.startswith(("/", "\\", "-")) or ".." in clean_fp:
                raise GitSecurityError(f"Invalid file path: {file_path}")
            args.extend(["--", clean_fp])

        diff_proc = self._run_git(cwd, args, check=False)
        diff_text = sanitize_output(diff_proc.stdout)

        # Get diff stat
        stat_args = ["diff", "--numstat"]
        if cached:
            stat_args.append("--cached")
        if file_path:
            stat_args.extend(["--", clean_fp])

        stat_proc = self._run_git(cwd, stat_args, check=False)
        files_changed = []
        insertions = 0
        deletions = 0

        for line in stat_proc.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) >= 3:
                ins = int(parts[0]) if parts[0].isdigit() else 0
                dels = int(parts[1]) if parts[1].isdigit() else 0
                fn = parts[2]
                files_changed.append(fn)
                insertions += ins
                deletions += dels

        return GitDiffResponse(
            diff=diff_text,
            files_changed=files_changed,
            insertions=insertions,
            deletions=deletions,
        )

    def create_commit(
        self,
        workspace_id: uuid.UUID,
        message: str,
        files: Optional[List[str]] = None,
        approved: bool = False,
        db: Optional[Session] = None,
    ) -> GitCommitResponse:
        """
        Commits changes in the workspace.
        STRICT SAFETY: Requires approved=True. Never commits without user confirmation.
        """
        if not approved:
            raise GitApprovalRequiredError(
                "Commit requires explicit user approval ('approved': true)."
            )

        if not message or not message.strip():
            raise ValueError("Commit message cannot be empty.")

        clean_message = message.strip()
        cwd = self.resolve_workspace(workspace_id)
        self.init_repository(workspace_id, db)

        # Stage files
        if files:
            for f in files:
                clean_f = f.strip()
                if clean_f.startswith(("/", "\\", "-")) or ".." in clean_f:
                    raise GitSecurityError(f"Unsafe file path rejected: {f}")
                self._run_git(cwd, ["add", "--", clean_f])
        else:
            self._run_git(cwd, ["add", "-A"])

        # Check if anything is staged
        status = self.get_status(workspace_id)
        if not status.staged_files:
            raise GitError("No staged changes to commit.")

        # Execute commit
        self._run_git(cwd, ["commit", "-m", clean_message])

        # Get commit SHA and branch
        sha_proc = self._run_git(cwd, ["rev-parse", "HEAD"])
        commit_sha = sha_proc.stdout.strip()
        branch = status.current_branch or "main"

        self._log_audit(
            db,
            workspace_id,
            operation="commit",
            status="success",
            branch=branch,
            commit_sha=commit_sha,
            details={
                "message": clean_message,
                "files_committed": len(status.staged_files),
            },
        )

        return GitCommitResponse(
            commit_sha=commit_sha,
            branch=branch,
            message=clean_message,
            files_committed=len(status.staged_files),
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def list_branches(self, workspace_id: uuid.UUID) -> GitBranchListResponse:
        """Lists local branches and returns current active branch."""
        cwd = self.resolve_workspace(workspace_id)
        dot_git = cwd / ".git"

        if not dot_git.is_dir():
            return GitBranchListResponse(current_branch="main", branches=["main"])

        proc = self._run_git(cwd, ["branch", "--list"], check=False)
        branches = []
        current_branch = "main"

        for line in proc.stdout.splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            if cleaned.startswith("* "):
                name = cleaned[2:].strip()
                current_branch = name
                branches.append(name)
            else:
                branches.append(cleaned)

        if not branches:
            branches = [current_branch]

        return GitBranchListResponse(current_branch=current_branch, branches=branches)

    def create_branch(
        self,
        workspace_id: uuid.UUID,
        branch_name: str,
        checkout: bool = True,
        db: Optional[Session] = None,
    ) -> GitBranchResponse:
        """
        Creates a new branch with input validation.
        Rejects invalid flags, path traversals, or dangerous tokens.
        """
        clean_name = branch_name.strip()
        if not BRANCH_REGEX.match(clean_name) or clean_name.startswith("-") or len(clean_name) > 100:
            raise GitSecurityError(
                f"Invalid branch name '{branch_name}'. Use alphanumeric, underscores, hyphens, and slashes."
            )

        cwd = self.resolve_workspace(workspace_id)
        self.init_repository(workspace_id, db)

        args = ["checkout", "-b", clean_name] if checkout else ["branch", clean_name]
        self._run_git(cwd, args)

        self._log_audit(
            db,
            workspace_id,
            operation="branch_create",
            status="success",
            branch=clean_name,
            details={"checkout": checkout},
        )

        return GitBranchResponse(
            current_branch=clean_name if checkout else self.get_status(workspace_id).current_branch or clean_name,
            message=f"Branch '{clean_name}' created successfully.",
        )

    def checkout_branch(
        self,
        workspace_id: uuid.UUID,
        branch_name: str,
        db: Optional[Session] = None,
    ) -> GitBranchResponse:
        """Switches to an existing branch."""
        clean_name = branch_name.strip()
        if not BRANCH_REGEX.match(clean_name) or clean_name.startswith("-"):
            raise GitSecurityError(f"Invalid branch name '{branch_name}'.")

        cwd = self.resolve_workspace(workspace_id)
        self._run_git(cwd, ["checkout", clean_name])

        self._log_audit(
            db,
            workspace_id,
            operation="checkout",
            status="success",
            branch=clean_name,
        )

        return GitBranchResponse(
            current_branch=clean_name,
            message=f"Switched to branch '{clean_name}'.",
        )

    def get_commit_history(self, workspace_id: uuid.UUID, limit: int = 10) -> List[GitCommitInfo]:
        """Returns the recent commit history for the current branch."""
        cwd = self.resolve_workspace(workspace_id)
        dot_git = cwd / ".git"

        if not dot_git.is_dir():
            return []

        proc = self._run_git(
            cwd,
            ["log", f"-n{max(1, min(limit, 50))}", "--pretty=format:%H%x00%s%x00%an%x00%aI"],
            check=False,
        )

        commits = []
        for line in proc.stdout.splitlines():
            parts = line.strip().split("\x00")
            if len(parts) >= 4:
                commits.append(
                    GitCommitInfo(
                        sha=parts[0],
                        message=parts[1],
                        author=parts[2],
                        date=parts[3],
                    )
                )
        return commits


git_service = GitService()
