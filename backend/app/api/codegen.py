import logging
import re
from typing import List, Optional
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.codegen import GeneratedFile, GeneratedProject
from app.models.project import Project
from app.schemas.codegen import (
    FileContentResponse,
    GenerateStartRequest,
    GenerateStatusResponse,
    GeneratedFileResponse,
    GeneratedProjectResponse,
)
from app.services.codegen_service import CodeGenerationEngine
from app.services.storage_service import PathTraversalError, storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}", tags=["Code Generation"])


@router.post(

    "/generate",
    response_model=GenerateStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start background code generation for a project",
)
def start_code_generation(
    project_id: uuid.UUID,
    request: GenerateStartRequest = GenerateStartRequest(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
):
    """
    Initiates code generation from approved requirements and architecture.
    Runs asynchronously in the background.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )

    # Check if a generation session is already in progress
    active_gen = (
        db.query(GeneratedProject)
        .filter(
            GeneratedProject.project_id == project_id,
            GeneratedProject.status.in_(["pending", "generating"]),
        )
        .first()
    )

    if active_gen:
        pct = (
            round((active_gen.generated_files_count / active_gen.total_files) * 100, 1)
            if active_gen.total_files > 0
            else 0.0
        )
        return GenerateStatusResponse(
            id=active_gen.id,
            project_id=active_gen.project_id,
            status=active_gen.status,
            template_type=active_gen.template_type,
            total_files=active_gen.total_files,
            generated_files_count=active_gen.generated_files_count,
            percent_complete=pct,
            error_message=active_gen.error_message,
            updated_at=active_gen.updated_at,
        )

    # Create new generation session
    template = request.template_type or "fullstack"
    gen_project = GeneratedProject(
        project_id=project_id,
        template_type=template,
        status="pending",
        total_files=0,
        generated_files_count=0,
    )
    db.add(gen_project)
    db.commit()
    db.refresh(gen_project)

    # Dispatch generation worker to background
    background_tasks.add_task(
        CodeGenerationEngine.execute_generation,
        gen_project.id,
        None,  # db session created inside worker
        request.force_regenerate,
    )

    return GenerateStatusResponse(
        id=gen_project.id,
        project_id=gen_project.project_id,
        status="pending",
        template_type=gen_project.template_type,
        total_files=0,
        generated_files_count=0,
        percent_complete=0.0,
        error_message=None,
        updated_at=gen_project.updated_at,
    )


@router.get(
    "/generate/status",
    response_model=GenerateStatusResponse,
    summary="Retrieve current generation status and progress",
)
def get_generation_status(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Returns the latest generation status, file counts, and error state.
    """
    gen_project = (
        db.query(GeneratedProject)
        .filter(GeneratedProject.project_id == project_id)
        .order_by(GeneratedProject.created_at.desc())
        .first()
    )

    if not gen_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No code generation session found for project '{project_id}'.",
        )

    pct = (
        round((gen_project.generated_files_count / gen_project.total_files) * 100, 1)
        if gen_project.total_files > 0
        else (100.0 if gen_project.status == "completed" else 0.0)
    )

    return GenerateStatusResponse(
        id=gen_project.id,
        project_id=gen_project.project_id,
        status=gen_project.status,
        template_type=gen_project.template_type,
        total_files=gen_project.total_files,
        generated_files_count=gen_project.generated_files_count,
        percent_complete=pct,
        error_message=gen_project.error_message,
        updated_at=gen_project.updated_at,
    )


@router.get(
    "/files",
    response_model=List[GeneratedFileResponse],
    summary="List all generated files and metadata for the project",
)
def list_generated_files(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Returns an array of file records, paths, languages, and checksums.
    """
    gen_project = (
        db.query(GeneratedProject)
        .filter(GeneratedProject.project_id == project_id)
        .order_by(GeneratedProject.created_at.desc())
        .first()
    )

    if not gen_project:
        return []

    files = (
        db.query(GeneratedFile)
        .filter(GeneratedFile.generated_project_id == gen_project.id)
        .order_by(GeneratedFile.file_path.asc())
        .all()
    )
    return files


@router.get(
    "/files/content",
    response_model=FileContentResponse,
    summary="Retrieve source code and metadata of a specific generated file",
)
def get_file_content(
    project_id: uuid.UUID,
    path: str = Query(..., description="Relative file path within workspace, e.g. 'app/main.py'"),
    db: Session = Depends(get_db),
):
    """
    Returns the raw content of the requested source file after verifying path safety.
    """
    # 1. Path safety check
    try:
        storage_service.validate_relative_path(project_id, path)
    except PathTraversalError as pte:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file path: {str(pte)}",
        )

    # 2. Check metadata in DB
    gen_project = (
        db.query(GeneratedProject)
        .filter(GeneratedProject.project_id == project_id)
        .order_by(GeneratedProject.created_at.desc())
        .first()
    )

    file_rec = None
    if gen_project:
        file_rec = (
            db.query(GeneratedFile)
            .filter(
                GeneratedFile.generated_project_id == gen_project.id,
                GeneratedFile.file_path == path,
            )
            .first()
        )

    # 3. Read content from storage
    try:
        content = storage_service.read_file(project_id, path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File '{path}' does not exist in project workspace.",
        )
    except Exception as exc:
        logger.error("Failed to read file '%s': %s", path, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error reading file from storage.",
        )

    lang = file_rec.language if file_rec else storage_service.detect_language(path)
    checksum = file_rec.checksum if file_rec else ""
    is_modified = file_rec.is_modified_by_user if file_rec else False

    return FileContentResponse(
        file_path=path,
        content=content,
        language=lang,
        size_bytes=len(content.encode("utf-8")),
        checksum=checksum,
        is_modified_by_user=is_modified,
    )


@router.get(
    "/download",
    summary="Download complete generated project as a ZIP archive",
)
def download_project_zip(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Packages the dedicated project workspace into a zip archive and streams it for download.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )

    try:
        zip_bytes = storage_service.create_project_zip(project_id)
    except Exception as exc:
        logger.exception("Failed to create ZIP for project %s: %s", project_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate project archive.",
        )

    # Sanitize file name
    safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", project.name.lower()).strip("_") or "project"
    archive_filename = f"{safe_name}.zip"

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{archive_filename}"',
            "Content-Length": str(len(zip_bytes)),
        },
    )
