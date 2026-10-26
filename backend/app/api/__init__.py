from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.projects import router as projects_router
from app.api.ai import router as ai_router
from app.api.workflows import router as workflows_router
from app.api.codegen import router as codegen_router
from app.api.repositories import router as repositories_router
from app.api.git import router as git_router
from app.api.sandbox import router as sandbox_router
from app.api.qa import router as qa_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(projects_router)
api_router.include_router(ai_router)
api_router.include_router(workflows_router)
api_router.include_router(codegen_router)
api_router.include_router(repositories_router)
api_router.include_router(git_router)
api_router.include_router(sandbox_router)
api_router.include_router(qa_router)

__all__ = ["api_router"]




