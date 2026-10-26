import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure root backend directory is in sys.path so 'python main.py' works directly
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api import api_router
from app.config.settings import settings
from app.database.session import engine
from app.middleware.correlation import CorrelationAndLoggingMiddleware, CorrelationIdFilter

# Configure structured logging with correlation IDs
logging_handler = logging.StreamHandler(sys.stdout)
logging_handler.addFilter(CorrelationIdFilter())
logging_formatter = logging.Formatter(
    fmt="[%(asctime)s] [%(levelname)s] [cid: %(correlation_id)s] [%(name)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging_handler.setFormatter(logging_formatter)

root_logger = logging.getLogger()
root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
# Replace existing handlers with our filtered handler
root_logger.handlers = [logging_handler]

logger = logging.getLogger("codepilot.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for the FastAPI application."""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    # Ensure storage directories exist
    for dir_path in [settings.GENERATED_PROJECTS_DIR, settings.IMPORTED_REPOS_DIR, settings.FAISS_INDEXES_DIR]:
        os.makedirs(dir_path, exist_ok=True)
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME} gracefully")
    try:
        engine.dispose()
    except Exception:
        pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API for CodePilot AI - Multi-agent software engineering assistant.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Correlation and structured request logging middleware
app.add_middleware(CorrelationAndLoggingMiddleware)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes under /api
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Root"])
def root_status():
    """Root endpoint welcoming developers and pointing to documentation."""
    return JSONResponse(
        content={
            "app": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "status": "online",
            "docs_url": "/docs",
            "health_url": f"{settings.API_V1_PREFIX}/health",
            "projects_url": f"{settings.API_V1_PREFIX}/projects",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
