import hashlib
import io
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid
import zipfile

from app.config.settings import settings


class PathTraversalError(ValueError):
    """Raised when an unsafe path or path traversal attempt is detected."""
    pass


class StorageService:
    """
    Dedicated workspace storage service for generated projects.
    Ensures generated code is stored safely outside CodePilot's own codebase,
    validates relative file paths, and prevents directory traversal attacks.
    """

    def __init__(self, base_dir: Optional[str] = None):
        # Base directory defaults to the configured GENERATED_PROJECTS_DIR
        raw_base = base_dir or settings.GENERATED_PROJECTS_DIR
        self.base_dir = Path(raw_base).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_project_dir(self, project_id: Union[uuid.UUID, str]) -> Path:
        """
        Returns the resolved absolute path to the project's dedicated workspace directory.
        Creates the directory if it does not yet exist.
        """
        project_dir = (self.base_dir / str(project_id)).resolve()
        
        # Verify the project directory itself is strictly within base_dir
        if not project_dir.is_relative_to(self.base_dir):
            raise PathTraversalError(f"Invalid project ID or workspace path: {project_id}")
            
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    def validate_relative_path(self, project_id: Union[uuid.UUID, str], relative_path: str) -> Path:
        r"""
        Validates that relative_path is a safe relative path inside the project workspace.
        Rejects:
        - Absolute paths (/foo, \foo, C:\foo)
        - Path traversal sequences (../, ..\)
        - Paths resolving outside the project's workspace directory
        """

        if not relative_path or not relative_path.strip():
            raise PathTraversalError("File path cannot be empty")

        cleaned_path = relative_path.strip()

        # Reject explicit absolute path indicators across platforms
        if cleaned_path.startswith("/") or cleaned_path.startswith("\\"):
            raise PathTraversalError(f"Absolute paths are forbidden: '{relative_path}'")
        
        # Reject Windows drive letters (e.g., C:, D:)
        if len(cleaned_path) >= 2 and cleaned_path[1] == ":":
            raise PathTraversalError(f"Absolute drive paths are forbidden: '{relative_path}'")

        # Reject path traversal tokens
        parts = Path(cleaned_path).parts
        if ".." in parts:
            raise PathTraversalError(f"Path traversal sequence '..' is forbidden: '{relative_path}'")

        project_dir = self.get_project_dir(project_id)
        target_path = (project_dir / cleaned_path).resolve()

        # Check containment
        if not target_path.is_relative_to(project_dir):
            raise PathTraversalError(f"Path traversal detected: '{relative_path}' escapes workspace")

        # The target cannot be the workspace root itself
        if target_path == project_dir:
            raise PathTraversalError("Target path cannot be the project workspace root directory")

        return target_path

    def list_files(self, project_id: Union[uuid.UUID, str]) -> List[Dict[str, Any]]:
        """
        Recursively discovers all files in the project workspace,
        returning relative path, size in bytes, and language.
        """
        project_dir = self.get_project_dir(project_id)
        file_entries: List[Dict[str, Any]] = []

        if not project_dir.exists():
            return file_entries

        for root, _, files in os.walk(project_dir):
            for file_name in files:
                full_path = Path(root) / file_name
                rel_path = str(full_path.relative_to(project_dir)).replace("\\", "/")
                try:
                    size_bytes = full_path.stat().st_size
                except OSError:
                    size_bytes = 0

                file_entries.append({
                    "path": rel_path,
                    "size_bytes": size_bytes,
                    "language": self.detect_language(rel_path),
                })

        return file_entries

    def write_file(
        self,
        project_id: Union[uuid.UUID, str],
        relative_path: str,
        content: str,
    ) -> Tuple[int, str]:
        """
        Writes content to the validated relative path inside the project workspace.
        Creates parent directories if necessary.
        Returns a tuple of (file_size_bytes, sha256_checksum).
        """
        target_path = self.validate_relative_path(project_id, relative_path)
        
        # Ensure parent directory exists
        target_path.parent.mkdir(parents=True, exist_ok=True)

        content_bytes = content.encode("utf-8")
        target_path.write_bytes(content_bytes)

        file_size = len(content_bytes)
        checksum = hashlib.sha256(content_bytes).hexdigest()

        return file_size, checksum

    def read_file(self, project_id: Union[uuid.UUID, str], relative_path: str) -> str:
        """
        Reads and returns the UTF-8 content of a generated file.
        Raises FileNotFoundError if the file does not exist.
        """
        target_path = self.validate_relative_path(project_id, relative_path)
        if not target_path.exists() or not target_path.is_file():
            raise FileNotFoundError(f"File not found: {relative_path}")

        return target_path.read_text(encoding="utf-8", errors="replace")

    def file_exists(self, project_id: Union[uuid.UUID, str], relative_path: str) -> bool:
        """
        Checks whether a relative file path exists within the project workspace.
        """
        try:
            target_path = self.validate_relative_path(project_id, relative_path)
            return target_path.exists() and target_path.is_file()
        except PathTraversalError:
            return False

    def create_project_zip(self, project_id: Union[uuid.UUID, str]) -> bytes:
        """
        Creates an in-memory ZIP archive of all files in the project workspace.
        Maintains the relative directory hierarchy.
        """
        project_dir = self.get_project_dir(project_id)
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(project_dir):
                for file_name in files:
                    full_path = Path(root) / file_name
                    # Compute relative path inside the project folder
                    rel_path = full_path.relative_to(project_dir)
                    zipf.write(full_path, arcname=str(rel_path).replace("\\", "/"))

        zip_buffer.seek(0)
        return zip_buffer.getvalue()

    @staticmethod
    def detect_language(file_path: str) -> str:
        """
        Infers language syntax highlight key from file extension or name.
        """
        lower = file_path.lower()
        if lower.endswith(".py"):
            return "python"
        elif lower.endswith(".ts"):
            return "typescript"
        elif lower.endswith(".tsx"):
            return "typescriptreact"
        elif lower.endswith(".js"):
            return "javascript"
        elif lower.endswith(".jsx"):
            return "javascriptreact"
        elif lower.endswith(".json"):
            return "json"
        elif lower.endswith(".html"):
            return "html"
        elif lower.endswith(".css"):
            return "css"
        elif lower.endswith(".md"):
            return "markdown"
        elif lower.endswith(".sql"):
            return "sql"
        elif lower.endswith(".yaml") or lower.endswith(".yml"):
            return "yaml"
        elif lower.endswith(".sh") or lower.endswith(".bash"):
            return "shell"
        elif lower.endswith(".toml"):
            return "toml"
        elif lower.endswith(".dockerfile") or lower == "dockerfile":
            return "dockerfile"
        elif lower.endswith(".env") or lower.startswith(".env"):
            return "plaintext"
        return "plaintext"


# Singleton instance
storage_service = StorageService()
