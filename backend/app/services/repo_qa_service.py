from datetime import datetime
import logging
from typing import List, Optional
import uuid

from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.repository import ImportedRepository
from app.schemas.repository import CodeChunkMetadata, RepoChatResponse, RetrievedChunk
from app.services.chunking_service import chunker
from app.services.llm_service import LLMService, get_llm_service
from app.services.repo_service import repo_service
from app.services.vector_service import vector_service

logger = logging.getLogger(__name__)


class RepoQAService:
    """
    RAG service that retrieves relevant code chunks from FAISS and synthesizes
    answers through Groq while citing specific file paths and line ranges.
    """

    @classmethod
    def answer_question(
        cls,
        repo_id: uuid.UUID,
        question: str,
        top_k: int = 4,
        llm_service: Optional[LLMService] = None,
    ) -> RepoChatResponse:
        """
        Executes vector similarity search in FAISS and generates an answer citing code chunks.
        """
        # 1. Retrieve top-k relevant code chunks from the repository's isolated index
        sources: List[RetrievedChunk] = vector_service.search(
            repo_id=repo_id,
            query=question,
            top_k=top_k,
        )

        if not sources:
            return RepoChatResponse(
                question=question,
                answer=(
                    "The repository index is empty or no relevant code chunks were found. "
                    "Repository evidence is insufficient to answer this question."
                ),
                sources=[],
                evidence_sufficient=False,
            )

        # 2. Format retrieved code context with line numbers and file paths
        context_blocks = []
        for i, src in enumerate(sources, 1):
            context_blocks.append(
                f"--- Snippet {i} [{src.file_path}:{src.line_range}] ({src.language}) ---\n"
                f"{src.content}\n"
            )
        context_str = "\n".join(context_blocks)

        # 3. Prompt Groq LLM to synthesize answer citing retrieved evidence
        service = llm_service or get_llm_service()
        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            chat_model = service._get_chat_model()

            messages = [
                SystemMessage(
                    content=(
                        "You are a Senior Principal Code Analyst at CodePilot AI. "
                        "Answer user questions about the repository using ONLY the provided code snippets.\n"
                        "Rules:\n"
                        "1. Always cite specific file paths and line ranges for your findings (e.g. `[src/main.py:10-35]`).\n"
                        "2. If the provided code snippets DO NOT contain sufficient evidence to answer the question, you MUST "
                        "explicitly state: 'The repository evidence is insufficient to answer this question fully.'\n"
                        "3. Never guess, hallucinate, or extrapolate facts beyond the provided code snippets.\n"
                        "4. Explain the logic clearly and reference exact function or variable names."
                    )
                ),
                HumanMessage(
                    content=(
                        f"User Question: {question}\n\n"
                        f"Retrieved Repository Code Snippets:\n```\n{context_str}\n```\n\n"
                        "Provide a thorough, evidence-based answer citing file paths and line ranges:"
                    )
                ),
            ]

            response = chat_model.invoke(messages)
            raw_content = getattr(response, "content", response)
            answer_text = raw_content if isinstance(raw_content, str) else str(raw_content)


            insufficient = (
                "evidence is insufficient" in answer_text.lower()
                or "not enough information" in answer_text.lower()
            )

            return RepoChatResponse(
                question=question,
                answer=answer_text,
                sources=sources,
                evidence_sufficient=not insufficient,
            )

        except Exception as exc:
            logger.error("RAG question answering failed: %s", exc)
            return RepoChatResponse(
                question=question,
                answer=f"Error generating repository answer: {str(exc)}. Retrieved {len(sources)} relevant snippets.",
                sources=sources,
                evidence_sufficient=False,
            )

    @classmethod
    def run_import_and_indexing(
        cls,
        repo_id: uuid.UUID,
        owner: str,
        repo_name: str,
        branch: Optional[str] = None,
        access_token: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> None:
        """
        Background worker that downloads, scans, chunks, and indexes a GitHub repository.
        Never logs or stores the access token.
        """
        session = db or SessionLocal()
        should_close = db is None

        try:
            repo_record = session.query(ImportedRepository).filter_by(id=repo_id).first()
            if not repo_record:
                logger.error("ImportedRepository %s not found in database", repo_id)
                return

            repo_record.status = "importing"
            repo_record.error_message = None
            session.commit()

            # 1. Fetch files from GitHub
            logger.info("Fetching repository archive for %s/%s...", owner, repo_name)
            repo_service.fetch_repository(
                repo_id=repo_id,
                owner=owner,
                repo_name=repo_name,
                branch=branch,
                access_token=access_token,
            )

            # 2. Scan allowable text files
            repo_record.status = "indexing"
            session.commit()

            files = repo_service.scan_workspace(repo_id)
            total_bytes = sum(f["size"] for f in files)

            # 3. Chunk source code
            chunks = chunker.chunk_repository_files(repo_id, files)

            # 4. Build and persist FAISS index
            total_vectors = vector_service.build_and_save_index(repo_id, chunks)

            # 5. Update database record
            repo_record.status = "ready"
            repo_record.total_files = len(files)
            repo_record.total_chunks = total_vectors
            repo_record.total_size_bytes = total_bytes
            repo_record.index_path = str(vector_service.get_repo_dir(repo_id))
            repo_record.last_indexed_at = datetime.now()
            session.commit()

            logger.info(
                "Repository %s/%s indexing complete: %d files, %d chunks",
                owner,
                repo_name,
                len(files),
                total_vectors,
            )

        except Exception as exc:
            logger.exception("Repository import/indexing failed for %s: %s", repo_id, exc)
            if repo_record:
                repo_record.status = "failed"
                repo_record.error_message = str(exc)
                session.commit()
        finally:
            if should_close:
                session.close()


repo_qa_service = RepoQAService()
