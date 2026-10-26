import hashlib
from typing import List
import uuid

from app.schemas.repository import CodeChunkMetadata
from app.services.storage_service import storage_service


class CodeChunker:
    """
    Splits source files into bounded, overlapping chunks while capturing
    accurate line numbers, file paths, and language metadata for vector indexing.
    """

    def __init__(self, target_lines: int = 45, overlap_lines: int = 10, min_chunk_chars: int = 30):
        self.target_lines = target_lines
        self.overlap_lines = overlap_lines
        self.min_chunk_chars = min_chunk_chars

    def chunk_file(
        self,
        repo_id: uuid.UUID,
        file_path: str,
        content: str,
        language: str = "",
    ) -> List[CodeChunkMetadata]:
        """
        Splits a single file into line-aware chunks with position metadata.
        """
        if not content or not content.strip():
            return []

        lang = language or storage_service.detect_language(file_path)
        lines = content.splitlines()
        total_lines = len(lines)

        chunks: List[CodeChunkMetadata] = []

        # If file is short, keep as single chunk
        if total_lines <= self.target_lines:
            text = content.strip()
            if len(text) >= self.min_chunk_chars:
                chunk_id = self._generate_chunk_id(repo_id, file_path, 1, total_lines)
                chunks.append(
                    CodeChunkMetadata(
                        chunk_id=chunk_id,
                        repo_id=str(repo_id),
                        file_path=file_path,
                        language=lang,
                        start_line=1,
                        end_line=total_lines,
                        line_range=f"1-{total_lines}",
                        content=text,
                    )
                )
            return chunks

        step = max(1, self.target_lines - self.overlap_lines)
        for i in range(0, total_lines, step):
            start_line = i + 1
            end_line = min(i + self.target_lines, total_lines)
            chunk_slice = lines[i:end_line]
            chunk_text = "\n".join(chunk_slice).strip()

            if len(chunk_text) < self.min_chunk_chars:
                continue

            chunk_id = self._generate_chunk_id(repo_id, file_path, start_line, end_line)
            chunks.append(
                CodeChunkMetadata(
                    chunk_id=chunk_id,
                    repo_id=str(repo_id),
                    file_path=file_path,
                    language=lang,
                    start_line=start_line,
                    end_line=end_line,
                    line_range=f"{start_line}-{end_line}",
                    content=chunk_text,
                )
            )

            if end_line >= total_lines:
                break

        return chunks

    def chunk_repository_files(
        self,
        repo_id: uuid.UUID,
        files: List[dict],
    ) -> List[CodeChunkMetadata]:
        """
        Processes a list of repository files ({'path': ..., 'content': ...}) into chunks.
        """
        all_chunks: List[CodeChunkMetadata] = []
        for f in files:
            file_path = f.get("path", "")
            content = f.get("content", "")
            language = f.get("language") or storage_service.detect_language(file_path)
            file_chunks = self.chunk_file(repo_id, file_path, content, language)
            all_chunks.extend(file_chunks)
        return all_chunks

    @staticmethod
    def _generate_chunk_id(repo_id: uuid.UUID, file_path: str, start: int, end: int) -> str:
        raw = f"{repo_id}:{file_path}:{start}:{end}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        return f"chunk_{digest}"


chunker = CodeChunker()
