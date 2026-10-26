import io
import logging
import os
from pathlib import Path
import re
import shutil
import tarfile
from typing import Dict, List, Optional, Tuple
import uuid
import zipfile

import httpx

from app.config.settings import settings
from app.services.chunking_service import chunker
from app.services.storage_service import PathTraversalError, storage_service
from app.services.vector_service import vector_service

logger = logging.getLogger(__name__)

# Excluded directory names
EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "env",
    "__pycache__",
    "dist",
    "build",
    "target",
    ".next",
    "out",
    ".nuxt",
    ".idea",
    ".vscode",
    "vendor",
    ".tox",
    "coverage",
    ".pytest_cache",
}

# Excluded binary and archive file extensions
EXCLUDED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
    ".pdf", ".zip", ".tar", ".gz", ".7z", ".rar",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".wasm",
    ".pyc", ".pyo", ".pyd", ".whl",
    ".db", ".sqlite", ".sqlite3", ".parquet",
    ".mp3", ".mp4", ".mov", ".wav",
    ".ttf", ".woff", ".woff2", ".eot",
}

# Excluded sensitive and secret file patterns
EXCLUDED_SECRET_FILES = {
    ".env", ".env.local", ".env.production", ".env.development",
    "id_rsa", "id_ed25519", "credentials.json", "secrets.json",
}


class RepoValidationError(ValueError):
    """Raised when repository URL or inputs are invalid."""
    pass


