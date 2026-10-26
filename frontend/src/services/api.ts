import type {
  AnalyzeRequestPayload,
  CreateProjectPayload,
  HealthResponse,
  Project,
  RequirementsAnalysis,
  WorkflowRun,
  WorkflowStartResponse,
} from '../types/project';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiError extends Error {
  statusCode: number;

  constructor(message: string, statusCode: number) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
  }
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options?.headers || {}),
  };

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorMessage = `HTTP error ${response.status}`;
      try {
        const errorJson = await response.json();
        if (typeof errorJson.detail === 'string') {
          errorMessage = errorJson.detail;
        } else if (Array.isArray(errorJson.detail)) {
          // Pydantic validation error array
          errorMessage = errorJson.detail.map((d: { msg?: string; loc?: string[] }) => d.msg || 'Validation error').join(', ');
        }
      } catch {
        // Response was not JSON
      }
      throw new ApiError(errorMessage, response.status);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    // Network errors or connection refused
    throw new ApiError(
      error instanceof Error ? error.message : 'Unable to connect to backend server',
      0
    );
  }
}

export const api = {
  /**
   * Health check query to backend
   */
  async getHealth(): Promise<HealthResponse> {
    return request<HealthResponse>('/api/health');
  },

  /**
   * Retrieve list of all projects
   */
  async getProjects(): Promise<Project[]> {
    return request<Project[]>('/api/projects');
  },

  /**
   * Retrieve single project by UUID
   */
  async getProject(projectId: string): Promise<Project> {
    return request<Project>(`/api/projects/${projectId}`);
  },

  /**
   * Retrieve engineering implementation report for project (Phase G)
   */
  async getEngineeringReport(projectId: string): Promise<{ project_id: string; project_name: string; engineering_report: string }> {
    return request<{ project_id: string; project_name: string; engineering_report: string }>(`/api/projects/${projectId}/report`);
  },

  /**
   * Create a new project with user requirements
   */
  async createProject(payload: CreateProjectPayload): Promise<Project> {
    return request<Project>('/api/projects', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Analyze software requirements using Groq AI
   */
  async analyzeRequirements(payload: AnalyzeRequestPayload): Promise<RequirementsAnalysis> {
    return request<RequirementsAnalysis>('/api/ai/analyze', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Start LangGraph multi-agent workflow for a project
   */
  async startProjectWorkflow(
    projectId: string,
    payload?: { pipeline_type?: string; repo_id?: string }
  ): Promise<WorkflowStartResponse> {
    return request<WorkflowStartResponse>(`/api/projects/${projectId}/workflow/start`, {
      method: 'POST',
      body: JSON.stringify(payload || { pipeline_type: 'full' }),
    });
  },

  /**
   * Retrieve latest workflow execution and architectural results for a project
   */
  async getLatestProjectWorkflow(projectId: string): Promise<WorkflowRun> {
    return request<WorkflowRun>(`/api/projects/${projectId}/workflow/latest`);
  },

  /**
   * Poll current workflow execution status for a project
   */
  async getProjectWorkflowStatus(projectId: string): Promise<WorkflowRun> {
    return request<WorkflowRun>(`/api/projects/${projectId}/workflow/status`);
  },

  /**
   * Retrieve workflow run by UUID
   */
  async getWorkflowById(workflowId: string): Promise<WorkflowRun> {
    return request<WorkflowRun>(`/api/workflows/${workflowId}`);
  },

  /**
   * Start background code generation for a project
   */
  async startCodeGeneration(
    projectId: string,
    payload?: import('../types/project').GenerateStartRequest
  ): Promise<import('../types/project').GenerateStatusResponse> {
    return request<import('../types/project').GenerateStatusResponse>(
      `/api/projects/${projectId}/generate`,
      {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }
    );
  },

  /**
   * Retrieve current code generation status and progress
   */
  async getCodeGenerationStatus(
    projectId: string
  ): Promise<import('../types/project').GenerateStatusResponse> {
    return request<import('../types/project').GenerateStatusResponse>(
      `/api/projects/${projectId}/generate/status`
    );
  },

  /**
   * List generated files for a project
   */
  async getGeneratedFiles(
    projectId: string
  ): Promise<import('../types/project').GeneratedFile[]> {
    return request<import('../types/project').GeneratedFile[]>(
      `/api/projects/${projectId}/files`
    );
  },

  /**
   * Retrieve source content for a single generated file
   */
  async getFileContent(
    projectId: string,
    filePath: string
  ): Promise<import('../types/project').FileContentResponse> {
    const encoded = encodeURIComponent(filePath);
    return request<import('../types/project').FileContentResponse>(
      `/api/projects/${projectId}/files/content?path=${encoded}`
    );
  },

  /**
   * Get direct URL to download generated project zip
   */
  getProjectDownloadUrl(projectId: string): string {
    return `${API_BASE_URL}/api/projects/${projectId}/download`;
  },

  /**
   * Retrieve synthesized documentation & engineering report for a project
   */
  async getProjectReport(projectId: string): Promise<Record<string, any>> {
    return request<Record<string, any>>(`/api/projects/${projectId}/report`);
  },

  /**
   * Import an authorized GitHub repository (Phase 6)
   */
  async importRepository(
    payload: import('../types/project').RepoImportRequest
  ): Promise<import('../types/project').ImportedRepository> {
    return request<import('../types/project').ImportedRepository>(
      '/api/repositories/import',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );
  },

  /**
   * List all imported GitHub repositories
   */
  async getRepositories(): Promise<import('../types/project').ImportedRepository[]> {
    return request<import('../types/project').ImportedRepository[]>('/api/repositories');
  },

  /**
   * Get single repository details
   */
  async getRepository(
    repoId: string
  ): Promise<import('../types/project').ImportedRepository> {
    return request<import('../types/project').ImportedRepository>(
      `/api/repositories/${repoId}`
    );
  },

  /**
   * Poll repository import and FAISS indexing status
   */
  async getRepositoryStatus(
    repoId: string
  ): Promise<import('../types/project').ImportedRepository> {
    return request<import('../types/project').ImportedRepository>(
      `/api/repositories/${repoId}/status`
    );
  },

  /**
   * Re-index repository code into FAISS vector index
   */
  async reindexRepository(
    repoId: string
  ): Promise<import('../types/project').ImportedRepository> {
    return request<import('../types/project').ImportedRepository>(
      `/api/repositories/${repoId}/reindex`,
      { method: 'POST' }
    );
  },

  /**
   * Ask questions about repository code using RAG and vector retrieval
   */
  async chatRepository(
    repoId: string,
    question: string,
    topK: number = 4
  ): Promise<import('../types/project').RepoChatResponse> {
    return request<import('../types/project').RepoChatResponse>(
      `/api/repositories/${repoId}/chat`,
      {
        method: 'POST',
        body: JSON.stringify({ question, top_k: topK }),
      }
    );
  },

  /**
   * Delete repository workspace files and isolated FAISS index
   */
  async deleteRepository(
    repoId: string
  ): Promise<{ message: string }> {
    return request<{ message: string }>(
      `/api/repositories/${repoId}`,
      { method: 'DELETE' }
    );
  },

  /**
   * Initialize Git in project/repository workspace (Phase 7)
   */
  async initGit(
    workspaceId: string
  ): Promise<import('../types/project').GitStatusResponse> {
    return request<import('../types/project').GitStatusResponse>(
      `/api/git/${workspaceId}/init`,
      { method: 'POST' }
    );
  },

  /**
   * Inspect Git status, branch, and working-tree changes
   */
  async getGitStatus(
    workspaceId: string
  ): Promise<import('../types/project').GitStatusResponse> {
    return request<import('../types/project').GitStatusResponse>(
      `/api/git/${workspaceId}/status`
    );
  },

  /**
   * Inspect working-tree unified diff preview
   */
  async getGitDiff(
    workspaceId: string,
    cached: boolean = false,
    filePath?: string
  ): Promise<import('../types/project').GitDiffResponse> {
    let url = `/api/git/${workspaceId}/diff?cached=${cached}`;
    if (filePath) {
      url += `&file_path=${encodeURIComponent(filePath)}`;
    }
    return request<import('../types/project').GitDiffResponse>(url);
  },

  /**
   * Generate an AI-assisted conventional commit message from diff
   */
  async proposeCommitMessage(
    workspaceId: string
  ): Promise<import('../types/project').GitCommitProposeResponse> {
    return request<import('../types/project').GitCommitProposeResponse>(
      `/api/git/${workspaceId}/commit-message/propose`,
      { method: 'POST' }
    );
  },

  /**
   * Review and commit staged or working-tree changes (requires approved: true)
   */
  async createCommit(
    workspaceId: string,
    payload: import('../types/project').GitCommitRequest
  ): Promise<import('../types/project').GitCommitResponse> {
    return request<import('../types/project').GitCommitResponse>(
      `/api/git/${workspaceId}/commit`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );
  },

  /**
   * List local workspace branches and active branch
   */
  async listBranches(
    workspaceId: string
  ): Promise<import('../types/project').GitBranchListResponse> {
    return request<import('../types/project').GitBranchListResponse>(
      `/api/git/${workspaceId}/branches`
    );
  },

  /**
   * Create a new branch with validation
   */
  async createBranch(
    workspaceId: string,
    branchName: string,
    checkout: boolean = true
  ): Promise<import('../types/project').GitBranchResponse> {
    return request<import('../types/project').GitBranchResponse>(
      `/api/git/${workspaceId}/branches`,
      {
        method: 'POST',
        body: JSON.stringify({ branch_name: branchName, checkout }),
      }
    );
  },

  /**
   * Checkout an existing branch
   */
  async checkoutBranch(
    workspaceId: string,
    branchName: string
  ): Promise<import('../types/project').GitBranchResponse> {
    return request<import('../types/project').GitBranchResponse>(
      `/api/git/${workspaceId}/branches/checkout`,
      {
        method: 'POST',
        body: JSON.stringify({ branch_name: branchName }),
      }
    );
  },

  /**
   * Prepare a Pull Request summary from diffs and QA findings
   */
  async getPRSummary(
    workspaceId: string,
    baseBranch: string = 'main'
  ): Promise<import('../types/project').GitPRSummaryResponse> {
    return request<import('../types/project').GitPRSummaryResponse>(
      `/api/git/${workspaceId}/pr/summary`,
      {
        method: 'POST',
        body: JSON.stringify({ base_branch: baseBranch }),
      }
    );
  },

  /**
   * Create GitHub Pull Request through GitHub API with explicit user approval
   */
  async createPullRequest(
    workspaceId: string,
    payload: import('../types/project').GitPRCreateRequest
  ): Promise<import('../types/project').GitPRCreateResponse> {
    return request<import('../types/project').GitPRCreateResponse>(
      `/api/git/${workspaceId}/pr/create`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );
  },

  /**
   * Retrieve Git and GitHub operation audit logs
   */
  async getGitAuditLogs(
    workspaceId: string
  ): Promise<import('../types/project').GitAuditLogResponse[]> {
    return request<import('../types/project').GitAuditLogResponse[]>(
      `/api/git/${workspaceId}/audit-logs`
    );
  },

  /**
   * Enqueue a new isolated container sandbox execution job (Phase 8)
   */
  async createSandboxJob(
    projectId: string,
    payload: import('../types/project').SandboxJobCreateRequest
  ): Promise<import('../types/project').SandboxJobResponse> {
    return request<import('../types/project').SandboxJobResponse>(
      `/api/sandboxes/${projectId}/jobs`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );
  },

  /**
   * List recent sandbox execution jobs for a project
   */
  async getSandboxJobs(
    projectId: string,
    limit: number = 20
  ): Promise<import('../types/project').SandboxJobListResponse> {
    return request<import('../types/project').SandboxJobListResponse>(
      `/api/sandboxes/${projectId}/jobs?limit=${limit}`
    );
  },

  /**
   * Get specific sandbox job status, exit code, and logs
   */
  async getSandboxJob(
    projectId: string,
    jobId: string
  ): Promise<import('../types/project').SandboxJobResponse> {
    return request<import('../types/project').SandboxJobResponse>(
      `/api/sandboxes/${projectId}/jobs/${jobId}`
    );
  },

  /**
   * Check project quota, concurrency, and host Docker availability
   */
  async getSandboxQuota(
    projectId: string
  ): Promise<import('../types/project').SandboxQuotaStatusResponse> {
    return request<import('../types/project').SandboxQuotaStatusResponse>(
      `/api/sandboxes/${projectId}/quota`
    );
  },

  /**
   * Phase 5: Trigger a new QA and Security Audit run on the project workspace
   */
  async triggerQARun(
    projectId: string
  ): Promise<import('../types/project').QARunResponse> {
    return request<import('../types/project').QARunResponse>(
      `/api/projects/${projectId}/qa/run`,
      { method: 'POST' }
    );
  },

  /**
   * Get the latest QA and Security audit run for a project
   */
  async getLatestQARun(
    projectId: string
  ): Promise<import('../types/project').QARunResponse | null> {
    return request<import('../types/project').QARunResponse | null>(
      `/api/projects/${projectId}/qa/latest`
    );
  },

  /**
   * Apply an approved bounded repair to fix a specific QA finding
   */
  async applyFindingRepair(
    projectId: string,
    findingId: string,
    customCode?: string
  ): Promise<import('../types/project').ApplyRepairResponse> {
    return request<import('../types/project').ApplyRepairResponse>(
      `/api/projects/${projectId}/qa/findings/${findingId}/repair`,
      {
        method: 'POST',
        body: JSON.stringify({ custom_code: customCode }),
      }
    );
  },

  /**
   * List all findings for a project
   */
  async getProjectFindings(
    projectId: string
  ): Promise<import('../types/project').QAFindingItem[]> {
    return request<import('../types/project').QAFindingItem[]>(
      `/api/projects/${projectId}/qa/findings`
    );
  },
};







