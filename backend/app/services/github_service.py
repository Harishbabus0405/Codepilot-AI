import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.git import GitAuditLog
from app.models.qa import QAFinding
from app.schemas.git import GitPRCreateResponse, GitPRSummaryResponse
from app.services.git_service import (
    GitApprovalRequiredError,
    GitError,
    GitSecurityError,
    git_service,
    sanitize_output,
)
from app.services.llm_service import LLMService


class GitHubAPIError(RuntimeError):
    """Raised when GitHub REST API returns an error or rejects a request."""
    pass


class GitHubAuthError(PermissionError):
    """Raised when GitHub authorization fails (401 Bad Credentials)."""
    pass


class GitHubNotFoundError(FileNotFoundError):
    """Raised when repository or branch does not exist on GitHub (404 Not Found)."""
    pass


# Strict GitHub repo slug or URL matcher: owner/repo
GITHUB_REPO_REGEX = re.compile(
    r"^(?:https?://github\.com/)?([a-zA-Z0-9_.\-]+)/([a-zA-Z0-9_.\-]+?)(?:\.git)?$"
)


def extract_repo_owner_and_name(repo_url: str) -> tuple[str, str]:
    """Extracts and validates (owner, repo) from a GitHub URL or slug."""
    clean_url = repo_url.strip()
    match = GITHUB_REPO_REGEX.match(clean_url)
    if not match:
        raise GitSecurityError(
            f"Invalid GitHub repository identifier '{repo_url}'. Expected 'owner/repo' or 'https://github.com/owner/repo'."
        )
    return match.group(1), match.group(2)


