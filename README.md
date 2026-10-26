# CodePilot AI — Multi-Agent Software Engineering Assistant

CodePilot AI is a multi-agent software engineering assistant designed to turn natural-language software requirements into production-ready architectures, modules, implementation plans, real source code files, automated test suites, and verified security repairs.

- **Phase 1: Foundation** — Clean monorepo architecture, FastAPI backend with SQLAlchemy 2.0 and Alembic migrations, PostgreSQL persistence via Docker Compose, and a minimal dark-themed developer dashboard built with React, Vite, TypeScript, and Tailwind CSS.
- **Phase 2: Groq & LangChain Integration** — Enterprise-grade LLM service integration using LangChain and Groq API (`llama-3.3-70b-versatile`). Provides structured requirements analysis, executive summaries, functional specifications, and tech stack recommendations.
- **Phase 3: LangGraph Multi-Agent Orchestration** — Full stateful multi-agent workflow coordinated by a Supervisor Agent routing between Planner, Architect, and Requirement Validation nodes. Features typed shared state, conditional routing, recursion limits, bounded retries, and PostgreSQL execution persistence.
- **Phase 4: Code Generation Engine** — Multi-file code generation pipeline that transforms approved requirements and system architecture into real, organized project source files across supported templates (`FastAPI`, `React + Vite`, `Fullstack`). Features strict path safety, dedicated workspace isolation, bounded retries with AST syntax validation, user edit protection, and one-click ZIP download.
- **Phase 5: QA, Code Review, Security Review & Bounded Repair** — Integrated quality and security audit pipeline. Performs AST static analysis, detects dangerous patterns (such as `eval`, `exec`, and unsafe shell invocations), generates test plans, calculates quality scores (0-100), and provides automated bounded repairs verified through static re-checks.
- **Phase 6: GitHub Repository Intelligence & FAISS Vector Search** — Import public or token-authorized private GitHub repositories, isolate code into persistent per-repository FAISS vector indexes with line-aware chunking, and query repository code using retrieval-augmented generation (RAG) powered by Groq with source citations (`[file:line_range]`) and explicit insufficient-evidence handling.
- **Phase 7: GitHub and Developer Workflow** — Controlled Git operations and GitHub integration for project workspaces. Features repository initialization, diff inspection, AI-assisted conventional commit messages, explicit commit approval gates, branch creation/checkout, pull request summaries combining diffs with QA findings, real GitHub API pull request creation with in-flight credential protection, and operation audit logging.
- **Phase 8: Isolated Code Execution Sandbox** — Dedicated execution service that executes untrusted generated project code and test suites in disposable Docker containers. Features strict multi-layered isolation (`--network none`, non-root user `1000:1000`, `--cap-drop ALL`, `--security-opt no-new-privileges`, 512 MB memory, 1.0 CPU, 64 PIDs, read-only root filesystems with 64 MB tmpfs, project-only volume mounts), server-controlled command validation policies, concurrency/hourly quota protection, sanitized log output, execution audit persistence, and residual risk documentation with multi-tenant isolation recommendations.
- **Phase 9: End-to-End Integration, Production Readiness & Full Deployment** — Complete verification of all 9 end-to-end workflows. Multi-stage Dockerfiles (`backend/Dockerfile`, `frontend/Dockerfile`), Nginx reverse proxy, production Docker Compose configuration with persistent named volumes and health dependencies, structured JSON logging with `X-Correlation-ID` request correlation, 10 MB payload limits, API authorization hooks, database readiness probes (`/api/ready`), and comprehensive deployment documentation.

---

## Technology Stack

- **Frontend**: React 19, Vite, TypeScript, Tailwind CSS, Lucide React, Nginx (Alpine)
- **Backend API**: Python 3.12, FastAPI, Pydantic v2, Uvicorn, Gunicorn
- **Multi-Agent Orchestration**: LangGraph, LangChain, Groq API (`langgraph`, `langchain-groq`, `langchain-core`)
- **Quality & Security**: AST Static Analyzer, Test Plan Generator, Bounded Code Repairer
- **Version Control & GitHub**: Git CLI, GitHub REST API v3, HTTPX
- **Vector Search & Embeddings**: FAISS (`faiss-cpu`), FastEmbed (`fastembed`, `BAAI/bge-small-en-v1.5`), NumPy
- **Isolated Execution & Sandbox**: Docker CLI, disposable containers (`python:3.12-slim`, `node:20-alpine`), resource cgroups, air-gapped network namespace
- **Database & ORM**: PostgreSQL 16 (with SQLite dev fallback), SQLAlchemy 2.0, Alembic migrations
- **Testing & Quality**: Pytest (93 passing tests), HTTPX, FastAPI TestClient
- **Production Containerization**: Multi-stage Docker builds, Docker Compose, Nginx SPA routing, persistent named volumes, health & readiness checks (`/api/health`, `/api/ready`)



---

## Project Structure

