export interface Project {
  id: string;
  name: string;
  original_requirements: string;
  status: string;
  repository_id?: string | null;
  selected_branch?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateProjectPayload {
  requirements: string;
  name?: string;
  repository_id?: string | null;
  selected_branch?: string | null;
}

export interface HealthResponse {
  status: 'ok' | 'degraded';
  version: string;
  database: 'connected' | 'disconnected';
  timestamp: string;
}

export type ConnectionStatus = 'checking' | 'connected' | 'disconnected';

export interface ModuleItem {
  name: string;
  description: string;
}

export interface RequirementsAnalysis {
  project_summary: string;
  functional_requirements: string[];
  suggested_tech_stack: string[];
  main_modules: ModuleItem[];
  important_assumptions: string[];
  potential_risks: string[];
  model_used?: string;
}

export interface AnalyzeRequestPayload {
  requirements: string;
  project_name?: string;
}

export interface WorkflowPlanTask {
  id: string;
  title: string;
  description: string;
  dependencies: string[];
  acceptance_criteria: string[];
  estimated_complexity: string;
}

export interface WorkflowPlan {
  tasks: WorkflowPlanTask[];
  missing_information: string[];
  execution_strategy: string;
}

export interface ArchitectureComponent {
  name: string;
  type: string;
  responsibilities: string;
  technologies: string[];
}

export interface ApiBoundary {
  endpoint: string;
  method: string;
  description: string;
  request_format: string;
  response_format: string;
}

export interface DatabaseEntity {
  entity_name: string;
  attributes: string[];
  relationships: string[];
}

export interface WorkflowArchitecture {
  system_pattern: string;
  components: ArchitectureComponent[];
  api_boundaries: ApiBoundary[];
  database_entities: DatabaseEntity[];
  data_flow: string[];
}

export interface WorkflowValidation {
  is_valid: boolean;
  score: number;
  coverage_summary: string;
  flagged_issues: string[];
  recommendations: string[];
}

export interface WorkflowRun {
  id: string;
  project_id: string;
  correlation_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  current_stage: string;
  completed_stages: string[];
  plan_output?: WorkflowPlan | null;
  architecture_output?: WorkflowArchitecture | null;
  validation_output?: WorkflowValidation | null;
  repo_understanding_output?: Record<string, any> | null;
  developer_output?: Record<string, any> | null;
  qa_output?: Record<string, any> | null;
  security_output?: Record<string, any> | null;
  code_review_output?: Record<string, any> | null;
  documentation_output?: Record<string, any> | null;
  pipeline_type?: string;
  error_message?: string | null;
  retry_count: number;
  created_at: string;
  updated_at: string;
}

export interface WorkflowStartResponse {
  message: string;
  workflow_id: string;
  project_id: string;
  correlation_id: string;
  status: string;
  current_stage: string;
}

export interface FileManifestItem {
  path: string;
  language: string;
  purpose: string;
  is_entrypoint: boolean;
}

export interface GeneratedFile {
  id: string;
  file_path: string;
  language: string;
  purpose: string;
  file_size_bytes: number;
  checksum: string;
  is_modified_by_user: boolean;
  created_at: string;
  updated_at: string;
}

export interface FileContentResponse {
  file_path: string;
  content: string;
  language: string;
  size_bytes: number;
  checksum: string;
  is_modified_by_user: boolean;
}

export interface GenerateStatusResponse {
  id: string;
  project_id: string;
  status: 'pending' | 'generating' | 'completed' | 'failed';
  template_type: string;
  total_files: number;
  generated_files_count: number;
  percent_complete: number;
  error_message?: string | null;
  updated_at: string;
}

export interface GenerateStartRequest {
  template_type?: 'fastapi' | 'react' | 'fullstack';
  force_regenerate?: boolean;
}

export interface ImportedRepository {
  id: string;
  name: string;
  repo_url: string;
  owner: string;
  default_branch: string;
  is_private: boolean;
  status: 'pending' | 'importing' | 'indexing' | 'ready' | 'failed';
  total_files: number;
  total_chunks: number;
  total_size_bytes: number;
  error_message?: string | null;
  last_indexed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface RepoImportRequest {
  repo_url: string;
  name?: string;
  branch?: string;
  access_token?: string;
}

export interface RetrievedChunk {
  file_path: string;
  line_range: string;
  language: string;
  score: number;
  content: string;
}

export interface RepoChatResponse {
  question: string;
  answer: string;
  sources: RetrievedChunk[];
  evidence_sufficient: boolean;
}

export interface GitFileChange {
  path: string;
  status: 'modified' | 'added' | 'deleted' | 'untracked' | 'renamed';
  staged: boolean;
}

export interface GitCommitInfo {
  sha: string;
  message: string;
  author: string;
  date: string;
}

export interface GitStatusResponse {
  is_git_repo: boolean;
  current_branch?: string;
  is_clean: boolean;
  staged_files: GitFileChange[];
  unstaged_files: GitFileChange[];
  untracked_files: string[];
  total_changes: number;
  latest_commit?: GitCommitInfo | null;
}

export interface GitDiffResponse {
  diff: string;
  files_changed: string[];
  insertions: number;
  deletions: number;
}

export interface GitCommitProposeResponse {
  proposed_message: string;
  summary: string;
  files_detected: string[];
}

export interface GitCommitRequest {
  message: string;
  files?: string[];
  approved: boolean;
}

export interface GitCommitResponse {
  commit_sha: string;
  branch: string;
  message: string;
  files_committed: number;
  created_at: string;
}

export interface GitBranchListResponse {
  current_branch: string;
  branches: string[];
}

export interface GitBranchResponse {
  current_branch: string;
  message: string;
}

export interface GitPRSummaryResponse {
  title: string;
  body: string;
  commits_count: number;
  files_changed_count: number;
  qa_findings_referenced: number;
}

export interface GitPRCreateRequest {
  repo_url: string;
  title: string;
  body: string;
  head_branch: string;
  base_branch: string;
  github_token: string;
  approved: boolean;
}

export interface GitPRCreateResponse {
  pull_request_url: string;
  pull_request_number: number;
  title: string;
  state: string;
  head_branch: string;
  base_branch: string;
  created_at: string;
}

export interface GitAuditLogResponse {
  id: string;
  project_id?: string;
  repository_id?: string;
  operation: string;
  branch?: string;
  commit_sha?: string;
  details?: Record<string, any>;
  status: string;
  error_message?: string;
  created_at: string;
}

export type SandboxWorkloadType = 'python_pytest' | 'python_syntax' | 'react_build';

export interface SandboxJobCreateRequest {
  workload_type: SandboxWorkloadType;
  custom_args?: string[];
  timeout_seconds?: number;
}

export interface SandboxJobResponse {
  id: string;
  project_id: string;
  workload_type: string;
  command: string[];
  status: 'queued' | 'running' | 'completed' | 'failed' | 'timed_out';
  exit_code?: number | null;
  stdout?: string | null;
  stderr?: string | null;
  duration_ms?: number | null;
  memory_limit_mb: number;
  cpu_limit: string;
  timeout_seconds: number;
  error_message?: string | null;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface SandboxJobListResponse {
  jobs: SandboxJobResponse[];
  total: number;
}

export interface SandboxQuotaStatusResponse {
  project_id: string;
  hourly_runs_used: number;
  hourly_runs_limit: number;
  concurrent_running: number;
  concurrent_limit: number;
  can_execute: boolean;
  docker_available: boolean;
}

// Phase 5: QA, Code Review, and Security Types
export type QAFindingSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';

export interface QAFindingItem {
  id: string;
  qa_run_id: string;
  project_id: string;
  finding_type: string;
  severity: QAFindingSeverity;
  category: string;
  file_path: string;
  line_number?: number | null;
  is_verified: boolean;
  evidence?: string | null;
  explanation: string;
  suggested_remediation: string;
  proposed_code?: string | null;
  status: 'open' | 'repair_proposed' | 'repair_approved' | 'resolved' | 'dismissed';
  created_at: string;
  updated_at: string;
}

export interface QAReviewSummary {
  total_findings: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  info_count: number;
  verified_count: number;
  resolved_count: number;
  security_score: number;
  security_status: 'passed' | 'action_required';
  disclaimer: string;
}

export interface QATestPlanItem {
  file_target: string;
  test_type: string;
  description: string;
  expected_coverage: string;
}

export interface QATestPlan {
  test_framework: string;
  test_cases: QATestPlanItem[];
  coverage_gaps: string[];
}

export interface QARunResponse {
  id: string;
  project_id: string;
  generated_project_id?: string | null;
  status: string;
  current_stage: string;
  summary?: QAReviewSummary | null;
  test_plan?: QATestPlan | null;
  error_message?: string | null;
  repair_attempts: number;
  created_at: string;
  updated_at: string;
  findings: QAFindingItem[];
}

export interface ApplyRepairResponse {
  status: string;
  finding_id: string;
  affected_file: string;
  message: string;
  recheck_verified: boolean;
  summary?: QAReviewSummary | null;
}