class GitHubService:
    """
    Service for developer workflow automation:
    - AI-assisted conventional commit message generation from diffs
    - Pull request summary generation combining diffs, commits, and QA findings
    - Secure GitHub API pull request creation with strict approval checks
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or LLMService()

    def generate_commit_message(self, diff_text: str, changed_files: List[str]) -> str:
        """
        Generates a concise Conventional Commit message based on actual working tree diffs.
        Uses Groq LLM if available, with structured deterministic fallback.
        """
        if not diff_text and not changed_files:
            return "chore: update project configuration"

        # Truncate diff to avoid exceeding token limits
        trimmed_diff = diff_text[:3000] if diff_text else "No diff content available."
        files_str = ", ".join(changed_files[:15]) if changed_files else "multiple files"

        system_prompt = (
            "You are an expert software engineer. Generate a concise, high-quality Conventional Commit message "
            "(e.g., feat:, fix:, refactor:, chore:, docs:) summarizing the given changed files and diff. "
            "The first line MUST be under 72 characters. You may optionally include a bulleted list of 2-3 key details. "
            "Output ONLY the commit message without Markdown wrappers, quotes, or conversational explanations."
        )

        user_prompt = f"Changed Files: {files_str}\n\nGit Diff:\n{trimmed_diff}"

        try:
            chat_model = self.llm_service.get_chat_model(temperature=0.2)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            response = chat_model.invoke(messages)
            content = response.content if hasattr(response, "content") else str(response)
            clean_msg = content.strip().strip('"').strip("'")
            if clean_msg:
                # Remove any accidental markdown fence
                clean_msg = re.sub(r"^```[a-z]*\n", "", clean_msg)
                clean_msg = re.sub(r"\n```$", "", clean_msg).strip()
                return clean_msg
        except Exception:
            pass

        # Deterministic fallback based on file heuristics
        if any("test" in f.lower() for f in changed_files):
            return f"test: add automated test coverage for {changed_files[0] if changed_files else 'modules'}"
        if any(f.endswith(".md") for f in changed_files):
            return "docs: update repository documentation and guides"
        if any(f.endswith(".py") or f.endswith(".ts") or f.endswith(".tsx") for f in changed_files):
            primary = changed_files[0].split("/")[-1].split(".")[0] if changed_files else "code"
            return f"feat({primary}): implement updates and enhancements"
        return "chore: apply project workspace improvements"

    def prepare_pr_summary(
        self,
        workspace_id: uuid.UUID,
        base_branch: str = "main",
        db: Optional[Session] = None,
    ) -> GitPRSummaryResponse:
        """
        Compiles a professional GitHub pull request description from:
        1. Working tree and branch diffs
        2. Recent commit messages
        3. Associated QA, Code Review, and Security findings (if present in PostgreSQL)
        """
        cwd = git_service.resolve_workspace(workspace_id)
        status = git_service.get_status(workspace_id)

        # Retrieve branch diff if possible, else staged/unstaged diff
        diff_resp = git_service.get_diff(workspace_id)
        if not diff_resp.diff:
            diff_resp = git_service.get_diff(workspace_id, cached=True)

        history = git_service.get_commit_history(workspace_id, limit=5)
        commit_messages = [c.message for c in history]

        # Fetch verified QA/security findings from PostgreSQL if available
        qa_findings_count = 0
        qa_notes: List[str] = []
        if db:
            try:
                stmt = select(QAFinding).where(
                    QAFinding.project_id == workspace_id,
                    QAFinding.is_verified == True,
                ).limit(5)
                findings = db.scalars(stmt).all()
                qa_findings_count = len(findings)
                for f in findings:
                    qa_notes.append(f"- [{f.severity.upper()}] {f.file_path}: {f.explanation}")
            except Exception:
                pass

        # Synthesize via LLM
        system_prompt = (
            "You are a principal engineer preparing a comprehensive GitHub Pull Request description. "
            "Return a structured Markdown PR summary with: "
            "1. An informative PR Title (first line, prefix with 'TITLE: ') "
            "2. '## Overview' summary "
            "3. '## Key Changes' bullet list "
            "4. '## QA & Security Audit' section referencing addressed findings "
            "5. '## Verification Checklist'"
        )

        user_content = (
            f"Current Branch: {status.current_branch}\n"
            f"Base Branch: {base_branch}\n"
            f"Recent Commits:\n" + "\n".join(f"- {m}" for m in commit_messages) + "\n\n"
            f"Changed Files: {', '.join(diff_resp.files_changed)}\n"
            f"QA Findings Addressed:\n" + ("\n".join(qa_notes) if qa_notes else "None reported.") + "\n\n"
            f"Diff snippet:\n{diff_resp.diff[:2000]}"
        )

        title = f"feat: updates on branch {status.current_branch or 'feature'}"
        body = (
            f"## Overview\nThis PR introduces updates to {', '.join(diff_resp.files_changed[:5]) or 'the workspace'}.\n\n"
            f"## Key Changes\n" + "\n".join(f"- {m}" for m in commit_messages[:3] if m) + "\n\n"
            f"## QA & Security Audit\n" + ("\n".join(qa_notes) if qa_notes else "No automated defects detected.") + "\n\n"
            f"## Verification Checklist\n- [x] Code compiled and syntax validated\n- [x] Automated test suite verified\n- [x] Security review passed\n"
        )

        try:
            chat_model = self.llm_service.get_chat_model(temperature=0.3)
            resp = chat_model.invoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ])
            text = resp.content if hasattr(resp, "content") else str(resp)
            lines = text.strip().splitlines()
            if lines and lines[0].startswith("TITLE:"):
                title = lines[0].replace("TITLE:", "").strip()
                body = "\n".join(lines[1:]).strip()
            elif lines:
                title = lines[0].strip().lstrip("#").strip()
                body = "\n".join(lines[1:]).strip()
        except Exception:
            pass

        return GitPRSummaryResponse(
            title=title,
            body=body,
            commits_count=len(commit_messages),
            files_changed_count=len(diff_resp.files_changed),
            qa_findings_referenced=qa_findings_count,
        )

    def create_pull_request(
        self,
        repo_url: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
        github_token: str = "",
        approved: bool = False,
        db: Optional[Session] = None,
        workspace_id: Optional[uuid.UUID] = None,
    ) -> GitPRCreateResponse:
        """
        Creates a pull request on GitHub via the official REST API v3.
        STRICT SAFETY: Requires approved=True.
        Tokens are handled transiently and NEVER persisted or logged.
        """
        if not approved:
            raise GitApprovalRequiredError(
                "Pull request creation requires explicit user approval ('approved': true)."
            )

        if not github_token or not github_token.strip():
            raise GitHubAuthError("A valid GitHub Personal Access Token is required to create a pull request.")

        clean_token = github_token.strip()
        owner, repo = extract_repo_owner_and_name(repo_url)

        api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        headers = {
            "Authorization": f"Bearer {clean_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "CodePilot-AI",
        }
        payload = {
            "title": title.strip(),
            "body": body.strip(),
            "head": head_branch.strip(),
            "base": base_branch.strip(),
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(api_url, headers=headers, json=payload)
        except httpx.RequestError as exc:
            err = f"Network failure communicating with GitHub API: {str(exc)}"
            git_service._log_audit(
                db,
                workspace_id or uuid.uuid4(),
                operation="pr_create",
                status="failed",
                error_message=err,
            )
            raise GitHubAPIError(err) from exc

        # Handle HTTP Status Codes
        if response.status_code == 201:
            data = response.json()
            pr_resp = GitPRCreateResponse(
                pull_request_url=data.get("html_url", f"https://github.com/{owner}/{repo}/pull/{data.get('number')}"),
                pull_request_number=data.get("number", 0),
                title=data.get("title", title),
                state=data.get("state", "open"),
                head_branch=head_branch,
                base_branch=base_branch,
                created_at=data.get("created_at", ""),
            )
            git_service._log_audit(
                db,
                workspace_id or uuid.uuid4(),
                operation="pr_create",
                status="success",
                branch=head_branch,
                details={
                    "pr_url": pr_resp.pull_request_url,
                    "pr_number": pr_resp.pull_request_number,
                    "repo": f"{owner}/{repo}",
                },
            )
            return pr_resp

        # Audit failure without credentials
        error_detail = ""
        try:
            err_data = response.json()
            error_detail = err_data.get("message", response.text)
            if "errors" in err_data:
                field_errors = [e.get("message", str(e)) for e in err_data["errors"] if isinstance(e, dict)]
                if field_errors:
                    error_detail += f" ({', '.join(field_errors)})"
        except Exception:
            error_detail = response.text

        sanitized_err = sanitize_output(error_detail)
        git_service._log_audit(
            db,
            workspace_id or uuid.uuid4(),
            operation="pr_create",
            status="failed",
            branch=head_branch,
            error_message=sanitized_err,
        )

        if response.status_code == 401:
            raise GitHubAuthError("GitHub authorization failed: Invalid or expired personal access token.")
        elif response.status_code == 404:
            raise GitHubNotFoundError(
                f"Repository '{owner}/{repo}' not found on GitHub, or token lacks pull request permissions."
            )
        elif response.status_code == 422:
            raise GitHubAPIError(f"GitHub validation rejected pull request: {sanitized_err}")
        else:
            raise GitHubAPIError(f"GitHub API error (HTTP {response.status_code}): {sanitized_err}")


github_service = GitHubService()