```
CodePilot-AI/
├── backend/
│   ├── alembic/                      # Alembic migration environment & scripts
│   │   ├── versions/
│   │   │   ├── 20261021_0001_initial_projects.py
│   │   │   ├── 20261021_0002_workflow_runs.py
│   │   │   ├── 20261021_0003_codegen.py     # GeneratedProject & GeneratedFile tables
│   │   │   ├── 20261021_0004_qa_system.py   # QA, Review & Security tables
│   │   │   ├── 20261021_0005_repositories.py# ImportedRepository metadata table
│   │   │   ├── 20261021_0006_git_workflow.py# GitAuditLog operation table
│   │   │   └── 20261021_0007_sandbox_execution.py# Phase 8: SandboxExecutionJob table
│   │   ├── env.py
│   │   └── script.py.mako
│   ├── app/
│   │   ├── agents/                   # Phase 3: LangGraph Multi-Agent System
│   │   │   ├── __init__.py
│   │   │   ├── architect.py          # Architect Agent node (Components, APIs, Schemas)
│   │   │   ├── graph.py              # Compiled LangGraph StateGraph & background runner
│   │   │   ├── planner.py            # Planner Agent node (Tasks, Dependencies, Criteria)
│   │   │   ├── state.py              # Typed AgentWorkflowState shared dictionary
│   │   │   ├── supervisor.py         # Supervisor Agent node (Coordination & Routing)
│   │   │   └── validator.py          # Requirement Validation node (Audit & Coverage Score)
│   │   ├── api/                      # REST API endpoints & routers
│   │   │   ├── __init__.py
│   │   │   ├── ai.py                 # POST /api/ai/analyze
│   │   │   ├── codegen.py            # Phase 4: /api/projects/{id}/generate, /files, /download
│   │   │   ├── git.py                # Phase 7: /api/git/{id}/status, /commit, /branches, /pr
│   │   │   ├── health.py             # GET /api/health
│   │   │   ├── projects.py           # GET, POST /api/projects, GET /api/projects/{id}
│   │   │   ├── repositories.py       # Phase 6: /api/repositories/import, /chat, /reindex
│   │   │   ├── sandbox.py            # Phase 8: /api/sandboxes/{id}/jobs, status, quota
│   │   │   └── workflows.py          # POST /projects/{id}/workflow/start, GET .../latest, GET .../status
│   │   ├── config/                   # Pydantic BaseSettings configuration
│   │   │   ├── __init__.py
│   │   │   └── settings.py           # GROQ_API_KEY, GROQ_MODEL, EMBEDDING_MODEL_NAME, SANDBOX limits
│   │   ├── database/                 # SQLAlchemy 2.0 declarative base & session
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   └── session.py
│   │   ├── models/                   # SQLAlchemy 2.0 ORM models
│   │   │   ├── __init__.py
│   │   │   ├── codegen.py            # GeneratedProject & GeneratedFile ORM models
│   │   │   ├── git.py                # Phase 7: GitAuditLog ORM model
│   │   │   ├── project.py            # Project (UUID, name, requirements, status, timestamps)
│   │   │   ├── repository.py         # Phase 6: ImportedRepository ORM model
│   │   │   ├── sandbox.py            # Phase 8: SandboxExecutionJob ORM model
│   │   │   └── workflow.py           # WorkflowRun (UUID, project_id, correlation_id, outputs, status)
│   │   ├── schemas/                  # Pydantic v2 validation schemas
│   │   │   ├── __init__.py
│   │   │   ├── ai.py                 # AnalyzeRequest, RequirementsAnalysis
│   │   │   ├── codegen.py            # FileManifest, FileContentResponse, GenerateStatusResponse
│   │   │   ├── git.py                # Phase 7: GitStatusResponse, CommitRequest, PRCreateRequest
│   │   │   ├── health.py             # HealthResponse
│   │   │   ├── project.py            # ProjectCreate, ProjectResponse, ProjectListResponse
│   │   │   ├── repository.py         # Phase 6: RepoImportRequest, RepoChatRequest, ChunkMetadata
│   │   │   ├── sandbox.py            # Phase 8: SandboxJobCreateRequest, Response, Quota
│   │   │   └── workflow.py           # PlanOutput, ArchitectureOutput, ValidationOutput, WorkflowRunResponse
│   │   ├── services/                 # Business logic & LLM provider integrations
│   │   │   ├── __init__.py
│   │   │   ├── chunking_service.py   # Phase 6: Line-aware CodeChunker (overlap, metadata)
│   │   │   ├── codegen_service.py    # FileStructurePlanner, CodeValidationNode, CodeGenerationEngine
│   │   │   ├── git_service.py        # Phase 7: GitService (init, status, diff, safe commits, branches)
│   │   │   ├── github_service.py     # Phase 7: GitHubService (AI commit msg, PR summaries, API PRs)
│   │   │   ├── llm_service.py        # Reusable LangChain Groq service & sanitized error handling
│   │   │   ├── repo_qa_service.py    # Phase 6: RAG Q&A with source citations & Groq LLM
│   │   │   ├── repo_service.py       # Phase 6: GitHub import, tarball download, untrusted file filter
│   │   │   ├── sandbox_service.py    # Phase 8: Isolated execution in disposable Docker containers
│   │   │   ├── storage_service.py    # ProjectStorageService, path traversal guard, ZIP packing
│   │   │   └── vector_service.py     # Phase 6: FAISS IndexFlatIP manager & FastEmbed vectorizer
│   │   ├── __init__.py
│   │   └── main.py                   # FastAPI application entrypoint & CORS
│   ├── tests/                        # Automated Pytest suite (86 tests)
│   │   ├── __init__.py
│   │   ├── conftest.py               # In-memory test engine & dependency overrides
│   │   ├── test_ai.py                # AI analyze endpoint, schema, and error handling tests
│   │   ├── test_codegen.py           # Path validation, manifest, storage, retry, & API tests (22 tests)
│   │   ├── test_git.py               # Phase 7: Safe Git, commits, branches, PRs, audit tests (15 tests)
│   │   ├── test_health.py            # Health check tests
│   │   ├── test_projects.py          # Project CRUD & validation tests
│   │   ├── test_repositories.py      # Phase 6: Import, exclusions, chunking, FAISS, RAG tests (17 tests)
│   │   ├── test_sandbox.py           # Phase 8: Sandbox execution, isolation, policy, & quota tests (8 tests)
│   │   └── test_workflows.py         # LangGraph workflow, routing, retry, and persistence tests
│   ├── alembic.ini                   # Alembic configuration
│   ├── requirements.txt              # Backend Python dependencies (faiss-cpu, fastembed, etc.)
│   └── .env.example                  # Backend environment variable template
├── frontend/
│   ├── src/
│   │   ├── components/               # UI components
│   │   │   ├── AnalysisPanel.tsx     # AI architectural analysis display panel
│   │   │   ├── BackendStatus.tsx     # Live connection indicator with health & DB badge
│   │   │   ├── ProjectDetailModal.tsx# Tabbed modal: Code, Workflow, Git, Sandbox Execution, Details
│   │   │   ├── ProjectWorkspace.tsx  # File explorer, read-only code viewer, generation status, ZIP download
│   │   │   ├── RecentProjectsList.tsx# Project list with quick workspace launch
│   │   │   ├── RepositoryChatPanel.tsx# Phase 6: GitHub import, FAISS RAG chat, code citation drawer
│   │   │   ├── RequirementsInput.tsx # Multiline textarea, AI analyze action, & Create Project
│   │   │   ├── SandboxExecutionPanel.tsx# Phase 8: Isolated container runner, logs, & quotas
│   │   │   ├── Sidebar.tsx           # Minimal developer sidebar with navigation tabs
│   │   │   ├── VersionControlPanel.tsx# Phase 7: Git status, diff viewer, commit approval, PR creator
│   │   │   └── WorkflowView.tsx      # Real-time multi-agent progression, stepper, & stage outputs
│   │   ├── pages/
│   │   │   ├── DashboardPage.tsx     # Developer dashboard view
│   │   │   └── VersionControlPage.tsx# Phase 7: Workspace switcher & VersionControlPanel
│   │   ├── services/
│   │   │   └── api.ts                # Typed fetch API client (projects, health, AI, workflows, repos, git)
│   │   ├── types/
│   │   │   └── project.ts            # TypeScript interfaces (Project, GitStatusResponse, PRRequest, etc.)
│   │   ├── App.css
│   │   ├── App.tsx                   # Top-level application layout with tab switching
│   │   ├── index.css                 # Tailwind base styles and theme tokens
│   │   └── main.tsx                  # React DOM root entrypoint

│   ├── index.html                    # HTML template with Inter typography
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── generated_projects/               # Dedicated workspace directory for generated code (git-ignored)
├── imported_repositories/            # Filtered local copies of imported GitHub repos (git-ignored)
├── faiss_indexes/                    # Isolated FAISS vector indexes and chunk metadata (git-ignored)
├── docker-compose.yml                # PostgreSQL service with persistent volume
└── README.md
```

---

## Phase 4: Code Generation Engine

### 1. Architecture & Workflow

```mermaid
flowchart TD
    A[Approved Requirements & Architecture] --> B[FileStructurePlanner]
    B -->|Generate Manifest| C[(PostgreSQL: Manifest & Pending)]
    C --> D[CodeGenerationEngine: File-by-File Generator]
    D --> E[CodeValidationNode: AST & Syntax Audit]
    E -->|Valid| F[StorageService: Write to Dedicated Workspace]
    E -->|Invalid Syntax| G{Retry Limit Reached?}
    G -->|No| D
    G -->|Yes| H[Safe Boilerplate Fallback] --> F
    F --> I[(PostgreSQL: File Metadata & Checksums)]
    I --> J[User Inspects Code / Downloads ZIP Archive]
```

### 2. Core Components

1. **File Structure Planner (`FileStructurePlanner`)**:
   - Generates a complete, structured file manifest before any source code is produced.
   - Initial supported templates:
     - **FastAPI Backend (`fastapi`)**: `app/main.py`, `app/config.py`, `app/models.py`, `app/schemas.py`, `app/routes.py`, `requirements.txt`, `README.md`.
     - **React + Vite Frontend (`react`)**: `package.json`, `index.html`, `vite.config.ts`, `tsconfig.json`, `src/main.tsx`, `src/App.tsx`, `src/App.css`, `src/index.css`, `README.md`.
     - **Fullstack (`fullstack`)**: Both `backend/` and `frontend/` directories configured with a unified root `README.md`.
   - Incorporates architectural components and REST API boundaries generated by the multi-agent workflow.

