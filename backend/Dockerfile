# Multi-stage production Dockerfile for CodePilot AI Backend
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies (build-essential, git, libpq-dev for PostgreSQL, curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root system user for runtime security
RUN groupadd -g 1001 codepilot && \
    useradd -u 1001 -g codepilot -s /bin/bash -m codepilot

# Create and set permissions for persistent workspace storage directories
RUN mkdir -p /app/generated_projects /app/imported_repositories /app/faiss_indexes && \
    chown -R codepilot:codepilot /app

# Copy application source code and migration scripts
COPY . .
RUN chown -R codepilot:codepilot /app

USER codepilot

EXPOSE 8000

# Health check using FastAPI /api/health endpoint
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Launch script: run database migrations, then start Uvicorn ASGI server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"]