class RepoImportService:
    """
    Manages GitHub repository validation, secure download, filtering of untrusted files,
    file scanning, and dispatching to chunking & FAISS vector indexing.
    """

    def __init__(self, base_dir: Optional[str] = None):
        raw_base = base_dir or settings.IMPORTED_REPOS_DIR
        self.base_dir = Path(raw_base).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def validate_github_url(url: str) -> Tuple[str, str, str]:
        """
        Validates that a URL is a legitimate GitHub HTTPS repository URL.
        Rejects non-GitHub domains, unsupported schemes, and invalid characters.
        Returns: (normalized_url, owner, repo_name)
        """
        if not url or not url.strip():
            raise RepoValidationError("Repository URL cannot be empty.")

        cleaned = url.strip()

        # Strict regex matching: https://github.com/{owner}/{repo}
        pattern = r"^https:\/\/github\.com\/([a-zA-Z0-9_\-\.]+)\/([a-zA-Z0-9_\-\.]+?)(?:\.git|\/)?$"
        match = re.match(pattern, cleaned)
        if not match:
            raise RepoValidationError(
                f"Invalid or unsupported repository URL: '{url}'. "
                "Only standard HTTPS GitHub repository URLs are supported (e.g. 'https://github.com/owner/repo')."
            )

        owner = match.group(1)
        repo_name = match.group(2)

        if not owner or not repo_name:
            raise RepoValidationError("GitHub repository owner and repository name are required.")

        # Disallow dot navigation in names
        if ".." in owner or ".." in repo_name or "/" in owner or "/" in repo_name:
            raise RepoValidationError("Illegal path traversal sequence in repository name.")

        normalized_url = f"https://github.com/{owner}/{repo_name}"
        return normalized_url, owner, repo_name

    def get_repo_workspace(self, repo_id: uuid.UUID) -> Path:
        """Returns the isolated disk directory for the repository's files."""
        repo_dir = (self.base_dir / str(repo_id)).resolve()
        if not repo_dir.is_relative_to(self.base_dir):
            raise PathTraversalError(f"Access denied: {repo_id}")
        repo_dir.mkdir(parents=True, exist_ok=True)
        return repo_dir

    def is_file_allowed(self, rel_path: str, file_size: int) -> bool:
        """
        Checks whether a file should be included in the knowledge index.
        Applies strict filtering for excluded directories, binaries, secrets, and size limits.
        """
        parts = Path(rel_path).parts
        # 1. Directory exclusion check
        for part in parts[:-1]:
            if part.lower() in EXCLUDED_DIRS or part.startswith("."):
                return False

        file_name = parts[-1].lower() if parts else ""

        # 2. Secret file check
        if file_name in EXCLUDED_SECRET_FILES or file_name.startswith(".env"):
            return False
        if file_name.endswith((".pem", ".key", ".pfx", ".cer", ".crt")):
            return False

        # 3. Extension check
        ext = os.path.splitext(file_name)[1]
        if ext in EXCLUDED_EXTENSIONS:
            return False

        # 4. Size limit check
        if file_size > settings.MAX_FILE_SIZE_BYTES or file_size == 0:
            return False

        return True

    def scan_workspace(self, repo_id: uuid.UUID) -> List[Dict[str, str]]:
        """
        Scans the imported repository workspace and reads allowable text files.
        Enforces maximum file count and total repository byte limits.
        """
        repo_dir = self.get_repo_workspace(repo_id)
        scanned_files: List[Dict[str, str]] = []
        total_bytes = 0

        for root, dirs, files in os.walk(repo_dir):
            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_DIRS and not d.startswith(".")]

            for file_name in files:
                full_path = Path(root) / file_name
                try:
                    rel_path = full_path.relative_to(repo_dir).as_posix()
                    file_size = full_path.stat().st_size

                    if not self.is_file_allowed(rel_path, file_size):
                        continue

                    if total_bytes + file_size > settings.MAX_TOTAL_REPO_BYTES:
                        logger.warning("Repository size limit reached (%d bytes). Stopping scan.", total_bytes)
                        break

                    if len(scanned_files) >= settings.MAX_REPO_FILES:
                        logger.warning("Repository max file count reached (%d files). Stopping scan.", len(scanned_files))
                        break

                    # Read text content safely
                    content = full_path.read_text(encoding="utf-8", errors="replace")
                    scanned_files.append({
                        "path": rel_path,
                        "content": content,
                        "language": storage_service.detect_language(rel_path),
                        "size": file_size,
                    })
                    total_bytes += file_size

                except Exception as exc:
                    logger.debug("Skipping unreadable file %s: %s", full_path, exc)

            if len(scanned_files) >= settings.MAX_REPO_FILES or total_bytes >= settings.MAX_TOTAL_REPO_BYTES:
                break

        return scanned_files

    def fetch_repository(
        self,
        repo_id: uuid.UUID,
        owner: str,
        repo_name: str,
        branch: Optional[str] = None,
        access_token: Optional[str] = None,
    ) -> int:
        """
        Downloads the repository archive from GitHub API without executing external commands.
        Unpacks files safely into the isolated repository workspace.
        Never logs or stores the access token.
        """
        repo_dir = self.get_repo_workspace(repo_id)

        # Clean existing files if re-importing
        for item in repo_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)

        ref = branch.strip() if branch and branch.strip() else ""
        url = f"https://api.github.com/repos/{owner}/{repo_name}/tarball/{ref}"

        headers = {
            "User-Agent": "CodePilot-AI",
            "Accept": "application/vnd.github.v3+json",
        }
        # Provide token if supplied for private repository authorization
        if access_token and access_token.strip():
            headers["Authorization"] = f"Bearer {access_token.strip()}"

        timeout = httpx.Timeout(float(settings.REPO_IMPORT_TIMEOUT_SECONDS), connect=10.0)

        with httpx.Client(headers=headers, timeout=timeout, follow_redirects=True) as client:
            response = client.get(url)

            if response.status_code == 404:

                raise RepoValidationError(
                    f"Repository '{owner}/{repo_name}' not found or is private. "
                    "If it is private, provide a valid GitHub Personal Access Token."
                )
            elif response.status_code == 401:
                raise RepoValidationError("GitHub authentication failed. Check your access token.")
            elif response.status_code == 403:
                raise RepoValidationError("GitHub API rate limit exceeded or access forbidden.")
            elif response.status_code != 200:
                raise RepoValidationError(f"GitHub archive download failed with HTTP {response.status_code}.")

            archive_bytes = response.content

        # Unpack tarball safely
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:*") as tar:
            members = tar.getmembers()
            # GitHub tarball wraps everything in a top-level directory like "owner-repo-commit"
            common_prefix = ""
            if members:
                first_part = members[0].name.split("/")[0]
                common_prefix = f"{first_part}/"

            extracted_count = 0
            for member in members:
                if not member.isfile():
                    continue

                rel_name = member.name
                if common_prefix and rel_name.startswith(common_prefix):
                    rel_name = rel_name[len(common_prefix):]

                if not rel_name:
                    continue

                # Safety check: prevent path traversal from malicious archives
                dest_file = (repo_dir / rel_name).resolve()
                if not dest_file.is_relative_to(repo_dir):
                    logger.warning("Skipping malicious tar member escaping workspace: %s", member.name)
                    continue

                if not self.is_file_allowed(rel_name, member.size):
                    continue

                dest_file.parent.mkdir(parents=True, exist_ok=True)
                file_obj = tar.extractfile(member)
                if file_obj:
                    dest_file.write_bytes(file_obj.read())
                    extracted_count += 1

                if extracted_count >= settings.MAX_REPO_FILES:
                    break

        logger.info("Successfully extracted %d files for repo %s/%s", extracted_count, owner, repo_name)
        return extracted_count

    def delete_repository(self, repo_id: uuid.UUID) -> bool:
        """Deletes both workspace files and vector index for a repository."""
        # 1. Delete vector index
        vector_service.delete_index(repo_id)

        # 2. Delete workspace files
        repo_dir = (self.base_dir / str(repo_id)).resolve()
        if repo_dir.exists() and repo_dir.is_relative_to(self.base_dir):
            shutil.rmtree(repo_dir, ignore_errors=True)
            logger.info("Deleted repository workspace %s", repo_id)
            return True
        return False


repo_service = RepoImportService()