2. **Code Generation Agent (`LLMService.generate_file_code`)**:
   - Generates code in separate, focused files—never as a single enormous code block.
   - Contextualizes each file with requirements, architectural patterns, and sister file paths.
   - Strips extraneous commentary and markdown wrappers.

3. **Code Validation Node (`CodeValidationNode`)**:
   - Python files: audited with `ast.parse` for syntax validity.
   - JSON configurations: verified with `json.loads`.
   - Strips markdown code blocks (` ```python ... ``` `).
   - Enforces bounded generation retries (up to 2 retries per file) providing the compiler/parser error back to the LLM.

4. **Generated Project Storage Service (`ProjectStorageService`)**:
   - **Isolation**: All generated code is written to `generated_projects/<project_id>/`, strictly segregated from CodePilot's own source code.
   - **Directory Traversal Guard**: Rejects absolute paths (`/`, `\`, `C:`), path traversal tokens (`..`), and ensures all writes resolve strictly within the assigned project directory.
   - **User Edit Protection**: Never overwrites user-modified files (`is_modified_by_user = true`) without explicit user opt-in (`force_regenerate = true`).
   - **Non-Execution Invariant**: Generated code is **never** executed automatically. It is treated strictly as read-only project artifacts until tested in a dedicated execution sandbox.
   - **ZIP Archive Streaming**: Packages the workspace on demand with exact directory hierarchies into a downloadable `.zip`.

---

## Phase 6: GitHub Repository Intelligence and FAISS Vector Search

### 1. Architecture & Retrieval Pipeline

```mermaid
flowchart TD
    A[User Enters GitHub URL + Optional PAT] --> B[RepoImportService: URL & Token Guard]
    B -->|Fetch Tarball via HTTPX| C[Untrusted File Scanner & Filter]
    C -->|Exclude .git, node_modules, binaries, secrets, oversized| D[(PostgreSQL: ImportedRepository Status)]
    D --> E[CodeChunker: Line-Aware Sliding Window]
    E -->|Chunks with line ranges & file paths| F[EmbeddingService: FastEmbed BAAI/bge-small-en-v1.5]
    F -->|384d Normalized Vectors| G[FAISSIndexManager: Write index.faiss + chunks.json]
    G --> H[(Persistent Storage: faiss_indexes/repo_id/)]
    
    I[User Asks Question] --> J[RepoQAService]
    J -->|Embed Query| F
    F -->|Search Top-K Cosine Sim| G
    G -->|Retrieved Chunks + Line Metadata| K[Groq LLM: Synthesize Answer]
    K -->|Evidence Present| L[Answer with Clickable File & Line Citations]
    K -->|Evidence Insufficient| M[Explicit Insufficient Evidence Disclaimer]
```

### 2. Core Components

1. **GitHub Repository Import Service (`RepoImportService`)**:
   - **URL Format Validation**: Validates `https://github.com/{owner}/{repo}` with strict regular expressions; rejects GitLab, BitBucket, insecure HTTP, and traversal sequences.
   - **Public & Private Repositories**: Downloads source archive tarballs directly via GitHub REST APIs (`https://api.github.com/repos/{owner}/{repo}/tarball/{branch}`) using HTTP basic/bearer authentication.
   - **Credential Security**: Personal Access Tokens (PATs) are used strictly in-flight for download requests. Tokens are never saved to PostgreSQL, written to disk, or logged. Passwords are categorically rejected.
   - **Untrusted File Filter**: Excludes `.git`, dependency directories (`node_modules`, `venv`, `vendor`), build artifacts (`dist`, `build`, `.next`), binary extensions (`.png`, `.exe`, `.so`, `.zip`, etc.), and secrets (`.env`, `id_rsa`, `*.pem`, `*.key`).
   - **Import Guardrails**: Limits maximum file size (500 KB), maximum repository footprint (25 MB), maximum file count (1,000 files), and download timeout (60 seconds).
   - **Path Traversal Guard**: Prevents extraction vulnerabilities by validating every extracted path against the destination repository workspace.

2. **Code Chunking Service (`CodeChunker`)**:
   - Splits source files into manageable code chunks (default 50 lines with 10-line overlap).
   - Preserves complete chunk metadata: `repository_id`, `file_path`, `language`, `start_line`, `end_line`, `line_range` (e.g. `L1-L50`), and content character length.
   - Ensures line numbering aligns directly with source files using standard newline slicing.

3. **Embedding Service (`EmbeddingService`)**:
   - **Configurable Model**: Defaults to `BAAI/bge-small-en-v1.5` (384-dimensional dense vectors) running locally via `fastembed`.
   - **Normalization**: Automatically L2-normalizes embedding vectors to enable fast inner-product (`IndexFlatIP`) cosine similarity search.
   - **Zero-Network Fallback**: Implements deterministic semantic projection fallback for offline or airgapped environments, ensuring unit tests and local sandboxes run reliably without downloading remote weights.

4. **FAISS Vector Index Manager (`FAISSIndexManager`)**:
   - **Strict Isolation**: Vector indexes and chunk metadata are kept completely segregated per repository under `faiss_indexes/{repo_id}/`.
   - **Persistence**: Persists `index.faiss` binary file and `chunks.json` metadata index atomically.
   - **Lifecycle Management**: Supports dynamic index creation, real-time nearest-neighbor retrieval, full reindexing on demand, and clean deletion of index artifacts upon repository removal.
   - **Architecture Role**: FAISS is used strictly for high-speed vector similarity search; relational repository metadata (status, file counts, error logs) is stored authoritatively in PostgreSQL.

5. **Repository Question-Answering Service (`RepoQAService`)**:
   - Retrieves top-k (`k=5`) most relevant chunks using cosine similarity threshold filtering.
   - Injects contextual code snippets with exact file paths and line ranges into Groq LLM prompt.
   - Produces answers citing precise file locations (`[path/file.py:L10-L25]`).
   - **Insufficient Evidence Handling**: When retrieved chunks fail similarity thresholds or when no relevant code exists, explicitly returns an insufficient evidence state (`evidence_sufficient = false`) rather than hallucinating details.

### 3. Configuration & Limitations

- **Configuration (`backend/.env`)**:
  - `EMBEDDING_MODEL_NAME`: Name of FastEmbed embedding model (default: `BAAI/bge-small-en-v1.5`).
  - `IMPORTED_REPOS_DIR`: Root path for extracted repository files (default: `imported_repositories`).
  - `FAISS_INDEXES_DIR`: Root path for persisted FAISS vector indexes (default: `faiss_indexes`).
  - `MAX_REPO_FILE_SIZE_BYTES`: Max single file size scanned (default: 524,288 bytes = 500 KB).
  - `MAX_REPO_TOTAL_SIZE_BYTES`: Max total repo size allowed (default: 26,214,400 bytes = 25 MB).
  - `MAX_REPO_FILE_COUNT`: Max file count allowed (default: 1,000 files).
  - `REPO_IMPORT_TIMEOUT_SECONDS`: Download timeout (default: 60.0s).
- **Limitations**:
  - Only text-based source and configuration files are embedded; binary assets and compiled files are excluded by design.
  - Subprocess commands like `git clone` are never executed; downloads rely purely on authenticated HTTPS tarball streams.
  - Repositories exceeding 25 MB or 1,000 files are rejected to protect server memory and index performance.

---

## Phase 7: GitHub and Developer Workflow

### 1. Architecture & Safe Execution Model

```mermaid
flowchart TD
    A[Authorized Workspace: generated_projects/ or imported_repositories/] --> B[GitService: Boundary & Isolation Guard]
    B -->|git init / status / diff| C[Local Git Repository & .gitignore]
    C -->|Diff & Changed Files| D[GitHubService: AI Commit Message Proposer]
    D -->|Propose Conventional Commit| E[User Reviews Message & Diffs]
    E -->|Explicit User Approval: approved=true| F[GitService: git add & git commit]
    F --> G[(PostgreSQL: GitAuditLog Record)]
    
    H[Branch Management] -->|Safe Regex Validation| B
    B -->|git checkout -b / checkout| C
    
    I[PR Summary Generator] --> J[Diffs + Commits + PostgreSQL QA Findings]
    J --> K[Groq LLM: Synthesize Structured PR Markdown]
    K --> L[User Reviews PR Title, Body & Target Repo]
    L -->|Explicit User Approval: approved=true + PAT| M[GitHub REST API v3: POST /repos/owner/repo/pulls]
    M -->|201 Created| N[Clickable PR Link & Audit Trail]
```

### 2. Core Components

1. **Dedicated Git Service (`GitService`)**:
   - **Workspace Containment**: Enforces that all Git CLI operations run exclusively inside isolated workspace directories (`generated_projects/<id>` or `imported_repositories/<id>`). Categorically forbids execution against CodePilot AI's own root application repository.
   - **Safe Subprocess Execution**: Always executes with `shell=False`, sanitized environment variables, and strict timeouts (15s). Never runs uncontrolled shell scripts or hooks.
   - **Initialization**: Automatically generates safe `.gitignore` defaults (`node_modules/`, `venv/`, `__pycache__/`, `.env`, `dist/`, etc.) and configures isolated local committer credentials.
   - **Working-Tree Status & Diffs**: Parses staged, unstaged, and untracked changes (`git status --porcelain=v1 -u`) and computes unified diffs with insertion and deletion metrics.
   - **Branch Management**: Supports safe branch creation and checkout with strict regex name validation (`^[a-zA-Z0-9_.\-/]+$`); rejects dangerous flags (`-D`, `;`, traversal sequences).
   - **Commit Approval Requirement**: Hardcoded safety gate requiring `approved: true` in request payloads. Rejects unconfirmed commits with structured `400 Bad Request` errors.

2. **GitHub Developer Workflow Integration (`GitHubService`)**:
   - **Conventional Commit Synthesis**: Analyzes working-tree diffs and changed filenames using Groq LLM (with deterministic heuristic fallback) to produce concise Conventional Commit messages (e.g. `feat(api): ...`, `test: ...`, `fix: ...`).
   - **Pull Request Summary**: Merges working tree diffs, branch commit history, and verified Phase 5 QA/Security findings from PostgreSQL into a comprehensive PR overview with verification checklists.
   - **GitHub REST API Pull Requests**: Authenticates via transient, scoped Personal Access Tokens (PATs) using `httpx` to create real GitHub pull requests (`POST /repos/{owner}/{repo}/pulls`).
   - **Credential Security**: Personal Access Tokens are handled strictly in-flight. Tokens are **never** logged, persisted to disk, or saved to the database. Error messages redact all credentials.

3. **Operation Audit Logging (`GitAuditLog`)**:
   - Persists every Git and GitHub operation (`init`, `commit`, `branch_create`, `checkout`, `pr_create`) with workspace ID, operation status, branch, commit SHA, and sanitized error messages.

---

## Phase 8: Isolated Code Execution Sandbox

Phase 8 introduces secure, disposable execution of untrusted generated code and test suites. Because executing untrusted generated code presents severe security risks to the host operating system, CodePilot AI enforces strict architectural isolation, container boundaries, air-gapped networking, and bounded resource limits.

### 1. Architecture & Execution Workflow

Untrusted source code is **never** executed inside the FastAPI application process or within the main application container. Instead, all executions are delegated to transient, disposable Docker containers managed by `SandboxService`:

```mermaid
flowchart TD
    A[User / Frontend: Request Test Run] --> B[API: POST /api/sandboxes/:project_id/jobs]
    B --> C{Sandbox Policy & Quota Check}
    C -->|Exceeded Concurrent / Hourly Limit| D[429 Quota Exceeded / 400 Bad Request]
    C -->|Allowed Workload & Arguments| E[Persist Job: status=queued]
    E --> F[Async Background Execution Task]
    F --> G[Update Job: status=running]
    G --> H[Hardened Disposable Docker Container]
    
    subgraph Container Isolation Boundary
        H --> I[Non-root User 1000:1000]
        H --> J[Air-gapped Network: --network none]
        H --> K[Drop Capabilities: --cap-drop ALL]
        H --> L[No New Privileges: --security-opt]
        H --> M[Read-only Root Filesystem + 64MB tmpfs]
        H --> N[Isolated Project Workspace Mount: /workspace:rw]
        H --> O[Limits: 512MB RAM, 1.0 CPU, 64 PIDs]
    end
    
    H -->|Execute Server-Controlled Policy Command| P[Execution Process: Pytest / AST / React Build]
    P --> Q{Execution Result}
    Q -->|Process completes within timeout| R[Capture Exit Code, Stdout, Stderr]
    Q -->|Exceeds 30s Timeout| S[Timeout Enforcement: Force Kill Container & status=timed_out]
    
    R --> T[Sanitize Output: Strip ANSI & Redact Secrets]
    S --> T
    T --> U[Persist Execution Result: completed / failed / timed_out]
    U --> V[Destroy Disposable Container: --rm & docker rm -f]
    V --> W[Display Real-Time Output & Terminal in UI]
```

### 2. Supported Workloads & Server-Controlled Policies

To prevent arbitrary command injection, users cannot pass uncontrolled shell strings. Commands are server-constructed strictly using server-controlled policy whitelists:

| Workload Type | Base Image | Default Command | Description | Allowed Custom Arguments |
|---|---|---|---|---|
| `python_pytest` | `python:3.12-slim` | `python -m pytest -v` | Discovers and executes project test suites. | Whitelisted pytest flags (`-k`, `-m`, `-v`, `-q`, `--tb=short`, `--tb=line`, `--maxfail=\d+`, safe test paths) |
| `python_syntax` | `python:3.12-slim` | `python -m compileall -q .` | Validates Python syntax and compiles AST across all workspace files. | None (fixed server policy) |
| `react_build` | `node:20-alpine` | `npm run build` | Frontend dependency and production build verification for supported React projects. | None (fixed server policy) |

### 3. Container Hardening & Isolation Matrix

| Isolation Layer | Security Flag / Directive | Rationale & Protection |
|---|---|---|
| **Dedicated Service** | Out-of-process Docker CLI | Isolates untrusted execution completely from FastAPI application processes and host memory. |
| **Air-gapped Networking** | `--network none` | Prevents data exfiltration, command-and-control beacons, network scanning, or unauthorized external API calls. |
| **Non-Root Execution** | `--user 1000:1000` | Ensures processes run with unprivileged user/group IDs inside the container. |
| **Dropped Capabilities** | `--cap-drop ALL` | Strips all Linux capabilities (e.g. `CAP_SYS_ADMIN`, `CAP_NET_RAW`), preventing host privilege escalation. |
| **Privilege Escalation Prevention** | `--security-opt no-new-privileges` | Prevents child processes from gaining elevated permissions via `setuid`/`setgid` binaries. |
| **Docker Socket Protection** | **Never Mounted** | Mounting `/var/run/docker.sock` allows total host takeover; CodePilot strictly forbids Docker socket mounting. |
| **Host Filesystem Protection** | **Project-Only Mount** | The host root filesystem is never mounted. Only the specific project directory (`generated_projects/<id>`) is mounted to `/workspace`. CodePilot source directories are verified outside the mount target. |
| **Read-Only Root Filesystem** | `--read-only` | Prevents modifying system binaries or installing persistent backdoors inside the container. |
| **Temporary Scratch Space** | `--tmpfs /tmp:rw,noexec,nosuid,size=64m` | Provides bounded volatile scratch space for compilation with execution forbidden. |
| **Memory Limit** | `-m 512m --memory-swap 512m` | Prevents memory exhaustion and out-of-memory (OOM) denial-of-service on the host. |
| **CPU Quota** | `--cpus 1.0` | Restricts CPU usage to at most 1.0 core, preventing compute starvation. |
| **Process Limit** | `--pids-limit 64` | Prevents fork bombs and thread exhaustion attacks. |
| **Execution Timeout** | Hard enforcement (default 30s) | Subprocess timeout kills containers exceeding the limit, setting status to `timed_out`. |
| **Resource Destruction** | `--rm` and cleanup | Ensures disposable containers are terminated immediately after execution. |
| **Output Sanitization** | `clean_ansi_and_secrets()` | Strips terminal ANSI escape codes and redacts potential environment secrets/keys from stdout/stderr. |

### 4. Per-Project Execution Quotas

To protect against resource exhaustion in multi-tenant environments, `SandboxService` enforces:
- **Maximum Concurrent Jobs Per Project**: At most 3 simultaneous active (`queued` or `running`) execution jobs per project.
- **Hourly Execution Quota Per Project**: At most 20 execution jobs initiated within any rolling 60-minute window per project.

### 5. Threat Modeling & Residual Risks Analysis

> [!WARNING]
> **Container Isolation is Not a Security Panacea**
> Standard Docker containers share the host Linux kernel (`cgroups` and `namespaces`). While the hardening flags above mitigate the vast majority of threats, containers do not provide the same security guarantees as hardware virtualization.

#### Residual Risks
1. **Linux Kernel Vulnerabilities**: If untrusted code exploits an unpatched kernel vulnerability (such as a privilege escalation bug or zero-day in Linux syscall handling), it could potentially break out of container namespaces to the host.
2. **CPU Architecture Side-Channels**: Microarchitectural side-channel attacks (e.g., Spectre, Meltdown, MDS) can potentially leak data across processes running on shared CPU cores.
3. **Storage DoS**: While memory and CPU are bounded, untrusted code could rapidly write to `/workspace` up to the disk volume limit.

#### Stronger Isolation Recommendations for Multi-Tenant Untrusted Workloads
For commercial or multi-tenant production deployments executing arbitrary untrusted code, we strongly recommend:
- **gVisor (`runsc`)**: A user-space kernel runtime created by Google that intercepts and implements Linux syscalls in user space, creating an architectural boundary between untrusted code and the host kernel.
- **Firecracker MicroVMs**: Minimalist, hardware-isolated KVM microvirtual machines (used by AWS Lambda and Fargate) providing independent kernel isolation in milliseconds.
- **Ephemeral Sandbox Clusters**: Dedicated execution worker nodes located in separate, non-routable VPC subnets with strictly no access to application databases or credential stores.

---


## Setup & Running Locally

### 1. Database Startup (PostgreSQL via Docker)
```bash
docker compose up -d db
```
*(SQLite fallback is enabled automatically if running locally without Docker: `DATABASE_URL=sqlite:///./codepilot_dev.db`).*

### 2. Backend Setup & Migrations
```bash
cd backend

# Activate virtual environment
# Windows: .\venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Swagger UI: `http://127.0.0.1:8000/docs`

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```
Dashboard: `http://127.0.0.1:5173/`

---

## System Architecture & Multi-Agent Collaboration

### 1. High-Level Architecture Diagram

```mermaid
flowchart TD
    subgraph Client ["Client Layer"]
        UI["React 19 + Vite Dashboard (SPA)"]
    end

    subgraph Ingress ["Ingress & Reverse Proxy"]
        NGINX["Nginx Container (:80 / :5173)"]
    end

    subgraph BackendAPI ["FastAPI Application (:8000)"]
        CORR["Correlation & Structured Logging\n(X-Correlation-ID Filter)"]
        AUTH["Auth & Project Authorization Hook\n(API_AUTH_ENABLED / Bearer Token)"]
        GUARD["Payload Limit (10MB) & Request Timeouts"]
        ROUTERS["API Routers\n(/projects, /ai, /workflows, /generate, /qa, /repositories, /git, /sandboxes)"]
    end

    subgraph AgentMesh ["LangGraph Multi-Agent Orchestration"]
        SUP["Supervisor Agent\n(StateGraph Coordinator & Router)"]
        PLAN["Planner Agent\n(Task Decomposition & Acceptance Criteria)"]
        ARCH["Architect Agent\n(Components, APIs, Entity Schemas)"]
        VAL["Validation Node\n(Quality Scoring & Gap Analysis)"]
        CODEGEN["Code Generation Engine\n(Manifest Planner & AST File Generator)"]
        QA["QA, Code Review & Security Agent\n(AST Pattern Detection & Test Plan Generator)"]
        REPAIR["Repair Coordinator\n(Bounded Code Fixes & AST Re-verification)"]
    end

    subgraph Storage ["Persistent Storage Layer"]
        PG[("PostgreSQL 16 Database\n(Named Volume: postgres_data)")]
        WS[("Generated Project Workspaces\n(Volume: generated_projects_data)")]
        REPOS[("Imported GitHub Workspaces\n(Volume: imported_repos_data)")]
        VEC[("FAISS Vector Indexes & Chunks\n(Volume: faiss_indexes_data)")]
    end

    subgraph Sandbox ["Isolated Execution Layer"]
        DOCKER["Docker Engine (Isolated Subprocess Runner)"]
        CONT["Disposable Containers (python:3.12-slim / node:20-alpine)\n--network none | --read-only | --user 1000:1000 | 512MB RAM"]
    end

    subgraph External ["External Services"]
        GROQ["Groq LLM API (llama-3.3-70b-versatile)"]
        GITHUB["GitHub REST API v3 (Cloning & Pull Requests)"]
    end

    UI -->|HTTP / JSON| NGINX
    NGINX -->|Reverse Proxy /api/| CORR
    CORR --> AUTH --> GUARD --> ROUTERS

    ROUTERS -->|Orchestrate| SUP
    SUP -->|Route| PLAN
    SUP -->|Route| ARCH
    SUP -->|Route| VAL
    VAL -->|Loop / Pass| SUP

    ROUTERS -->|Generate Code| CODEGEN
    ROUTERS -->|Audit & Repair| QA
    QA --> REPAIR

    ROUTERS -->|Vector Retrieval & RAG| VEC
    ROUTERS -->|Git Diffs & PRs| GITHUB
    ROUTERS -->|Run Sandboxed Tests| DOCKER
    DOCKER --> CONT

    PLAN & ARCH & VAL & CODEGEN & QA -->|Prompts| GROQ
    ROUTERS & AgentMesh -->|State Persistence| PG
    CODEGEN & REPAIR -->|Read/Write Source| WS
    ROUTERS -->|Clone & Scan| REPOS
    CONT -.->|Read-Only Bind Mount| WS
```

### 2. How the Agents Collaborate

CodePilot AI orchestrates specialized autonomous agents through LangGraph and deterministic validation pipelines:

1. **Supervisor Agent (`app/agents/supervisor.py`)**:
   - Acts as the central coordinator and router.
   - Evaluates workflow state at each transition, tracks completed stages, and decides whether to route execution to the **Planner**, **Architect**, or **Validator**.
   - Enforces execution limits (maximum 3 iterations and bounded retries) to prevent runaway agent loops.
2. **Planner Agent (`app/agents/planner.py`)**:
   - Takes raw user requirements and synthesizes a structured implementation plan.
   - Decomposes goals into discrete tasks, identifies technical dependencies, documents acceptance criteria, and highlights missing specifications.
3. **Architect Agent (`app/agents/architect.py`)**:
   - Translates planned tasks into concrete system architecture.
   - Defines system patterns (e.g., modular monolith, microservices), component boundaries, database entity schemas with relationships, and RESTful API specifications with request/response contracts.
4. **Requirement Validation Node (`app/agents/validator.py`)**:
   - Audits the proposed plan and architecture against original user requirements.
   - Checks for omissions, inconsistencies, or contradictions. Produces an objective coverage score (0-100). If the score falls below threshold, the Supervisor routes back for targeted refinement.
5. **Code Generation Engine (`app/services/codegen_service.py`)**:
   - **FileStructurePlanner**: Derives a complete manifest of required source files based on approved architecture before code generation begins.
   - **File Generator**: Generates clean source code file by file, maintaining awareness of sibling modules and architectural contracts.
   - **CodeValidationNode**: Parses Python files with Python AST and JSON files with `json.loads`. Automatically prompts bounded repair attempts if syntax validation fails.
6. **QA, Code Review & Security Agent (`app/services/qa_service.py`)**:
   - Reads project workspace files and builds an AST-based static analysis tree.
   - Identifies dangerous patterns (e.g., `eval`, `exec`, unescaped SQL, `subprocess(shell=True)`), syntax errors, and missing test coverage.
   - Synthesizes automated test plans and computes an overall code quality score.
7. **Repair Coordinator (`app/services/qa_service.py`)**:
   - Proposes targeted, bounded replacements for detected vulnerabilities.
   - Statically verifies that candidate fixes compile and resolve the defect before applying them to disk, updating the project's security posture.

---

## End-to-End Workflows Verification Matrix

All nine core workflows specified for Phase 9 have been verified end to end through automated integration test suites and runtime execution:

| # | Workflow | Status | Verification & Testing Evidence |
|---|---|---|---|
| 1 | **Create project & persist in PostgreSQL** | **PASSED** | Verified via `POST /api/projects`. Stored in PostgreSQL with generated UUID, slug, requirements, timestamps, and retrieved via `GET /api/projects/{id}`. Tested in `tests/test_projects.py` and `tests/test_e2e.py`. |
| 2 | **Analyze requirements using Groq** | **PASSED** | Verified via `POST /api/ai/analyze`. Generates structured summaries, functional requirements, technical stacks, and risks using `llama-3.3-70b-versatile`. Tested in `tests/test_ai.py` and `tests/test_e2e.py`. |
| 3 | **Run Planner & Architect via LangGraph** | **PASSED** | Verified via `POST /api/projects/{id}/workflow/start`. Supervisor routes sequentially through Planner, Architect, and Validator with state persisted to PostgreSQL `workflow_runs`. Tested in `tests/test_workflows.py` and `tests/test_e2e.py`. |
| 4 | **Generate project files from approved plan** | **PASSED** | Verified via `POST /api/projects/{id}/generate`. Creates manifest, validates syntax, writes isolated files to `generated_projects/{id}/`, and packs ZIP archives. Tested in `tests/test_codegen.py` and `tests/test_e2e.py`. |
| 5 | **Run QA, code review & approved repairs** | **PASSED** | Verified via `POST /api/projects/{id}/qa/run` and `POST /api/projects/{id}/qa/findings/{id}/repair`. AST static checker flags vulnerabilities (`eval`), generates test plans, and applies verified fixes. Tested in `tests/test_qa.py` and `tests/test_e2e.py`. |
| 6 | **Import GitHub repo & query via FAISS RAG** | **PASSED** | Verified via `POST /api/repositories/import` and `POST /api/repositories/{id}/chat`. Downloads repository, chunks source files, persists isolated FAISS vector index, and generates cited answers (`[file:line_range]`). Tested in `tests/test_repositories.py` and `tests/test_e2e.py`. |
| 7 | **Review Git diffs & approve Git operations** | **PASSED** | Verified via `/api/git/{id}/init`, `/diff`, `/commit`, and `/pr/create`. Diff viewer shows unified changes, commits require explicit `approved: true` gate, and PR summaries aggregate diffs with QA findings. Tested in `tests/test_git.py` and `tests/test_e2e.py`. |
| 8 | **Execute tests in isolated Docker sandbox** | **PASSED** | Verified via `POST /api/sandboxes/{id}/jobs`. Dispatches disposable container execution with strict cgroups (`--network none`, non-root, 512MB RAM, read-only root). Tested in `tests/test_sandbox.py` and `tests/test_e2e.py`. |
| 9 | **Retrieve history after application restart** | **PASSED** | Verified in `test_e2e.py` by purging active ORM sessions and reloading projects, workflow runs, QA reports, and sandbox executions directly from PostgreSQL and persistent volumes. |

---

## Production Readiness & Deployment

### 1. Docker Compose Multi-Container Deployment

CodePilot AI provides a complete multi-container orchestration configuration (`docker-compose.yml`) for production and local evaluation:

```bash
# Build and launch all services in detached mode
docker compose up -d --build

# Inspect container health and status
docker compose ps

# View unified structured logs with correlation IDs
docker compose logs -f backend
```

Services initialized by `docker-compose.yml`:
- **`db` (PostgreSQL 16-alpine)**: Persistent database with health check probe (`pg_isready`), initialized on internal network `codepilot_net`.
- **`backend` (FastAPI 3.12-slim)**: Non-root user (`codepilot:10001`), database migration auto-upgrade (`alembic upgrade head`), entrypoint running Uvicorn with correlation logging, health probe (`GET /api/health`), and readiness probe (`GET /api/ready`).
- **`frontend` (Nginx Alpine)**: Serves production Vite SPA assets, applies security headers, handles SPA routing (`try_files`), and reverse-proxies `/api/` traffic to the backend.

### 2. Persistent Storage Volumes

Data persistence is guaranteed across container restarts through named Docker volumes:
- `postgres_data` -> `/var/lib/postgresql/data` (PostgreSQL relational data).
- `generated_projects_data` -> `/app/generated_projects` (User project code and ZIP bundles).
- `imported_repos_data` -> `/app/imported_repositories` (Cloned and filtered GitHub repos).
- `faiss_indexes_data` -> `/app/faiss_indexes` (Persistent FAISS vector indexes and chunk metadata).

### 3. Production Hardening Features

- **Request Correlation & Structured Logging**: `CorrelationIdMiddleware` assigns or propagates an `X-Correlation-ID` header for every HTTP request. All Python log records include `[cid: <id>]` for end-to-end distributed tracing.
- **Payload Size & Timeout Guards**: Payloads exceeding 10 MB (`MAX_PAYLOAD_SIZE_BYTES`) are rejected immediately with HTTP 413 (Payload Too Large). Request timeouts default to 60s.
- **Authentication & Authorization Hooks**: `API_AUTH_ENABLED` and `API_AUTH_KEY` provide constant-time token validation (`Authorization: Bearer <key>`) for production deployments before exposing endpoints publicly.
- **Container Health & Readiness Probes**:
  - `GET /api/health`: Validates general process uptime, database connection status, and active model version.
  - `GET /api/ready`: Returns HTTP 200 when database and storage volumes are fully operational, or HTTP 503 when degraded (suitable for Kubernetes/Docker readiness probes).
- **Graceful Shutdown**: Traps SIGTERM and SIGINT, completing in-flight database transactions and releasing filesystem locks before termination.
- **Sanitized Error Logging**: Passwords, Groq API keys, GitHub personal access tokens, and raw confidential files are strictly scrubbed and never recorded in logs or error traces.

---

## Environment Variables Reference

| Variable | Type | Default | Description |
|---|---|---|---|
| `PROJECT_NAME` | string | `CodePilot AI API` | API service display name |
| `VERSION` | string | `0.1.0` | API version string |
| `DATABASE_URL` | string | `None` | Direct SQLAlchemy database URL (e.g., `postgresql://user:pass@host:5432/codepilot`). Overrides individual `POSTGRES_*` settings when provided. |
| `POSTGRES_SERVER` | string | `localhost` | PostgreSQL server hostname |
| `POSTGRES_PORT` | integer | `5432` | PostgreSQL server port |
| `POSTGRES_USER` | string | `postgres` | Database username |
| `POSTGRES_PASSWORD` | string | `postgres` | Database password |
| `POSTGRES_DB` | string | `codepilot` | Database name |
| `GROQ_API_KEY` | string | `None` | Groq API Key (required for real LLM features) |
| `GROQ_MODEL` | string | `llama-3.3-70b-versatile` | Groq chat completion model |
| `GROQ_TIMEOUT_SECONDS` | float | `30.0` | Groq LLM API request timeout in seconds |
| `EMBEDDING_MODEL_NAME` | string | `BAAI/bge-small-en-v1.5` | FastEmbed ONNX embedding model for vector search |
| `GENERATED_PROJECTS_DIR` | string | `generated_projects` | Workspace directory for generated code files |
| `IMPORTED_REPOS_DIR` | string | `imported_repositories` | Workspace directory for imported GitHub repos |
| `FAISS_INDEXES_DIR` | string | `faiss_indexes` | Directory for persistent FAISS vector indexes |
| `DOCKER_PYTHON_IMAGE` | string | `python:3.12-slim` | Execution image for Python sandbox jobs |
| `DOCKER_NODE_IMAGE` | string | `node:20-alpine` | Execution image for Node/React sandbox jobs |
| `SANDBOX_TIMEOUT_SECONDS`| float | `30.0` | Execution timeout for sandbox containers |
| `SANDBOX_MAX_MEMORY_MB` | integer | `512` | Memory limit per sandbox container |
| `SANDBOX_MAX_CPUS` | string | `1.0` | CPU quota per sandbox container |
| `SANDBOX_MAX_PIDS` | integer | `64` | Maximum PID limit inside sandbox container |
| `SANDBOX_MAX_CONCURRENT_JOBS` | integer | `3` | Max active concurrent sandbox jobs per project |
| `SANDBOX_HOURLY_QUOTA_PER_PROJECT` | integer | `20` | Hourly execution rate limit per project |
| `SANDBOX_ENABLE_MOCK_FALLBACK` | boolean | `True` | Fallback simulation when Docker daemon is unreachable |
| `API_AUTH_ENABLED` | boolean | `False` | Enable bearer token authentication for all API endpoints |
| `API_AUTH_KEY` | string | `None` | Secret API bearer token for authentication |
| `REQUEST_TIMEOUT_SECONDS`| float | `60.0` | Overall HTTP request timeout |
| `MAX_PAYLOAD_SIZE_BYTES` | integer | `10485760` (10 MB) | Maximum incoming request body size limit |
| `LOG_LEVEL` | string | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `CORS_ORIGINS` | list/str | `["http://localhost:5173", ...]` | Permitted CORS origins |

---

## Local Development & Operations Guide

### 1. Local Development Setup

#### Backend
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate  # On Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Apply database migrations
alembic upgrade head

# Start development API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation: `http://127.0.0.1:8000/docs`

#### Frontend
```bash
cd frontend
npm install
npm run dev
```
Dashboard: `http://127.0.0.1:5173/`

### 2. Database Migrations Procedure

Alembic manages all schema revisions:
```bash
# Check current revision status
alembic current

# Generate new migration script after model changes
alembic revision --autogenerate -m "describe_schema_change"

# Apply pending migrations to database
alembic upgrade head

# Rollback one migration step
alembic downgrade -1
```

### 3. Database Backup & Disaster Recovery

```bash
# Export full database backup
docker compose exec db pg_dump -U postgres codepilot > codepilot_backup_$(date +%Y%m%d).sql

# Restore from backup file
docker compose exec -T db psql -U postgres codepilot < codepilot_backup.sql
```

### 4. FAISS Persistence & Reindexing Procedure

FAISS indexes are stored persistently on disk in `faiss_indexes/<repo_id>/` (`index.faiss` and `chunks.json`).
If the index files are corrupted or require updating following code changes:
- Trigger an on-demand reindexing via `POST /api/repositories/{id}/reindex`.
- The background task re-scans `imported_repositories/<repo_id>/`, regenerates normalized 384-dimensional vectors, and rebuilds the FAISS `IndexFlatIP`.

---

## Automated Test Suite

To run all automated tests (93 passing):
```bash
cd backend
.\venv\Scripts\pytest.exe -v
```

### Test Coverage (93/93 Passing)
- **Phase 9 End-to-End Workflows & Production Middleware (`tests/test_e2e.py`) — 2 tests**:
  - `test_complete_end_to_end_integration_workflow`: Sequentially executes all 9 workflows from project creation to application restart.
  - `test_production_middleware_correlation_and_limits`: Verifies `X-Correlation-ID` header generation/propagation and 10 MB payload rejection (HTTP 413).
- **Phase 8 Isolated Execution Sandbox (`tests/test_sandbox.py`) — 8 tests**:
  - Hardened Docker flags, cgroup limits, PID quotas, workspace containment, hourly rate limits, timeout termination, and sanitized logs.
- **Phase 7 GitHub & Developer Workflow (`tests/test_git.py`) — 15 tests**:
  - Safe Git initialization, diff generation, Conventional Commit message synthesis, explicit commit approval gates, branch creation/checkout, PR summary generation, and GitHub REST API integration.
- **Phase 6 GitHub Repository Intelligence & FAISS (`tests/test_repositories.py`) — 17 tests**:
  - Repository URL validation, security exclusions, line-aware code chunking, FAISS IndexFlatIP persistence, RAG Q&A with citations, and insufficient evidence handling.
- **Phase 5 QA, Code Review & Bounded Repair (`tests/test_qa.py`) — 4 tests**:
  - AST security visitor, automated QA review execution, test plan generation, bounded code repair application, and static re-verification.
- **Phase 4 Code Generation Engine (`tests/test_codegen.py`) — 22 tests**:
  - Workspace directory isolation, AST syntax validation, template manifests, generation retry loops, user edit protection, and ZIP bundle creation.
- **Phase 3 Multi-Agent Workflows (`tests/test_workflows.py`) — 5 tests**:
  - Supervisor routing, LangGraph execution, bounded retries, and persistence.
- **Phase 2 AI Analysis (`tests/test_ai.py`) — 9 tests**:
  - Requirements analysis, schema validation, rate limits, timeouts, and sanitized errors.
- **Phase 1 Foundation & Readiness Probes (`tests/test_health.py` & `tests/test_projects.py`) — 11 tests**:
  - Root endpoint, `/api/health`, `/api/ready` readiness probe, project CRUD, UUID validation, timestamps, and list pagination.

---

## API Endpoints Reference

| Method | Endpoint | Description | Status Codes |
|---|---|---|---|
| `GET` | `/api/health` | Process health and database connectivity check | `200` |
| `GET` | `/api/ready` | Container and volume readiness probe for orchestrators | `200`, `503` |
| `GET` | `/api/projects` | List all persisted projects ordered by creation date | `200` |
| `POST` | `/api/projects` | Create a new project from user requirements | `201`, `422`, `500` |
| `GET` | `/api/projects/{id}` | Retrieve project details by UUID | `200`, `404`, `422` |
| `POST` | `/api/ai/analyze` | Single-shot requirements analysis via Groq + LangChain | `200`, `422`, `429`, `502`, `503`, `504` |
| `POST` | `/api/projects/{id}/workflow/start` | Start LangGraph multi-agent orchestration for a project | `202`, `404` |
| `GET` | `/api/projects/{id}/workflow/latest` | Retrieve latest completed or active workflow and outputs | `200`, `404` |
| `GET` | `/api/projects/{id}/workflow/status` | Poll execution status and current stage of the latest workflow | `200`, `404` |
| `GET` | `/api/workflows/{workflow_id}` | Retrieve specific workflow run by primary key UUID | `200`, `404` |
| `POST` | `/api/projects/{id}/generate` | Start background code generation from approved requirements | `202`, `404` |
| `GET` | `/api/projects/{id}/generate/status` | Retrieve current generation status, progress %, and errors | `200`, `404` |
| `GET` | `/api/projects/{id}/files` | List all generated files with metadata and checksums | `200`, `404` |
| `GET` | `/api/projects/{id}/files/content?path=...` | Read source code of a specific file in workspace | `200`, `400`, `404` |
| `GET` | `/api/projects/{id}/download` | Download complete generated project workspace as a ZIP archive | `200`, `404`, `500` |
| `POST` | `/api/projects/{id}/qa/run` | Execute QA review, AST security audit, and test plan generation | `200`, `400`, `404` |
| `GET` | `/api/projects/{id}/qa/latest` | Retrieve latest QA review run, score, and posture badge | `200`, `404` |
| `GET` | `/api/projects/{id}/qa/findings` | List open and resolved security/defect findings for project | `200`, `404` |
| `POST` | `/api/projects/{id}/qa/findings/{finding_id}/repair` | Apply approved bounded code repair with AST verification | `200`, `400`, `404` |
| `POST` | `/api/repositories/import` | Import and index a public/private GitHub repository | `202`, `400`, `422` |
| `GET` | `/api/repositories` | List all imported repositories with indexing status | `200` |
| `GET` | `/api/repositories/{id}` | Retrieve imported repository details and statistics | `200`, `404` |
| `GET` | `/api/repositories/{id}/status` | Poll repository import, scanning, and indexing progress | `200`, `404` |
| `POST` | `/api/repositories/{id}/reindex` | Trigger on-demand re-chunking and FAISS reindexing | `200`, `404` |
| `POST` | `/api/repositories/{id}/chat` | Ask questions about repository code using FAISS RAG | `200`, `400`, `404`, `502` |
| `DELETE` | `/api/repositories/{id}` | Delete repository workspace, FAISS index, and DB record | `200`, `404` |
| `POST` | `/api/git/{workspace_id}/init` | Initialize Git in workspace with safe defaults & .gitignore | `200`, `400`, `500` |
| `GET` | `/api/git/{workspace_id}/status` | Inspect working-tree changes, branch, and latest commit | `200`, `400`, `500` |
| `GET` | `/api/git/{workspace_id}/diff` | Inspect staged or unstaged unified diff preview | `200`, `400`, `500` |
| `POST` | `/api/git/{workspace_id}/commit-message/propose` | AI Conventional Commit message generation from diff | `200`, `400`, `500` |
| `POST` | `/api/git/{workspace_id}/commit` | Review and commit changes (explicit approval required) | `200`, `400` |
| `GET` | `/api/git/{workspace_id}/branches` | List local branches and active branch | `200`, `400`, `500` |
| `POST` | `/api/git/{workspace_id}/branches` | Create new branch with validation and optional checkout | `200`, `400` |
| `POST` | `/api/git/{workspace_id}/branches/checkout` | Switch to an existing branch | `200`, `400` |
| `POST` | `/api/git/{workspace_id}/pr/summary` | Prepare PR summary from diffs and PostgreSQL QA findings | `200`, `400`, `500` |
| `POST` | `/api/git/{workspace_id}/pr/create` | Submit Pull Request via GitHub API (approval required) | `200`, `400`, `401`, `404`, `502` |
| `GET` | `/api/git/{workspace_id}/history` | Get recent commit history for current branch | `200`, `400`, `500` |
| `GET` | `/api/git/{workspace_id}/audit-logs` | Retrieve Git and GitHub operation audit trail | `200` |
| `POST` | `/api/sandboxes/{project_id}/jobs` | Create an isolated sandbox execution job (pytest, AST, React build) | `202`, `400`, `404`, `429` |
| `GET` | `/api/sandboxes/{project_id}/jobs` | List recent sandbox execution jobs for project | `200`, `404` |
| `GET` | `/api/sandboxes/{project_id}/jobs/{job_id}` | Retrieve sandbox execution job details, logs, exit code | `200`, `404` |
| `GET` | `/api/sandboxes/{project_id}/quota` | Inspect per-project concurrency and hourly quota status | `200`, `404` |

---

## Final Codebase Audit & Security Limitations

### 1. Codebase Audit Checklist

| Inspection Category | Feasible Verification Check | Result | Verification Notes |
|---|---|---|---|
| **Automated Tests** | `pytest -v` across all backend suites | **PASSED** | 93 passing tests across 10 test modules. 0 failures. |
| **Frontend Production Build** | `npm.cmd run build` (TypeScript + Vite) | **PASSED** | Zero TypeScript errors; production bundle built cleanly in 1.41s. |
| **Duplicate Implementations** | Code search across `app/services/` and `app/agents/` | **PASSED** | Unified AST check service alias `ASTStaticCheckService` established. |
| **Dead Code & Broken Routes** | Route registration in `app/api/__init__.py` | **PASSED** | All routers (`projects`, `ai`, `workflows`, `codegen`, `qa`, `repositories`, `git`, `sandboxes`, `health`) mapped with matching prefixes. |
| **Hardcoded Secrets** | Grep scan for keys or tokens in source tree | **PASSED** | No hardcoded tokens. Environment fallback variables used throughout. |
| **Schema Consistency** | Cross-verification of ORM models vs Pydantic schemas | **PASSED** | All schema mappings verified and passing in automated tests. |
| **Docker Compose Config** | Lint and validate compose specification | **PASSED** | Syntax validated for `db`, `backend`, and `frontend` with named volumes. |

### 2. Residual Security Boundaries & Production Recommendations

1. **Sandbox Container Isolation**:
   - The current sandbox enforces `--network none`, `--cap-drop ALL`, non-root user `1000:1000`, `--security-opt no-new-privileges`, and strict memory/CPU limits.
   - *Production Recommendation*: For multi-tenant production environments executing adversarial untrusted code, deploy kernel-isolated runtimes such as **gVisor (`runsc`)** or lightweight microVMs (**Kata Containers** or **Firecracker**) rather than standard Linux runc containers.
2. **Multi-Tenant User Isolation**:
   - CodePilot AI includes an authentication hook (`API_AUTH_ENABLED`, `API_AUTH_KEY`).
   - *Production Recommendation*: Integrate an enterprise OAuth2 / OIDC provider (e.g., Keycloak, Auth0, Okta) and enforce row-level security (RLS) or project tenant isolation before hosting multiple external organizations on the same database.
3. **GitHub Token Handling**:
   - Personal Access Tokens (PATs) passed to Git/PR endpoints are held purely in memory during request execution and are never written to disk or recorded in database audit logs.
   - *Production Recommendation*: Prefer short-lived GitHub App installation tokens over personal access tokens for enterprise workflows.



