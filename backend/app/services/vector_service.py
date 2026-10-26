import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
from typing import List, Optional
import uuid

import numpy as np

from app.config.settings import settings
from app.schemas.repository import CodeChunkMetadata, RetrievedChunk

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Configurable embedding service.
    Uses fastembed (ONNX runtime, BAAI/bge-small-en-v1.5) by default,
    with a deterministic fallback vectorizer for offline or isolated test environments.
    """

    DIMENSION = 384

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self._model = None
        self._use_fallback = False

    def _get_model(self):
        if self._model is None and not self._use_fallback:
            try:
                from fastembed import TextEmbedding
                self._model = TextEmbedding(model_name=self.model_name)
                logger.info("Initialized fastembed model: %s", self.model_name)
            except Exception as e:
                logger.warning(
                    "Fastembed model initialization failed or offline (%s). Using deterministic vectorizer.",
                    e,
                )
                self._use_fallback = True
        return self._model

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Embeds a list of texts into L2-normalized float32 vectors of shape (N, DIMENSION).
        """
        if not texts:
            return np.empty((0, self.DIMENSION), dtype=np.float32)

        model = self._get_model()
        if model and not self._use_fallback:
            try:
                # fastembed returns a generator of numpy arrays
                embeddings = list(model.embed(texts))
                arr = np.array(embeddings, dtype=np.float32)
                # Normalize L2
                norms = np.linalg.norm(arr, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                return arr / norms
            except Exception as exc:
                logger.warning("Fastembed inference error (%s); using deterministic projection.", exc)

        return self._deterministic_embed(texts)

    def embed_query(self, query: str) -> np.ndarray:
        """
        Embeds a single search query into shape (1, DIMENSION).
        """
        return self.embed_texts([query])

    def _deterministic_embed(self, texts: List[str]) -> np.ndarray:
        """
        Deterministic, fast n-gram pseudo-random projection vectorizer.
        Generates consistent 384-dimensional unit vectors with cosine similarity preservation.
        Used as a robust zero-network fallback and for ultra-fast unit testing.
        """
        vectors = np.zeros((len(texts), self.DIMENSION), dtype=np.float32)
        for i, text in enumerate(texts):
            words = text.lower().split()
            if not words:
                continue
            for word in words:
                # Seed projection with word hash
                seed = int(hashlib.md5(word.encode("utf-8")).hexdigest()[:8], 16)
                rng = np.random.default_rng(seed)
                word_vec = rng.standard_normal(self.DIMENSION, dtype=np.float32)
                vectors[i] += word_vec

            norm = np.linalg.norm(vectors[i])
            if norm > 0:
                vectors[i] /= norm
            else:
                vectors[i, 0] = 1.0

        return vectors


class FAISSIndexManager:
    """
    Manages isolated persistent FAISS vector indexes and metadata for imported repositories.
    Stores each repository's index in 'faiss_indexes/<repo_id>/'.
    """

    def __init__(self, base_dir: Optional[str] = None):
        raw_base = base_dir or settings.FAISS_INDEXES_DIR
        self.base_dir = Path(raw_base).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.embedding_service = EmbeddingService()

    def get_repo_dir(self, repo_id: uuid.UUID) -> Path:
        """Returns the isolated directory for a specific repository's index."""
        repo_dir = (self.base_dir / str(repo_id)).resolve()
        if not repo_dir.is_relative_to(self.base_dir):
            raise ValueError(f"Invalid repository ID or path traversal: {repo_id}")
        repo_dir.mkdir(parents=True, exist_ok=True)
        return repo_dir

    def index_exists(self, repo_id: uuid.UUID) -> bool:
        """Checks if a valid FAISS index and chunk metadata exist for the repo."""
        repo_dir = self.get_repo_dir(repo_id)
        index_file = repo_dir / "index.faiss"
        chunks_file = repo_dir / "chunks.json"
        return index_file.exists() and chunks_file.exists()

    def build_and_save_index(
        self,
        repo_id: uuid.UUID,
        chunks: List[CodeChunkMetadata],
    ) -> int:
        """
        Embeds chunk contents and writes the persistent FAISS index and metadata.
        Returns the total number of indexed chunks.
        """
        import faiss

        repo_dir = self.get_repo_dir(repo_id)
        if not chunks:
            # Create empty placeholder index
            empty_index = faiss.IndexFlatIP(self.embedding_service.DIMENSION)
            faiss.write_index(empty_index, str(repo_dir / "index.faiss"))
            (repo_dir / "chunks.json").write_text("[]", encoding="utf-8")
            return 0

        # 1. Embed chunk contents
        texts = [
            f"File: {c.file_path} (Lines {c.line_range})\n{c.content}"
            for c in chunks
        ]
        vectors = self.embedding_service.embed_texts(texts)

        # 2. Build FAISS IndexFlatIP (Inner Product on normalized vectors = Cosine Similarity)
        dimension = vectors.shape[1]
        index = faiss.IndexFlatIP(dimension)
        index.add(vectors)

        # 3. Write index to disk
        index_path = repo_dir / "index.faiss"
        faiss.write_index(index, str(index_path))

        # 4. Write chunk metadata to chunks.json
        chunks_data = [c.model_dump() for c in chunks]
        (repo_dir / "chunks.json").write_text(
            json.dumps(chunks_data, indent=2),
            encoding="utf-8",
        )

        logger.info(
            "Saved FAISS index for repo %s: %d vectors (dimension %d)",
            repo_id,
            index.ntotal,
            dimension,
        )
        return index.ntotal

    def search(
        self,
        repo_id: uuid.UUID,
        query: str,
        top_k: int = 4,
    ) -> List[RetrievedChunk]:
        """
        Retrieves top-k most relevant code chunks for a query from the repository's index.
        """
        import faiss

        if not self.index_exists(repo_id):
            logger.warning("No index found for repo %s", repo_id)
            return []

        repo_dir = self.get_repo_dir(repo_id)
        index_path = repo_dir / "index.faiss"
        chunks_path = repo_dir / "chunks.json"

        try:
            index = faiss.read_index(str(index_path))
            chunks_data = json.loads(chunks_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error("Failed to load index or chunks for repo %s: %s", repo_id, e)
            return []

        if index.ntotal == 0 or not chunks_data:
            return []

        # Embed query
        query_vector = self.embedding_service.embed_query(query)

        # Search index
        k = min(top_k, index.ntotal)
        scores, indices = index.search(query_vector, k)

        results: List[RetrievedChunk] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(chunks_data):
                continue
            chunk = chunks_data[idx]
            results.append(
                RetrievedChunk(
                    file_path=chunk.get("file_path", ""),
                    line_range=chunk.get("line_range", ""),
                    language=chunk.get("language", ""),
                    score=float(score),
                    content=chunk.get("content", ""),
                )
            )

        return results

    def delete_index(self, repo_id: uuid.UUID) -> bool:
        """Deletes the isolated FAISS index directory for a repository."""
        repo_dir = (self.base_dir / str(repo_id)).resolve()
        if repo_dir.exists() and repo_dir.is_relative_to(self.base_dir):
            shutil.rmtree(repo_dir, ignore_errors=True)
            logger.info("Deleted FAISS index for repo %s", repo_id)
            return True
        return False


vector_service = FAISSIndexManager()
