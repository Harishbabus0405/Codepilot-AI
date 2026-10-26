import logging
from typing import List
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.repository import ImportedRepository
from app.schemas.repository import (
    RepoChatRequest,
    RepoChatResponse,
    RepoImportRequest,
    RepoImportStatusResponse,
    RepoResponse,
)
from app.services.repo_qa_service import repo_qa_service
from app.services.repo_service import RepoValidationError, repo_service
from app.services.vector_service import vector_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repositories", tags=["GitHub Repositories"])


@router.post(
    "/import",
    response_model=RepoResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Import an authorized GitHub repository and trigger vector indexing",
)
def import_repository(
    request: RepoImportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Validates GitHub URL, registers the repository, and initiates secure background
    download, filtering, chunking, and FAISS vector indexing.
    Never requests or stores GitHub passwords; tokens are used transiently.
    """
    try:
        normalized_url, owner, repo_name = repo_service.validate_github_url(request.repo_url)
    except RepoValidationError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )

    display_name = request.name.strip() if request.name and request.name.strip() else repo_name

    # Check if this repository is already imported
    existing = (
        db.query(ImportedRepository)
        .filter(ImportedRepository.repo_url == normalized_url)
        .first()
    )

    if existing:
        # Re-use existing record and update status
        existing.status = "pending"
        existing.name = display_name
        existing.error_message = None
        db.commit()
        db.refresh(existing)
        repo_record = existing
    else:
        repo_record = ImportedRepository(
            name=display_name,
            repo_url=normalized_url,
            owner=owner,
            default_branch=request.branch or "main",
            is_private=bool(request.access_token),
            status="pending",
        )
        db.add(repo_record)
        db.commit()
        db.refresh(repo_record)

    # Dispatch download & indexing to background worker
    background_tasks.add_task(
        repo_qa_service.run_import_and_indexing,
        repo_record.id,
        owner,
        repo_name,
        request.branch,
        request.access_token,
    )

    return repo_record


@router.get(
    "",
    response_model=List[RepoResponse],
    summary="List all imported GitHub repositories",
)
def list_repositories(
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Returns all imported repositories ordered by creation date descending.
    """
    repos = (
        db.query(ImportedRepository)
        .order_by(ImportedRepository.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return repos


@router.get(
    "/{repo_id}",
    response_model=RepoResponse,
    summary="Retrieve single imported repository details",
)
def get_repository(
    repo_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Returns metadata, file count, and indexing status for a specific repository.
    """
    repo = db.query(ImportedRepository).filter(ImportedRepository.id == repo_id).first()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository with ID '{repo_id}' not found.",
        )
    return repo


@router.get(
    "/{repo_id}/status",
    response_model=RepoImportStatusResponse,
    summary="Retrieve repository import and indexing progress",
)
def get_repository_status(
    repo_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Polls the current status, chunk count, and potential errors of a repository.
    """
    repo = db.query(ImportedRepository).filter(ImportedRepository.id == repo_id).first()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository with ID '{repo_id}' not found.",
        )
    return RepoImportStatusResponse(
        id=repo.id,
        name=repo.name,
        status=repo.status,
        total_files=repo.total_files,
        total_chunks=repo.total_chunks,
        total_size_bytes=repo.total_size_bytes,
        error_message=repo.error_message,
        last_indexed_at=repo.last_indexed_at,
    )


@router.post(
    "/{repo_id}/reindex",
    response_model=RepoImportStatusResponse,
    summary="Re-run chunking and FAISS vector indexing on existing repository files",
)
def reindex_repository(
    repo_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Re-scans the repository workspace and re-generates the FAISS vector index.
    """
    repo = db.query(ImportedRepository).filter(ImportedRepository.id == repo_id).first()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository with ID '{repo_id}' not found.",
        )

    repo.status = "indexing"
    repo.error_message = None
    db.commit()
    db.refresh(repo)

    def _reindex_worker():
        from app.database.session import SessionLocal
        from app.services.chunking_service import chunker
        session = SessionLocal()
        try:
            r = session.query(ImportedRepository).filter_by(id=repo_id).first()
            if not r:
                return
            files = repo_service.scan_workspace(repo_id)
            chunks = chunker.chunk_repository_files(repo_id, files)
            total_vecs = vector_service.build_and_save_index(repo_id, chunks)
            r.status = "ready"
            r.total_files = len(files)
            r.total_chunks = total_vecs
            r.total_size_bytes = sum(f["size"] for f in files)
            session.commit()
        except Exception as e:
            logger.exception("Reindexing error: %s", e)
            r = session.query(ImportedRepository).filter_by(id=repo_id).first()
            if r:
                r.status = "failed"
                r.error_message = str(e)
                session.commit()
        finally:
            session.close()

    background_tasks.add_task(_reindex_worker)

    return RepoImportStatusResponse(
        id=repo.id,
        name=repo.name,
        status="indexing",
        total_files=repo.total_files,
        total_chunks=repo.total_chunks,
        total_size_bytes=repo.total_size_bytes,
        error_message=None,
        last_indexed_at=repo.last_indexed_at,
    )


@router.post(
    "/{repo_id}/chat",
    response_model=RepoChatResponse,
    summary="Ask questions about repository code using RAG and FAISS vector retrieval",
)
def chat_repository(
    repo_id: uuid.UUID,
    request: RepoChatRequest,
    db: Session = Depends(get_db),
):
    """
    Searches the isolated FAISS vector index for relevant code chunks and generates
    an answer through Groq with file and line range citations.
    """
    repo = db.query(ImportedRepository).filter(ImportedRepository.id == repo_id).first()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository with ID '{repo_id}' not found.",
        )

    if repo.status == "importing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Repository is currently being imported. Please wait until import is complete.",
        )

    response = repo_qa_service.answer_question(
        repo_id=repo_id,
        question=request.question,
        top_k=request.top_k,
    )
    return response


@router.delete(
    "/{repo_id}",
    summary="Delete repository files and isolated FAISS vector index",
)
def delete_repository(
    repo_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Removes the repository from PostgreSQL, deletes disk files, and removes the FAISS index.
    """
    repo = db.query(ImportedRepository).filter(ImportedRepository.id == repo_id).first()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository with ID '{repo_id}' not found.",
        )

    # 1. Delete disk files and vector index
    repo_service.delete_repository(repo_id)

    # 2. Delete database record
    db.delete(repo)
    db.commit()

    return {"message": f"Repository '{repo.name}' and FAISS vector index deleted successfully."}
